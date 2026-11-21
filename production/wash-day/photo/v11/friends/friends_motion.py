"""Cairo playback of fixed, independently photographed pose and expression cels."""
from functools import lru_cache
import json
from pathlib import Path
import cairocffi as cairo

ROOT=Path(__file__).resolve().parent
ATLAS=json.loads((ROOT/'atlas.json').read_text())
NAMES={'S':'sheriff','1':'one','2':'two'}
MOUTHS={'X':0,'A':0,'B':1,'C':4,'D':3,'E':2,'F':5,'G':7,'H':4}
@lru_cache(3)
def _sheet(role):
    sheet=cairo.ImageSurface.create_from_png(str(ROOT/(NAMES[role]+'-2x.png')))
    sheet.set_device_scale(2,2)
    return sheet

def exposure(role,viseme='X',gesture_phase=None,eye=None):
    role=str(role)
    if isinstance(viseme,(tuple,list)):
        old,current,mix=viseme
        viseme=current if mix>=.45 else old
    mouth=MOUTHS.get(viseme,0)
    p=max(0,min(1,gesture_phase)) if gesture_phase is not None else 0.
    # The gesture accelerates out of anticipation, holds at full extension, and
    # settles. Each step directly selects an independently posed replacement arm.
    t=[0.,.13,.19,.25,.33,.43,.52] if role!='S' else [0.,.13,.19,.26,.34,.47]
    if p>.68:
        p=(1.-p)/.32*.52
    i=sum(p>=v-1e-8 for v in t)-1
    if eye is None:
        eye='down' if gesture_phase is not None and .10<=gesture_phase<.83 else 'ahead'
    if eye not in ('down','ahead','blink'):
        eye='ahead'
    return max(0,i),str(mouth),eye


def _cel(ctx,surface,rec):
    sx,sy,w,h,x,y=rec
    ctx.save()
    ctx.rectangle(x,y,w,h)
    ctx.clip()
    ctx.set_source_surface(surface,x-sx,y-sy)
    ctx.get_source().set_filter(cairo.FILTER_BILINEAR)
    ctx.paint()
    ctx.restore()


def draw_actor(ctx,role,x,ground_y,height,action,t,viseme='X',gesture_phase=None,eye=None):
    """Draw at a fixed floor contact. gesture_phase is a single intentional cue [0,1]."""
    role=str(role)
    if role not in ATLAS:
        return
    record=ATLAS[role]; pose,mouth,eye=exposure(role,viseme,gesture_phase,eye)
    center,sole,top=record['hold']
    scale=height/(sole-top)
    ctx.save()
    ctx.translate(x-center*scale,ground_y-sole*scale)
    ctx.scale(scale,scale)
    sheet=_sheet(role)
    _cel(ctx,sheet,record['body'][pose])
    if mouth!='0':
        _cel(ctx,sheet,record['mouth'][mouth])
    if eye!='down':
        _cel(ctx,sheet,record['eye'][eye])
    ctx.restore()


@lru_cache(96)
def _held_visemes(cues,n,fps):
    vals=[]
    for pos in range(n):
        second=(pos+.5)/fps
        mark=next((value for start,end,value in cues if start<=second<end),'X')
        vals.append(mark)
    def groups():
        runs=[]
        for i,v in enumerate(vals):
            if runs and MOUTHS.get(runs[-1][2],0)==MOUTHS.get(v,0):
                runs[-1][1]=i+1
            else:
                runs.append([i,i+1,v])
        return runs
    # One- and two-frame intra-word flashes are too short for the replacement
    # mouth to read. Preserve the longer neighboring phoneme and any line silence.
    while True:
        runs=groups()
        short=next((i for i,(a,b,v) in enumerate(runs)
                    if 0<i<len(runs)-1 and b-a<3),None)
        if short is None:
            break
        a,b,_=runs[short]
        prev,next_=runs[short-1],runs[short+1]
        candidate=prev if prev[1]-prev[0]>=next_[1]-next_[0] else next_
        vals[a:b]=[candidate[2]]*(b-a)
    return ''.join(vals)

def line_viseme(clip,frame,fps=24):
    """Use the existing Rhubarb timing with a three-exposure minimum for inner cues."""
    if clip is None or not clip['start']<=frame<clip['end']:
        return 'X'
    cues=tuple((s['start'],s['end'],s['value']) for s in clip['shapes'])
    return _held_visemes(cues,clip['end']-clip['start'],fps)[frame-clip['start']]


def line_gesture(clip,frame):
    """A single semantic beat on the first model or closing invitation."""
    if clip is None or not clip['start']<=frame<clip['end']:
        return None
    invited=clip['role']=='S' and clip['kind']=='cue' and clip['start'] in {400,2315,3021}
    shown=clip['role'] in {'1','2'} and clip['kind']=='repeat' and clip['wav'] in {'02','04','12','13'}
    if clip['kind'] not in {'lead','model'} and not (invited or shown):
        return None
    length=clip['end']-clip['start']
    p=(frame-clip['start'])/max(1,length-1)
    return max(0.,min(1.,(p-.07)/.87))
