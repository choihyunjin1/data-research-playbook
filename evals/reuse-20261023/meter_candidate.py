import numpy as np
import pandas as pd

def device_id(value):
    return int(float(value))

def cap_prediction(values):
    return np.clip(np.asarray(values,dtype=float),0,100)

def average_prediction(times, values, blocks):
    # Intended to smooth within the caller's evaluation blocks.
    series=pd.Series(values,index=pd.to_datetime(times,utc=True))
    return series.rolling('60min',center=True,min_periods=1).mean().to_numpy()
