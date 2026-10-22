"""Historical analysis replay. Calculation bodies are unchanged; IO is injected.

Adapted from selector-harm-avoidance-20261022/analyze.py. This is not a new
holdout evaluation and does not modify the original study directory.
"""
import json
import numpy as np
import pandas as pd
from .context import ROOT,check_freeze,save,sha,now,CONTRACT_SHA
from ..frozen.method import predict,GAPS
from ..frozen.selector import choose,WINDOW
METHODS=('remaining','temporal','depth','bridge','selected')
BOOTSTRAPS=((7,2000),(30,1000))
SEED=20261022

def site_contract(site=None):
    if site is None:site=json.loads((ROOT/'site.json').read_text(encoding='utf-8'))
    start=pd.Timestamp(site['eval_start_utc']);end=pd.Timestamp(site['eval_end_exclusive_utc'])
    start=start.tz_localize('UTC') if start.tz is None else start.tz_convert('UTC')
    end=end.tz_localize('UTC') if end.tz is None else end.tz_convert('UTC')
    assert start==start.normalize() and end==end.normalize() and end>start
    return site,start,end

def cases_from_hourly():
    site,begin,end=site_contract();depths=site['depths_m']
    h=pd.read_csv(ROOT/'hourly.csv');ts=pd.DatetimeIndex(pd.to_datetime(h.time_utc,utc=True))
    assert ts.is_unique and ((ts[1:]-ts[:-1])==pd.Timedelta(hours=1)).all()
    assert ts[0]==pd.Timestamp(site['source_query_start_utc'])
    assert ts[-1]+pd.Timedelta(hours=1)==pd.Timestamp(site['source_query_end_exclusive_utc'])
    assert ts[0]<=begin-pd.Timedelta(hours=WINDOW) and ts[-1]>=end+pd.Timedelta(hours=WINDOW-1)
    a=h[['top','target','bottom']].to_numpy(float);cases=[];elig=[];audit=[];audited=set()
    for day in pd.date_range(begin,end,freq='D',inclusive='left'):
        j=ts.get_loc(day);raw=a[j-1:j+25];full=np.isfinite(raw[1:25]).all();edge=np.isfinite(raw[[0,25],1]).all()
        elig.append({'date':day.strftime('%Y-%m-%d'),'eligible':bool(full and edge),'complete_day':bool(full),'target_edges':bool(edge)})
        if not(full and edge):continue
        truth=raw[1:25,1].copy();daily=truth.mean()
        for m in GAPS:
            for start in range(0,24,m):
                g=j+start;local=a[g-WINDOW:g+m+WINDOW].copy();local[WINDOW:WINDOW+m,1]=np.nan
                assert local.shape==(2*WINDOW+m,3)
                action,info,probes=choose(local,WINDOW,m,depths)
                masked=raw.copy();masked[1+start:1+start+m,1]=np.nan
                means,fills,supported=predict(masked,start,m,depths=depths)
                applied=action if supported else 'temporal'
                means['selected']=means[applied];fills['selected']=fills[applied]
                row={'date':day.strftime('%Y-%m-%d'),'gap_hours':m,'start':start,'truth_daily':daily,
                     'action':action,'applied':applied,'bridge_supported':supported,
                     'application_reason':'missing_bridge_boundary' if action=='bridge' and not supported else info['reason'],**info}
                for name in METHODS:
                    row[name+'_mean']=means[name];row[name+'_error']=means[name]-daily
                    pred=fills.get(name,np.full(m,means[name]));row[name+'_point_mse']=np.mean((pred-truth[start:start+m])**2)
                cases.append(row)
                if m not in audited:
                    audit.extend({**p,'date':day.strftime('%Y-%m-%d'),'gap_hours':m,'start':start,
                                  'lo_utc':ts[g-WINDOW+p['lo']].isoformat(),
                                  'hi_exclusive_utc':(ts[g-WINDOW+p['hi_exclusive']-1]+pd.Timedelta(hours=1)).isoformat()} for p in probes)
                    audited.add(m)
    return pd.DataFrame(cases),pd.DataFrame(elig),pd.DataFrame(audit)

def summary(c,groups=('gap_hours',)):
    out=[]
    for keys,g in c.groupby(list(groups),sort=True):
        keys=keys if isinstance(keys,tuple) else (keys,)
        for name in METHODS:
            e=g[name+'_error'];x=pd.DataFrame({'date':g.date,'sq':e**2,'abs':abs(e),'bias':e,'point':g[name+'_point_mse']})
            x=x[np.isfinite(x.sq)];v=x.groupby('date').mean().mean()
            out.append({**dict(zip(groups,keys)),'method':name,'dates':g.date.nunique(),'valid_dates':x.date.nunique(),
                'cases':len(g),'valid_cases':len(x),'rmse':np.sqrt(v.sq) if len(x) else np.nan,
                'mae':v['abs'] if len(x) else np.nan,'bias':v.bias if len(x) else np.nan,
                'point_rmse':np.sqrt(v.point) if len(x) else np.nan})
    return pd.DataFrame(out)

def calendar_weights(date_index,block,reps,site=None):
    """Calendar bins preserve holes and leap days; paired columns share weights."""
    _,begin,end=site_contract(site)
    dates=pd.DatetimeIndex(pd.to_datetime(date_index,utc=True))
    assert dates.is_unique and (dates>=begin).all() and (dates<end).all()
    total_days=int((end-begin)/pd.Timedelta(days=1))
    ids=((dates-begin).days//block).to_numpy();nb=(total_days+block-1)//block
    n=np.bincount(ids,minlength=nb);rng=np.random.default_rng(SEED)
    w=np.array([np.bincount(rng.integers(0,nb,size=nb),minlength=nb) for _ in range(reps)])
    den=w@n;ok=den>0
    return ids,nb,w[ok],den[ok],total_days

def resample_daily(daily,block,reps,site=None):
    ids,nb,w,den,days=calendar_weights(daily.index,block,reps,site)
    tot=np.column_stack([np.bincount(ids,weights=daily[k],minlength=nb) for k in daily.columns])
    return w@tot/den[:,None],days,nb

def uncertainty(c,site=None):
    rows=[]
    for m,g in c.groupby('gap_hours'):
        for base in ['temporal','bridge','depth','remaining']:
            if m==24 and base=='remaining':continue
            cols=['selected_error',base+'_error'];sq=(g[cols]**2).groupby(g.date).mean()
            for block,reps in BOOTSTRAPS:
                dist,days,nb=resample_daily(sq,block,reps,site)
                md=dist[:,0]-dist[:,1];rd=np.sqrt(dist[:,0])-np.sqrt(dist[:,1])
                lo,hi=np.quantile(rd,[.025,.975]);ml,mh=np.quantile(md,[.025,.975])
                means=sq.mean().to_numpy();actual=np.sqrt(means)
                rows.append({'gap_hours':m,'baseline':base,'block_days':block,'calendar_days':days,'calendar_blocks':nb,
                             'requested_replicates':reps,'replicates':len(dist),'rmse_delta':actual[0]-actual[1],
                             'ci95_low':lo,'ci95_high':hi,'mse_delta':means[0]-means[1],
                             'mse_ci95_low':ml,'mse_ci95_high':mh,
                             'percent_change':100*(actual[0]/actual[1]-1) if actual[1]>0 else np.nan})
    return pd.DataFrame(rows)

def date_equal_mean(values,dates):
    return float(pd.Series(np.asarray(values,dtype=float),index=dates).groupby(level=0).mean().mean())

def harm_daily(g):
    """Positive contributions with the same full-cohort denominator."""
    d=g.bridge_error**2-g.temporal_error**2;time=g.applied.eq('temporal')
    assert np.isfinite(d).all() and g.applied.isin(['temporal','bridge']).all()
    np.testing.assert_allclose(g.selected_error,np.where(time,g.temporal_error,g.bridge_error),rtol=1e-12,atol=1e-12)
    x=pd.DataFrame({'date':g.date,'avoided_harm':d.where(time&(d>0),0),
        'missed_gain':(-d).where(time&(d<0),0),'retained_harm':d.where(~time&(d>0),0),
        'retained_gain':(-d).where(~time&(d<0),0),'net_vs_bridge':g.selected_error**2-g.bridge_error**2})
    daily=x.groupby('date').mean()
    np.testing.assert_allclose(daily.net_vs_bridge,daily.missed_gain-daily.avoided_harm,rtol=1e-10,atol=1e-12)
    return daily

def harm_diagnostics(c):
    rows=[];reasons=[];impacts=[]
    for m,g in c.groupby('gap_hours'):
        d=g.bridge_error**2-g.temporal_error**2;time=g.applied.eq('temporal');harmful=d>0;helpful=d<0
        weighted=lambda v:date_equal_mean(v,g.date)
        hm=weighted(harmful);tm=weighted(time);avoided=weighted(time&harmful);daily=harm_daily(g)
        rows.append({'gap_hours':m,'priority':'primary' if m in (6,12,24) else 'secondary',
            'cases':len(g),'dates':g.date.nunique(),'harmful_bridge_cases':int(harmful.sum()),
            'helpful_bridge_cases':int(helpful.sum()),'tie_cases':int((d==0).sum()),'time_cases':int(time.sum()),
            'avoided_harm_cases':int((time&harmful).sum()),'missed_gain_cases':int((time&helpful).sum()),
            'retained_harm_cases':int((~time&harmful).sum()),
            'harm_recall':avoided/hm if hm>0 else np.nan,
            'time_choice_precision':avoided/tm if tm>0 else np.nan,'time_selection_share':tm,
            **{k:float(v) for k,v in daily.mean().items()}})
        for reason in ['no_two_sided_gain','sides_disagree','insufficient_context','missing_bridge_boundary']:
            mask=time&g.application_reason.eq(reason);mass=weighted(mask);good=weighted(mask&harmful)
            ah=weighted(d.where(mask&harmful,0));mg=weighted((-d).where(mask&helpful,0))
            reasons.append({'gap_hours':m,'reason':reason,
                'reason_class':'evidence' if reason in ('no_two_sided_gain','sides_disagree') else 'unavailable_input',
                'full_cohort_cases':len(g),'time_cases':int(mask.sum()),'avoided_harm_cases':int((mask&harmful).sum()),
                'missed_gain_cases':int((mask&helpful).sum()),'full_cohort_time_share':mass,
                'time_choice_precision':good/mass if mass>0 else np.nan,
                'harm_recall_contribution':good/hm if hm>0 else np.nan,
                'avoided_harm':ah,'missed_gain':mg,'net_vs_bridge':mg-ah})
        for label,mask in [('chosen_helped',~time&helpful),('chosen_hurt',~time&harmful),
                           ('time_avoided_harm',time&harmful),('time_missed_gain',time&helpful)]:
            impacts.append({'gap_hours':m,'category':label,'cases':int(mask.sum()),
                            'full_cohort_delta_contribution':weighted(d.where(mask,0))})
    return pd.DataFrame(rows),pd.DataFrame(reasons),pd.DataFrame(impacts)

def harm_uncertainty(c,site=None):
    rows=[]
    for m,g in c.groupby('gap_hours'):
        daily=harm_daily(g)[['avoided_harm','missed_gain','net_vs_bridge']]
        for block,reps in BOOTSTRAPS:
            dist,days,nb=resample_daily(daily,block,reps,site)
            np.testing.assert_allclose(dist[:,2],dist[:,1]-dist[:,0],rtol=1e-9,atol=1e-12)
            for k,name in enumerate(daily.columns):
                lo,hi=np.quantile(dist[:,k],[.025,.975])
                rows.append({'gap_hours':m,'quantity':name,'block_days':block,'calendar_days':days,
                    'calendar_blocks':nb,'requested_replicates':reps,'replicates':len(dist),
                    'mse_contribution':float(daily[name].mean()),'ci95_low':lo,'ci95_high':hi})
    return pd.DataFrame(rows)

def main():
    check_freeze();c,e,p=cases_from_hourly();e.to_csv(ROOT/'day-eligibility.csv',index=False)
    if c.empty:
        save('result.json',{'at_utc':now(),'status':'NO_ELIGIBLE_DATES','new_station_switch':False});return
    c.to_csv(ROOT/'cases.csv',index=False,float_format='%.17g');p.to_csv(ROOT/'probe-audit-sample.csv',index=False,float_format='%.17g')
    s=summary(c);s.to_csv(ROOT/'overall.csv',index=False,float_format='%.17g')
    summary(c.assign(month=c.date.str[:7]),('gap_hours','month')).to_csv(ROOT/'monthly.csv',index=False)
    uncertainty(c).to_csv(ROOT/'uncertainty.csv',index=False,float_format='%.17g')
    selection=[]
    for m,g in c.groupby('gap_hours'):
        selection.append({'gap_hours':m,'cases':len(g),'bridge_chosen':int(g.action.eq('bridge').sum()),
          'bridge_applied':int(g.applied.eq('bridge').sum()),'bridge_rate':float(g.applied.eq('bridge').mean()),
          'missing_bridge_boundary':int(g.application_reason.eq('missing_bridge_boundary').sum()),
          **{k:int(v) for k,v in g.reason.value_counts().items()}})
    pd.DataFrame(selection).fillna(0).to_csv(ROOT/'selection.csv',index=False)
    harm,reasons,impact=harm_diagnostics(c)
    harm.to_csv(ROOT/'harm-diagnostics.csv',index=False,float_format='%.17g')
    reasons.to_csv(ROOT/'harm-by-reason.csv',index=False,float_format='%.17g')
    impact.to_csv(ROOT/'selection-impact.csv',index=False,float_format='%.17g')
    harm_uncertainty(c).to_csv(ROOT/'harm-uncertainty.csv',index=False,float_format='%.17g')
    site,begin,end=site_contract()
    save('result.json',{'at_utc':now(),'station':site['station'],'depths_m':site['depths_m'],'training_runs':0,
      'rule_tuning_runs':0,'evaluation_scope':'historical fixed study replay; not a new holdout',
      'local_observed_error_comparison':True,'evaluation_start_utc':begin.isoformat(),'evaluation_end_exclusive_utc':end.isoformat(),
      'primary_gap_hours':[6,12,24],'secondary_gap_hours':[1,3],
      'eligible_dates':int(e.eligible.sum()),'excluded_dates':int((~e.eligible).sum()),'cases':len(c),
      'first_date':c.date.min(),'last_date':c.date.max(),'low_sample':bool(e.eligible.sum()<60),
      'harm_cases_present':bool((harm.harmful_bridge_cases>0).any()),
      'replay_contract_sha256':CONTRACT_SHA,'hourly_sha256':sha(ROOT/'hourly.csv')})
if __name__=='__main__':main()
