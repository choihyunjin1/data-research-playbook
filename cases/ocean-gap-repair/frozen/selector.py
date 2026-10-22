"""Fixed local-comparison selector: reads only observed intervals outside the gap."""
import numpy as np
WINDOW=168
MIN_PROBES=4
EPS=1e-12
def probe_stats(a,depths):
    """a contains m+2 fully observed points, all outside the actual hidden gap."""
    a=np.asarray(a,float);z0,zt,z1=depths
    if not z0<zt<z1 or a.ndim!=2 or a.shape[1]!=3 or len(a)<3:raise ValueError('Invalid depths/shape')
    if not np.isfinite(a).all():raise ValueError('Complete observed probe required')
    m=len(a)-2;f=np.arange(1,m+1)/(m+1);w=(zt-z0)/(z1-z0)
    S=(1-w)*a[:,0]+w*a[:,2]
    q=a[1:-1,1]-((1-f)*a[0,1]+f*a[-1,1])
    c=S[1:-1]-((1-f)*S[0]+f*S[-1])
    Q=q.sum()/24;C=c.sum()/24
    return Q*Q,C*C,2*C*Q,C*C-2*C*Q

def choose(masked,g,m,depths):
    """No path, hidden truth, or whole-series summary is accepted. Half-open indices."""
    a=np.asarray(masked,float)
    if a.ndim!=2 or a.shape[1]!=3 or m not in (1,3,6,12,24) or g<0 or g+m>len(a):raise ValueError('Invalid gap')
    if not np.isnan(a[g:g+m,1]).all():raise ValueError('Hide target before selection')
    if not depths[0]<depths[1]<depths[2]:raise ValueError('Unbracketed depths')
    k=m+2;meta={};rows=[];side_good=[];enough=[]
    for side in ['left','right']:
        stats=[]
        for j in range(1,WINDOW//k+1):
            lo=g-j*k if side=='left' else g+m+(j-1)*k;hi=lo+k
            if lo<0 or hi>len(a):continue
            assert hi<=g or lo>=g+m
            probe=a[lo:hi]
            if not np.isfinite(probe).all():continue
            v=probe_stats(probe,depths);stats.append(v)
            rows.append({'side':side,'probe_number':j,'lo':lo,'hi_exclusive':hi,
                         'target_mse':v[0],'correction_energy':v[1],'matched_term':v[2],'mse_delta':v[3]})
        means=np.mean(stats,axis=0) if stats else np.full(4,np.nan)
        meta.update({f'{side}_n':len(stats),f'{side}_delta':float(means[3]),
                     f'{side}_energy':float(means[1]),f'{side}_match':float(means[2])})
        enough.append(len(stats)>=MIN_PROBES);side_good.append(means[3]<-EPS)
    use=all(enough) and all(side_good)
    reason='both_sides_improved' if use else 'insufficient_context' if not all(enough) else 'sides_disagree' if any(side_good) else 'no_two_sided_gain'
    return ('bridge' if use else 'temporal'),{**meta,'reason':reason},rows
