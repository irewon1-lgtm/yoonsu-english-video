"""Quiet contact sounds anchored to the same post-response movement clock as film.state."""
import math
import numpy as np

def apply(mix,scenes,rate,fps):
    for number,sc in enumerate(scenes,1):
        start=sc['events'][4]['end']/fps+.08
        end=sc['end']/fps-.24
        marks={10:[(.495,144)],15:[(.79,79)],16:[(.79,87)],17:[(.395,97),(.895,90)],18:[(.79,82)],29:[(.91,73)],34:[(.96,105)]}.get(number,[])
        for phase,freq in marks:
            sec=start+(end-start)*phase
            begin=round(sec*rate); time=np.arange(round(.105*rate))/rate
            env=np.minimum(1,time/.004)*np.exp(-time/.023)*np.minimum(1,(time[-1]-time)/.015)
            tone=np.sin(2*np.pi*(freq*time+35*.023*(1-np.exp(-time/.023))))
            mix[begin:begin+len(time)]+=.043*tone*env
