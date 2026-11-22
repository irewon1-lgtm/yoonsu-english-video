"""Fixed-camera photographic 2D cel animation. Paint one registered scene per frame."""
import argparse
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from multiprocessing import Pool
from pathlib import Path
import subprocess
from PIL import Image, ImageOps
import cairocffi as cairo

from drawing import paint, surface
from whole_render_tools import encode, label_caption, mouth, title

ROOT=Path(__file__).resolve().parent
BASE=ROOT/'assets/base'
FIXED=ROOT/'assets/registered'
SHOTS=ROOT/'shots'
OVERRIDES=ROOT/'overrides'
WIDTH,HEIGHT=1280,720
W,H=1920,1080
FPS=24
TAKES={
 'alarm':'dlg-alarm-speech','wake':'dlg-bedroom-pj','wash':'dlg-bath-pj',
 'breakfast':'dlg-kitchen-pj','brush':'dlg-bath-pj','dress':'dlg-bedroom-dress',
 'socks':'dlg-bedroom-socks','mirror':'dlg-mirror','search':'dlg-search',
 'find':'dlg-bedroom-day-bag','shoes':'dlg-entry-day','depart':'dlg-entry-pack',
 'street':'dlg-street-speech','arrive':'dlg-arrive-speech','hello':'dlg-school-day',
}

@lru_cache(maxsize=1)
def read():
    sources=json.loads((ROOT/'whole-scene.json').read_text())['sheets']
    path=OVERRIDES/'dialogue'/'index.json'
    if path.is_file():
        edits=json.loads(path.read_text())['sheets']
        sources.update({k:dict(r['descriptor'],registered_dialogue=True) for k,r in edits.items()})
    motion=ROOT/'extra-sheets.json'
    if motion.is_file():
        sources.update(json.loads(motion.read_text()))
    return json.loads((ROOT/'timeline.json').read_text()),sources

def round_border(i,m,size):
    return round(i*size/m)

def best_sheet(name):
    info=read()[1][name]
    if info.get('registered_dialogue'):
        return OVERRIDES/'dialogue'/info['file']
    file=FIXED/info['file']
    return file if file.is_file() else BASE/info['file']

@lru_cache(maxsize=12)
def sheet(name):
    path=best_sheet(name)
    with Image.open(path) as im:
        return im.convert('RGB')

def normalize_full(im):
    return ImageOps.fit(im.convert('RGB'),(WIDTH,HEIGHT),method=Image.Resampling.LANCZOS)

@lru_cache(maxsize=48)
def from_atlas(name,number):
    conf=read()[1][name]
    im=sheet(name)
    cols,rows=conf['grid']
    col,row=number%cols,number//cols
    assert row<rows,(name,number)
    x=conf.get('x',[round_border(i,cols,im.width) for i in range(cols+1)])
    y=conf.get('y',[round_border(i,rows,im.height) for i in range(rows+1)])
    b=conf.get('inset',1)
    rectangle=(x[col]+b,y[row]+b,x[col+1]-b,y[row+1]-b)
    camera=normalize_full(im.crop(rectangle))
    if name=='dlg-entry-day':
        # A single stationary dialogue framing. The subsequent action shot
        # establishes the available shoe and the already shod foot before movement.
        camera=normalize_full(camera.crop((134,22,1174,607)))
    return surface(camera)

@dataclass
class Clip:
    folder:Path
    record:dict
    frames:tuple
    holds:tuple
    starts:tuple
    duration:int

@lru_cache(maxsize=30)
def clip(folder_text):
    folder=Path(folder_text)
    record=json.loads((folder/'index.json').read_text())
    assert int(record.get('fps',24))==24,folder
    frames=tuple(record['frames'])
    hs=record['exposure_frames']
    holds=(hs,)*len(frames) if isinstance(hs,int) else tuple(hs)
    assert len(holds)==len(frames) and all(isinstance(i,int) and i>0 for i in holds),folder
    starts=[];last=0
    for v in holds:
        starts.append(last);last+=v
    assert last>0
    return Clip(folder,record,frames,holds,tuple(starts),last)

@lru_cache(maxsize=48)
def from_clip(folder,cell):
    c=clip(folder)
    with Image.open(c.folder/c.frames[cell]) as im:
        picture=im.convert('RGBA')
    x,y,w,h=c.record.get('dest',(0,0,1,1))
    extent=(round(w*WIDTH),round(h*HEIGHT))
    pivot=(round(x*WIDTH),round(y*HEIGHT))
    if c.record.get('plate'):
        with Image.open(c.folder/c.record['plate']) as p:
            frame=p.convert('RGBA').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
        frame.alpha_composite(picture.resize(extent,Image.Resampling.LANCZOS),pivot)
    elif c.record.get('plates'):
        with Image.open(c.folder/c.record['plates'][cell]) as p:
            frame=p.convert('RGBA').resize((WIDTH,HEIGHT),Image.Resampling.LANCZOS)
        frame.alpha_composite(picture.resize(extent,Image.Resampling.LANCZOS),pivot)
    else:
        frame=picture
        assert frame.getchannel('A').getextrema()==(255,255),(folder,cell,'requires one locked plate')
    return surface(normalize_full(frame))

def dialog_cell(name,line,frame):
    conf=read()[1][name]
    if not line:return 0
    table=conf.get('cast',{}).get(line['role'],{})
    return table.get(mouth(line,frame),0)

@dataclass(frozen=True)
class Shot:
    start:int
    end:int
    kind:str
    key:str
    cels:tuple=()
    offset:int=0

def encoded_stages(key,turn,scene_count):
    """Expose actual positions during action, and hold only at intentional contacts."""
    rows=[]
    def add(a,b,m,k,cels=(),offset=0):
        if a>=b:return
        rows.append(Shot(a,b,m,k,tuple(cels),offset))
    def dg(a,b,stem=None):
        add(a,b,'speak',stem or TAKES[key])
    def act(a,b,stem,moves):
        bundle=[]
        span=b-a
        assert span>=len(moves), (key,a,b)
        choice=[(i,int(d)) for i,d in moves]
        total=sum(d for _,d in choice)
        if total>span:
            ends=[round(sum(h for _,h in choice[:i+1])*span/total) for i in range(len(choice))]
            choice=[(p,max(1,e-(ends[i-1] if i else 0))) for i,((p,_),e) in enumerate(zip(choice,ends))]
        if sum(h for _,h in choice)<span:
            choice[-1]=(choice[-1][0],choice[-1][1]+span-sum(h for _,h in choice))
        assert sum(h for _,h in choice)==span,(key,a,b)
        add(a,b,'atlas',stem,choice)
    def source(a,b,name,offset=0):
        folder=ROOT/'legacy-actions'/name
        add(a,b,'retime',str(folder),offset=offset)
    def compound(a,b,original,moves,timing):
        candidate='compound-'+original[4:]
        if candidate in read()[1]:
            act(a,b,candidate,list(enumerate(timing)))
        else:
            act(a,b,original,moves)
    def override(a,b):
        local=OVERRIDES/key
        if not (local/'index.json').is_file():return False
        c=clip(str(local));used=min(c.duration,b-a)
        add(a,a+used,'clip',str(local))
        if a+used<b:add(a+used,b,'clip',str(local),offset=c.duration-1)
        return True
    L=scene_count;q=turn
    if key=='alarm':
        act(0,9,'act-alarm',[(0,9)])
        dg(9,q+3)
        act(q+3,L,'act-alarm-press',[(0,8),(1,5),(2,3),(3,4),(4,4),(5,8)])
    elif key=='wake':
        if not override(0,132):
            source(0,132,'wake')
        d=OVERRIDES/'wake'
        if (d/'index.json').is_file():
            add(132,146,'still',str(d),offset=clip(str(d)).duration-1)
        else:
            add(132,146,'still',str(ROOT/'legacy-actions'/'wake'),offset=clip(str(ROOT/'legacy-actions'/'wake')).duration-1)
        dg(146,L)
    elif key=='wash':
        dg(0,q+3)
        compound(q+3,L,'act-wash',[(0,6),(1,7),(2,10),(3,12),(4,13),(5,5)],
                 [5,2,2,3,3,2,3,6,6,3,3,5])
    elif key=='breakfast':
        dg(0,q+3)
        compound(q+3,L,'act-breakfast-eat',[(0,8),(1,6),(2,8),(3,10),(4,7),(5,9)],
                 [6,2,3,2,3,2,3,6,3,3,3,5])
    elif key=='brush':
        dg(0,q+3)
        act(q+3,L,'compound-brush',[(0,7),(3,5),(5,4),(6,6),(8,8),(10,6)])
    elif key=='dress':
        dg(0,q+3)
        source(q+3,L,'dress')
    elif key=='socks':
        dg(0,q+3)
        source(q+3,L,'socks')
    elif key=='mirror':
        dg(0,q+3)
        act(q+3,L,'act-mirror',[(2,10),(3,10)])
    elif key=='search':
        act(0,28,'act-search-walk',[(0,4),(1,4),(2,6),(3,7)])
        dg(28,253)
        act(253,L,'act-search-crouch',[(1,6),(2,8),(3,9)])
    elif key=='find':
        dg(0,q+3)
        compound(q+3,L,'act-bag-find',[(0,11),(1,8),(2,8),(3,8),(4,7),(5,13)],
                 [6,2,3,2,3,2,3,4,3,3,4,5])
    elif key=='shoes':
        cutoff=q-76
        dg(0,cutoff)
        path=OVERRIDES/'shoes'
        add(cutoff,q,'still',str(path),offset=0)
        if not override(q,L):source(q,L,'shoes')
    elif key=='depart':
        cutoff=q-76
        dg(0,cutoff)
        add(cutoff,q,'still',str(OVERRIDES/'depart'),offset=0)
        if not override(q,L):source(q,L,'depart_volume_cut')
    elif key=='street':
        act(0,36,'act-street-reach',[(0,7),(1,6),(2,6),(3,8),(4,9)])
        dg(36,q+3)
        source(q+3,L,'street_volume',30)
    elif key=='arrive':
        dg(0,q+3)
        source(q+3,L,'arrive_volume',75)
    elif key=='hello':
        dg(0,q+3)
        source(q+3,L,'hello_volume')
    assert rows and rows[0].start==0 and rows[-1].end==L
    assert all(a.end==b.start for a,b in zip(rows,rows[1:])),(key,rows)
    return rows

class Film:
    def __init__(self):
        self.data,_=read()
        self.scenes=self.data['scenes']
        self.starts=[s['start'] for s in self.scenes]
        self.voices=[[] for s in self.scenes]
        self.stages=[]
        for d in self.data['dialogue']:
            self.voices[bisect_right(self.starts,d['start'])-1].append(d)
        for s in self.scenes:
            self.stages.append(encoded_stages(s['key'],s['turn'][1]-s['start'],s['end']-s['start']))

    def info(self,n):
        i=bisect_right(self.starts,n)-1
        sc=self.scenes[i];local=n-sc['start']
        line=next((d for d in self.voices[i] if d['start']<=n<d['end']),None)
        take=next(x for x in self.stages[i] if x.start<=local<x.end)
        if take.kind=='speak':
            cell=dialog_cell(take.key,line,n)
        elif take.kind in {'clip','retime','still'}:
            c=clip(take.key)
            rel=0 if take.kind=='still' else local-take.start
            available=c.duration-take.offset
            span=take.end-take.start
            if take.kind=='retime' and available>span:
                rel=round(rel*(available-1)/max(1,span-1))
            i1=min(c.duration-1,rel+take.offset)
            cell=bisect_right(c.starts,i1)-1
        else:
            remaining=local-take.start
            for cell,hold in take.cels:
                if remaining<hold:break
                remaining-=hold
        return sc,line,take,cell

    def draw(self,canvas,n,width):
        c=cairo.Context(canvas);c.scale(width/WIDTH,width/WIDTH)
        sc,line,take,cell=self.info(n)
        still=from_clip(take.key,cell) if take.kind in {'clip','retime','still'} else from_atlas(take.key,cell)
        paint(c,still,0,0,WIDTH,HEIGHT)
        a,b,text=sc['turn']
        if a<=n<b:
            label_caption(c,'Y',text,True,True)
        elif line:
            label_caption(c,line['role'],line['line'],False,False)
        if n<58:title(c)
        if self.data['frames']-42<=n:title(c,True)

def clip_range(args):
    i,first,last,w=args
    f=Film()
    path=SHOTS/f'{i:02d}.mp4'
    def render(c,j,width):f.draw(c,first+j,width)
    encode(path,last-first,render,width=w)
    n=f.scenes[i-1]['key']
    print(n,last-first,'rendered',flush=True)
    return path

def mux(paths,target,start,end,with_audio=True):
    manifest=SHOTS/(target.stem+'.txt')
    manifest.write_text(''.join(f"file '{p.resolve()}'\n" for p in paths))
    cmd=['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',str(manifest)]
    if with_audio:
        cmd+=['-ss',str(start/FPS),'-i',str(ROOT/'mix.wav'),'-map','0:v','-map','1:a','-c:a','aac','-b:a','128k']
    cmd+=['-t',str((end-start)/FPS),'-c:v','copy','-movflags','+faststart',str(target)]
    subprocess.run(cmd,check=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path)
    p.add_argument('--jobs',type=int,default=3)
    p.add_argument('--frame',type=int)
    p.add_argument('--range',nargs=2,type=int)
    p.add_argument('--gate',action='store_true')
    p.add_argument('--width',type=int,default=W)
    a=p.parse_args();w=a.width
    SHOTS.mkdir(exist_ok=True)
    f=Film()
    if a.frame is not None:
        out=cairo.ImageSurface(cairo.FORMAT_RGB24,w,w*9//16)
        f.draw(out,a.frame,w);out.write_to_png(str(a.out))
    elif a.range:
        start,last=a.range
        path=SHOTS/(a.out.stem+'-picture.mp4')
        encode(path,last-start,lambda c,n,w0:f.draw(c,n+start,w0),width=w)
        mux([path],a.out,start,last)
    elif a.gate:
        scenes={s['key']:s for s in f.scenes}
        windows=[('wake',0,154),('shoes',172,288),('depart',195,504)]
        ranges=[(scenes[name]['start']+a,scenes[name]['start']+b) for name,a,b in windows]
        frame_ids=[n for a,b in ranges for n in range(a,b)]
        assert 24<=len(frame_ids)/24<=30
        encode(a.out,len(frame_ids),lambda c,n,w0:f.draw(c,frame_ids[n],w0),width=w)
    else:
        with Pool(a.jobs) as pool:
            paths=pool.map(clip_range,[(i+1,s['start'],s['end'],w) for i,s in enumerate(f.scenes)])
        mux(paths,a.out or ROOT/'Good_Morning_Yoonsu_2D_Sprites_1080p.mp4',0,f.data['frames'])

if __name__=='__main__':
    main()
