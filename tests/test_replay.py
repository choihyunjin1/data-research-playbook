"""Historical synthetic checks plus portable replay failure contracts.

The 29 numerical tests retain the original assertions; runtime fixtures are
confined to ignored .runs. No raw source is required by this unit suite.
"""
import unittest,json,tempfile,shutil
from pathlib import Path
from unittest.mock import patch
import numpy as np,pandas as pd
from research_playbook.replay import (_case_root, _case_modules, _preflight, _sha,
    _validate_case, ReplayError, replay, _compare_expected)
CASE=_case_root()
RUNS=CASE.parents[1]/'.runs'
RUNS.mkdir(exist_ok=True)
with _case_modules(CASE,RUNS/'unit-unused',RUNS/'no-source.nc') as modules:
    analyze=modules['analyze'];method=modules['method'];selector=modules['selector']
    fingerprint=modules['fingerprints']
choose,probe_stats,WINDOW=selector.choose,selector.probe_stats,selector.WINDOW
predict,GAPS=method.predict,method.GAPS
ROOT=CASE/'frozen'
sha=_sha
DEPTHS=(33.,44.,55.)
YEAR={'eval_start_utc':'2024-01-01T00:00:00Z','eval_end_exclusive_utc':'2025-01-01T00:00:00Z'}

def harm_fixture():
    rows=[]
    for day,t,b,applied,reason in [
        ('2024-02-28',1.,3.,'temporal','no_two_sided_gain'),
        ('2024-02-28',3.,1.,'temporal','insufficient_context'),
        ('2024-03-01',1.,3.,'bridge','both_sides_improved')]:
        r={'date':day,'gap_hours':6,'applied':applied,'application_reason':reason,
           'temporal_error':t,'bridge_error':b,'selected_error':t if applied=='temporal' else b}
        for name in ('remaining','depth'):r[name+'_error']=2.
        rows.append(r)
    return pd.DataFrame(rows)

def curved(m=12):
    t=np.arange(2*WINDOW+m,dtype=float)
    y=15+np.sin(t/11)+.002*t
    a=np.column_stack([y+1,y,y-1]);a[WINDOW:WINDOW+m,1]=np.nan
    return a

class Tests(unittest.TestCase):
    def test_original_hash(self):
        self.assertEqual(sha(ROOT/'method.py'),'6ae98feb21786c52ccc15d7f344e2f340b2c3a2a1bbd5ad18e7d9fa5a7f3a5f0')
        self.assertEqual(sha(ROOT/'selector.py'),'c64514bbafa145509472589cf708738117f18fd302f121816f96579b5dbbce0e')
    def test_exact_error_identity_all_gaps(self):
        rng=np.random.default_rng(11)
        for m in GAPS:
            p=rng.normal(15,1,(m+2,3));q2,c2,matched,delta=probe_stats(p,DEPTHS)
            raw=np.full((26,3),15.);raw[:m+2]=p;truth=raw[1:25,1].mean()
            raw[1:m+1,1]=np.nan;means,_,_=predict(raw,0,m,DEPTHS)
            self.assertAlmostEqual((means['temporal']-truth)**2,q2,places=12)
            self.assertAlmostEqual((means['bridge']-truth)**2-(means['temporal']-truth)**2,delta,places=12)
            self.assertAlmostEqual(c2-matched,delta,places=12)
    def test_matching_changes_choose_bridge(self):
        for m in GAPS:
            action,info,_=choose(curved(m),WINDOW,m,DEPTHS)
            self.assertEqual(action,'bridge');self.assertLess(info['left_delta'],0)
    def test_linear_target_curved_neighbours_choose_time(self):
        a=curved();a[:,1]=15+np.arange(len(a))*.002;a[WINDOW:WINDOW+12,1]=np.nan
        self.assertEqual(choose(a,WINDOW,12,DEPTHS)[0],'temporal')
    def test_disagreement_fallback(self):
        a=curved();a[WINDOW+12:,1]=15+np.arange(WINDOW)*.002
        action,info,_=choose(a,WINDOW,12,DEPTHS)
        self.assertEqual(action,'temporal');self.assertEqual(info['reason'],'sides_disagree')
    def test_ties_fallback(self):
        a=np.ones((348,3))*15;a[168:180,1]=np.nan
        self.assertEqual(choose(a,168,12,DEPTHS)[0],'temporal')
    def test_missing_context_not_excluded(self):
        a=curved();a[:168]=np.nan
        action,info,_=choose(a,168,12,DEPTHS)
        self.assertEqual(action,'temporal');self.assertEqual(info['reason'],'insufficient_context')
    def test_only_three_probes_not_enough(self):
        a=curved();a[:168-3*14]=np.nan
        action,info,_=choose(a,168,12,DEPTHS)
        self.assertEqual(info['left_n'],3);self.assertEqual(action,'temporal')
    def test_expected_probe_counts_nonoverlap(self):
        for m in GAPS:
            _,info,rows=choose(curved(m),168,m,DEPTHS)
            n=168//(m+2);self.assertEqual(info['left_n'],n);self.assertEqual(info['right_n'],n)
            used=[]
            for p in rows:
                ix=list(range(p['lo'],p['hi_exclusive']));self.assertFalse(set(ix)&set(range(168,168+m)))
                self.assertFalse(set(ix)&set(used));used+=ix
    def test_unmasked_truth_rejected(self):
        a=curved();a[168:180,1]=0
        with self.assertRaises(ValueError):choose(a,168,12,DEPTHS)
    def test_hidden_truth_invariance(self):
        a=curved();b=a.copy();b[168:180,1]=1e30;b[168:180,1]=np.nan
        self.assertEqual(choose(a,168,12,DEPTHS),choose(b,168,12,DEPTHS))
        ra=a[167:193].copy();rb=ra.copy();rb[1:13,1]=np.nan
        np.testing.assert_allclose(predict(ra,0,12,DEPTHS)[1]['bridge'],predict(rb,0,12,DEPTHS)[1]['bridge'])
    def test_gap_neighbours_do_not_select(self):
        a=curved();b=a.copy();b[168:180,[0,2]]=1e10
        self.assertEqual(choose(a,168,12,DEPTHS),choose(b,168,12,DEPTHS))
    def test_outside_window_invariance(self):
        a=np.pad(curved(),((20,20),(0,0)),constant_values=8);b=a.copy();b[:20]=1e15;b[-20:]=-1e15
        self.assertEqual(choose(a,188,12,DEPTHS),choose(b,188,12,DEPTHS))
    def test_missing_actual_bridge_boundary(self):
        a=np.full((26,3),15.);a[1:25,1]=np.nan;a[0,0]=np.nan
        _,fills,supported=predict(a,0,24,DEPTHS)
        self.assertFalse(supported);np.testing.assert_array_equal(fills['temporal'],fills['bridge'])
    def test_custom_depth_not_parent_default(self):
        a=np.zeros((26,3));a[:,2]=2;a[1:7,1]=np.nan
        _,f,_=predict(a,0,6,DEPTHS);np.testing.assert_allclose(f['depth'],1)
    def test_invalid_probe(self):
        for a in [np.ones((2,3)),np.full((4,3),np.nan)]:
            with self.assertRaises(ValueError):probe_stats(a,DEPTHS)
    def test_integration_masks_before_selector(self):
        with tempfile.TemporaryDirectory(dir=RUNS) as d:
            root=Path(d);(root/'site.json').write_text(json.dumps({'depths_m':DEPTHS,
                'eval_start_utc':'2024-04-01T00:00:00Z','eval_end_exclusive_utc':'2024-04-02T00:00:00Z',
                'source_query_start_utc':'2024-03-25T00:00:00Z','source_query_end_exclusive_utc':'2024-04-09T00:00:00Z'}))
            ts=pd.date_range('2024-03-25T00:00Z','2024-04-09T00:00Z',inclusive='left',freq='h');a=np.full((len(ts),3),np.nan)
            j=ts.get_loc(pd.Timestamp('2024-04-01',tz='UTC'));a[j-1:j+25]=15
            h=pd.DataFrame(a,columns=['top','target','bottom']);h.insert(0,'time_utc',ts);h.to_csv(root/'hourly.csv',index=False)
            calls=[]
            def checked(masked,g,m,depths):
                self.assertTrue(np.isnan(masked[g:g+m,1]).all());self.assertEqual(tuple(depths),DEPTHS)
                self.assertEqual(masked.shape,(336+m,3));calls.append(m);return choose(masked,g,m,depths)
            with patch.object(analyze,'ROOT',root),patch.object(analyze,'choose',checked):c,e,p=analyze.cases_from_hourly()
            self.assertEqual(len(c),39);self.assertEqual(e.eligible.sum(),1);self.assertEqual(len(calls),39)
            self.assertTrue(c.action.eq('temporal').all())
            self.assertTrue(c.loc[c.gap_hours>=12,'reason'].eq('insufficient_context').all())
            self.assertTrue(c.reason.isin(['insufficient_context','no_two_sided_gain']).all())
    def test_date_equal_summary(self):
        rows=[]
        for day,errors in [('2023-01-01',[1,3]),('2023-01-02',[2])]:
            for err in errors:
                r={'date':day,'gap_hours':6}
                for method in analyze.METHODS:r[method+'_error']=err;r[method+'_point_mse']=err**2
                rows.append(r)
        s=analyze.summary(pd.DataFrame(rows));self.assertTrue(np.allclose(s.rmse,np.sqrt(4.5)))
    def test_harm_full_cohort_date_weighting(self):
        h,r,i=analyze.harm_diagnostics(harm_fixture());x=h.iloc[0]
        self.assertAlmostEqual(x.avoided_harm,2.)
        self.assertAlmostEqual(x.missed_gain,2.)
        self.assertAlmostEqual(x.retained_harm,4.)
        self.assertAlmostEqual(x.net_vs_bridge,0.)
        self.assertAlmostEqual(x.harm_recall,1/3)
        self.assertAlmostEqual(x.time_choice_precision,.5)
        self.assertEqual(x.harmful_bridge_cases,2)
        self.assertEqual(x.avoided_harm_cases,1)
    def test_harm_reason_accounting(self):
        h,r,_=analyze.harm_diagnostics(harm_fixture());x=h.iloc[0]
        self.assertAlmostEqual(r.avoided_harm.sum(),x.avoided_harm)
        self.assertAlmostEqual(r.missed_gain.sum(),x.missed_gain)
        self.assertAlmostEqual(r.net_vs_bridge.sum(),x.net_vs_bridge)
        evidence=r[r.reason_class.eq('evidence')]
        unavailable=r[r.reason_class.eq('unavailable_input')]
        self.assertAlmostEqual(evidence.avoided_harm.sum(),2.)
        self.assertAlmostEqual(unavailable.missed_gain.sum(),2.)
    def test_harm_no_outcome_filtering(self):
        c=harm_fixture();daily=analyze.harm_daily(c)
        self.assertEqual(len(daily),2)
        # An avoided harm of 8 has weight 1/4, not an outcome-conditioned mean 8.
        self.assertNotEqual(daily.avoided_harm.mean(),8.)
    def test_harm_zero_denominators_and_ties(self):
        c=harm_fixture();c['bridge_error']=c.temporal_error;c['selected_error']=c.temporal_error
        h,_,_=analyze.harm_diagnostics(c);x=h.iloc[0]
        self.assertTrue(np.isnan(x.harm_recall));self.assertEqual(x.time_choice_precision,0.)
        self.assertEqual(x.tie_cases,3);self.assertEqual(x.net_vs_bridge,0.)
        c['applied']='bridge';h,_,_=analyze.harm_diagnostics(c)
        self.assertTrue(np.isnan(h.iloc[0].time_choice_precision))
    def test_wrong_applied_result_is_rejected(self):
        c=harm_fixture();c.loc[0,'selected_error']=999
        with self.assertRaises(AssertionError):analyze.harm_daily(c)
    def test_calendar_holes_not_compressed(self):
        ids,nb,w,den,days=analyze.calendar_weights(['2024-01-01','2024-12-31'],7,50,YEAR)
        self.assertEqual(ids.tolist(),[0,52]);self.assertEqual(nb,53);self.assertEqual(days,366)
        self.assertTrue((den>0).all());self.assertLessEqual(len(w),50)
    def test_calendar_leap_day(self):
        ids,nb,_,_,days=analyze.calendar_weights(['2024-02-28','2024-02-29','2024-03-01'],1,10,YEAR)
        self.assertEqual(ids.tolist(),[58,59,60]);self.assertEqual(nb,366);self.assertEqual(days,366)
    def test_calendar_interval_not_year_hardcoded(self):
        site={'eval_start_utc':'2024-12-12T00:00:00Z','eval_end_exclusive_utc':'2025-04-16T00:00:00Z'}
        ids,nb,_,_,days=analyze.calendar_weights(['2024-12-12','2025-04-15'],30,10,site)
        self.assertEqual(days,125);self.assertEqual(nb,5);self.assertEqual(ids.tolist(),[0,4])
    def test_calendar_outside_dates_rejected(self):
        with self.assertRaises(AssertionError):analyze.calendar_weights(['2025-01-01'],7,10,YEAR)
    def test_bootstrap_is_paired_and_repeatable(self):
        daily=pd.DataFrame({'a':[1.,2.,8.],'b':[2.,4.,16.]},index=['2024-01-01','2024-02-29','2024-12-31'])
        a,days,nb=analyze.resample_daily(daily,7,200,YEAR)
        b,_,_=analyze.resample_daily(daily,7,200,YEAR)
        np.testing.assert_array_equal(a,b);np.testing.assert_allclose(a[:,1],2*a[:,0])
    def test_net_ci_matches_paired_mse_ci(self):
        c=harm_fixture();u=analyze.uncertainty(c,YEAR);h=analyze.harm_uncertainty(c,YEAR)
        for block in (7,30):
            x=u[u.baseline.eq('bridge')&u.block_days.eq(block)].iloc[0]
            y=h[h.quantity.eq('net_vs_bridge')&h.block_days.eq(block)].iloc[0]
            self.assertEqual(x.replicates,y.replicates)
            self.assertAlmostEqual(x.mse_delta,y.mse_contribution)
            self.assertAlmostEqual(x.mse_ci95_low,y.ci95_low)
            self.assertAlmostEqual(x.mse_ci95_high,y.ci95_high)

class ReplayContractTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=RUNS)
        self.addCleanup(self.temp.cleanup)
        self.base=Path(self.temp.name)
        self.inputs=self.base/'inputs';self.inputs.mkdir()
        self.output=self.base/'output'

    def test_config_has_no_machine_path(self):
        _,site=_validate_case(CASE)
        self.assertNotIn('local_source_path',site)
        self.assertEqual(site['depths_m'],[33.,44.,55.])
        self.assertEqual(site['instrument_indices'],[280,278,284])

    def test_missing_input_root_no_output(self):
        with self.assertRaises(ReplayError):replay(self.base/'absent',self.output)
        self.assertFalse(self.output.exists())

    def test_missing_raw_no_output(self):
        with self.assertRaises(ReplayError):replay(self.inputs,self.output)
        self.assertFalse(self.output.exists())

    def test_existing_output_is_not_overwritten(self):
        self.output.mkdir();sentinel=self.output/'keep.txt';sentinel.write_text('unchanged')
        with self.assertRaises(ReplayError):replay(self.inputs,self.output)
        self.assertEqual(sentinel.read_text(),'unchanged')

    def test_wrong_raw_hash_no_output(self):
        filename=json.loads((CASE/'config/site.json').read_text())['source_filename']
        (self.inputs/filename).write_bytes(b'not the public snapshot')
        with self.assertRaisesRegex(ReplayError,'SHA-256 mismatch'):replay(self.inputs,self.output)
        self.assertFalse(self.output.exists())

    def test_output_inside_inputs_is_refused(self):
        output=self.inputs/'new-run'
        with self.assertRaises(ReplayError):replay(self.inputs,output)
        self.assertFalse(output.exists())

    def test_output_inside_case_is_refused(self):
        with self.assertRaises(ReplayError):_preflight(self.inputs,CASE/'never-create-this')
        self.assertFalse((CASE/'never-create-this').exists())

    def test_changed_frozen_method_is_refused(self):
        target=self.base/'case';shutil.copytree(CASE,target)
        (target/'frozen/method.py').write_bytes(b'raise RuntimeError("modified")\n')
        with self.assertRaises(ReplayError):_validate_case(target)

    def test_changed_configuration_is_refused(self):
        target=self.base/'case';shutil.copytree(CASE,target)
        p=target/'config/site.json';site=json.loads(p.read_text());site['depths_m']=[20,60,63]
        p.write_text(json.dumps(site))
        with self.assertRaises(ReplayError):_validate_case(target)

    def test_missing_dependency_fails_before_output(self):
        # Isolate the dependency gate without forging a source acceptance receipt.
        with patch('research_playbook.replay._preflight',return_value=(CASE,self.inputs/'x',self.output,{},{})):
            with patch.dict('sys.modules',{'netCDF4':None}):
                with self.assertRaises(ModuleNotFoundError):replay(self.inputs,self.output)
        self.assertFalse(self.output.exists())

    def test_fingerprint_newlines_and_mutation(self):
        a=self.base/'a.csv';b=self.base/'b.csv'
        a.write_bytes(b'label,value\na,0.125\nb,\n')
        b.write_bytes(b'label,value\r\na,0.125\r\nb,\r\n')
        one=fingerprint.table_fingerprint(a,['label'])
        self.assertEqual(one,fingerprint.table_fingerprint(b,['label']))
        b.write_bytes(b'label,value\na,0.126\nb,\n')
        self.assertNotEqual(one,fingerprint.table_fingerprint(b,['label']))

    def test_independent_does_not_import_frozen_implementation(self):
        text=(CASE/'replay/independent.py').read_text()
        self.assertNotIn('from ..frozen',text)
        self.assertNotIn('from .analyze',text)


if __name__=='__main__':unittest.main(verbosity=2)
