"""Replay extraction from a hash-verified local snapshot, without network access.

TEMP selection, duplicate handling and hourly conversion match the historical
acquire_extract.py; source lookup and execution receipts are adapted for replay.
"""
import json
from pathlib import Path
import numpy as np,pandas as pd,netCDF4
from .context import ROOT,SOURCE,save,sha,now,check_freeze,CONTRACT_SHA

def main():
    check_freeze();site=json.loads((ROOT/'site.json').read_text(encoding='utf-8'))
    path=SOURCE;depths=site['depths_m'];indices=site['instrument_indices']
    assert sha(path)==site['source_sha256'],'Public source snapshot changed'
    folder=ROOT/'source';folder.mkdir(exist_ok=True)
    assert not (folder/'extraction-read.json').exists(),'Do not overwrite a replay extraction'
    start=pd.Timestamp(site['source_query_start_utc']);end=pd.Timestamp(site['source_query_end_exclusive_utc'])
    with netCDF4.Dataset(path) as ds:
        ds.set_auto_mask(False)
        save('source/metadata.json',{'attributes':{k:str(ds.getncattr(k)) for k in ds.ncattrs()},
          'variables':{k:{'dimensions':v.dimensions,'attrs':{n:str(v.getncattr(n)) for n in v.ncattrs()}} for k,v in ds.variables.items()}})
        nominal=np.asarray(ds['NOMINAL_DEPTH'][:],float)
        assert np.array_equal(nominal[indices],depths)
        ts=pd.DatetimeIndex(pd.to_datetime(netCDF4.num2date(ds['TIME'][:],ds['TIME'].units,
            only_use_cftime_datetimes=False).astype('datetime64[us]'),utc=True))
        ix=np.asarray(ds['instrument_index'][:],int)
        selected=np.flatnonzero((ts>=start)&(ts<end)&np.isin(ix,indices))
        rounded=ts[selected].round('h')
        assert len(selected) and max(abs((ts[selected]-rounded).total_seconds()))<=1
        check_freeze()
        save('source/extraction-read.json',{'at_utc':now(),'replay_contract_sha256':CONTRACT_SHA,
            'source_sha256':sha(path),'rows_requested':len(selected),'instrument_indices':indices,
            'query_start_utc':start.isoformat(),'query_end_exclusive_utc':end.isoformat(),
            'scope':'Only the three metadata-selected new deployment instruments; not all same-depth instruments',
            'file_previously_downloaded':True,'historical_replay':True,'new_holdout':False})
        t=np.asarray(ds['TEMP'][selected],float);t[t==ds['TEMP']._FillValue]=np.nan
        outside=(t<float(ds['TEMP'].valid_min))|(t>float(ds['TEMP'].valid_max))
        instruments=[]
        for i in indices:
            chars=lambda n:b''.join(ds[n][i]).decode().rstrip('\x00 ')
            instruments.append({'index':i,'depth':float(nominal[i]),'id':chars('instrument_id'),'source':chars('source_file')})
    frame=pd.DataFrame({'time_utc':rounded,'depth_m':nominal[ix[selected]],'instrument_index':ix[selected],'temperature_c':t})
    dup=frame.duplicated(['time_utc','depth_m'],keep=False)
    frame.assign(excluded_duplicate=dup).to_csv(folder/'selected-records.csv',index=False,float_format='%.17g')
    h=frame.loc[~dup].pivot(index='time_utc',columns='depth_m',values='temperature_c')
    h=h.reindex(pd.date_range(start,end-pd.Timedelta(hours=1),freq='h')).reindex(columns=depths)
    h.columns=['top','target','bottom'];h.index.name='time_utc';h.to_csv(ROOT/'hourly.csv',float_format='%.17g')
    save('source/extraction-quality.json',{'selected_rows':len(frame),'duplicate_rows_excluded':int(dup.sum()),
        'outside_metadata_range':int(outside.sum()),'nonfinite_selected_rows':int((~np.isfinite(t)).sum()),
        'valid_hours':{k:int(v) for k,v in h.notna().sum().items()},'instruments':instruments,
        'hourly_sha256':sha(ROOT/'hourly.csv'),'source_sha256':sha(path),
        'new_training':0,'source_policy':'Retain finite out-of-metadata-range values as before; exclude duplicates and fill values'})
if __name__=='__main__':main()
