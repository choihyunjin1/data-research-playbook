"""Frozen no-fit bridge and comparators. Hidden target is not an input."""
import numpy as np

GAPS=(1,3,6,12,24)
METHODS=('remaining','temporal','depth','bridge')
DEPTHS=(20.,60.,63.)

def predict(masked26,start,m,depths=DEPTHS):
    a=np.asarray(masked26,dtype=float)
    if a.shape!=(26,3) or m not in GAPS or start not in range(0,25-m):
        raise ValueError('26 hourly rows and valid gap required')
    z0,zt,z1=depths
    if not z0<zt<z1: raise ValueError('Target must be bracketed')
    q=1+start; y=a[:,1]
    if not np.isnan(y[q:q+m]).all(): raise ValueError('Mask hidden target first')
    keep=np.r_[y[1:q],y[q+m:25]]
    if not np.isfinite(keep).all() or not np.isfinite(y[[q-1,q+m]]).all():
        raise ValueError('Visible target/boundaries required')
    w=(zt-z0)/(z1-z0); S=(1-w)*a[:,0]+w*a[:,2]
    if not np.isfinite(S[q:q+m]).all(): raise ValueError('Gap depth endpoints required')
    f=np.arange(1,m+1)/(m+1)
    time=(1-f)*y[q-1]+f*y[q+m]
    depth=S[q:q+m].copy()
    supported=bool(np.isfinite(S[[q-1,q+m]]).all())
    bridge=time+depth-((1-f)*S[q-1]+f*S[q+m]) if supported else time.copy()
    fills={'temporal':time,'depth':depth,'bridge':bridge}
    means={k:float((keep.sum()+v.sum())/24) for k,v in fills.items()}
    means['remaining']=float(keep.mean()) if len(keep) else np.nan
    return means,fills,supported
