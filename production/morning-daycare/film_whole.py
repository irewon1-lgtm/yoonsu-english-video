"""Picture editor for authored, opaque, whole-camera sprite-sheet cels."""
import argparse
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
import hashlib
import json
from multiprocessing import Pool
from pathlib import Path
import subprocess

import cairocffi as cairo
from PIL import Image, ImageOps

from drawing import paint, surface
from whole_render_tools import FPS, H, ROOT, W, concat, encode, label_caption, mouth, title

CANVAS=(1280,720)
ASSETS=ROOT/'assets/whole-scene'
MANIFEST=ROOT/'whole-scene.json'
CEL_STAGE=ROOT/'shots-whole'
GATE_RANGES=((288,479),(3881,4049),(4284,4600))


@dataclass(frozen=True)
class Span:
    start: int
    end: int
    sheet: str
    mode: str
    cels: tuple


@lru_cache(maxsize=1)
def catalog():
    return json.loads(MANIFEST.read_text())


@lru_cache(maxsize=22)
def sheet(path):
    with Image.open(path) as picture:
        return picture.convert('RGB')


def cel_image(name,index):
    setup=catalog()['sheets'][name]
    src=sheet(ASSETS/setup['file'])
    columns,rows=setup['grid']
    if not 0<=index<columns*rows:
        raise IndexError((name,index,columns,rows))
    col,row=index%columns,index//columns
    if 'x' in setup:
        x=setup['x']
    else:
        x=[round(i*src.width/columns) for i in range(columns+1)]
    if 'y' in setup:
        y=setup['y']
    else:
        y=[round(i*src.height/rows) for i in range(rows+1)]
    box=(x[col],y[row],x[col+1],y[row+1])
    # Every tile contains a full rendered frame. The fixed inset excludes only any grid line.
    edge=setup.get('inset',1)
    box=(box[0]+edge,box[1]+edge,box[2]-edge,box[3]-edge)
    still=src.crop(box)
    return ImageOps.fit(still,CANVAS,method=Image.Resampling.LANCZOS)


@lru_cache(maxsize=36)
def exposure(name,index):
    return surface(cel_image(name,index))


def dialogue_index(setup,segment,frame):
    if not segment or segment['role'] not in setup.get('cast',{}):
        return 0
    shape=mouth(segment,frame)
    lookup=setup['cast'][segment['role']]
    return lookup.get(shape,lookup.get('default',0))


class WholeFilm:
    def __init__(self, draft=False):
        self.edit=json.loads((ROOT/'timeline.json').read_text())
        self.scenes=self.edit['scenes']
        self.starts=[scene['start'] for scene in self.scenes]
        self.lines=[[] for scene in self.scenes]
        for line in self.edit['dialogue']:
            self.lines[bisect_right(self.starts,line['start'])-1].append(line)
        self.spans=[]
        for s in self.scenes:
            plan=catalog()['timeline'].get(s['key'],[])
            start=s['start']
            spans=[]
            for after,sheet_name,mode,*args in plan:
                end=s['start']+after
                assert start<end<=s['end'],(s['key'],start,end)
                assert mode in ('hold','speech','motion'),mode
                if not draft:
                    assert sheet_name in catalog()['sheets'],(s['key'],sheet_name)
                cels=tuple(tuple(p) if isinstance(p,list) else p for p in args[0]) if args else ()
                if mode=='motion':
                    assert cels and sum(hold for _,hold in cels)==end-start,(s['key'],cels,end-start)
                spans.append(Span(start,end,sheet_name,mode,cels))
                start=end
            assert start==s['end'] or draft,(s['key'],start,s['end'])
            self.spans.append(spans)

    def source_at(self,frame):
        i=bisect_right(self.starts,frame)-1
        sc=self.scenes[i]
        segment=next((line for line in self.lines[i] if line['start']<=frame<line['end']),None)
        selected=next((p for p in self.spans[i] if p.start<=frame<p.end),None)
        if selected is None:
            raise ValueError((sc['key'],frame,'no whole-scene exposure'))
        if selected.mode=='speech':
            cel=dialogue_index(catalog()['sheets'][selected.sheet],segment,frame)
        elif selected.mode=='motion':
            remaining=frame-selected.start
            for cel,hold in selected.cels:
                if remaining<hold:
                    break
                remaining-=hold
        else:
            cel=selected.cels[0] if selected.cels else 0
        return sc,segment,selected,cel

    def picture(self,c,frame):
        sc,segment,selected,cel=self.source_at(frame)
        turn=sc['turn']
        paint(c,exposure(selected.sheet,cel),0,0,*CANVAS)
        if turn and turn[0]-2<=frame<=turn[1]+2:
            label_caption(c,'Y',turn[2],True,True)
        elif segment:
            label_caption(c,segment['role'],segment['line'],False,selected.mode=='motion')
        if frame<58:
            title(c)
        if self.edit['frames']-52<=frame:
            title(c,True)

    def draw(self,canvas,frame,width):
        context=cairo.Context(canvas)
        context.scale(width/CANVAS[0],width/CANVAS[0])
        self.picture(context,frame)


def with_audio(silent,out,start,end):
    subprocess.run(['ffmpeg','-nostdin','-y','-v','error','-i',str(silent),
                    '-ss',str(start/FPS),'-i',str(ROOT/'mix.wav'),'-map','0:v','-map','1:a',
                    '-t',str((end-start)/FPS),'-c:v','copy','-c:a','aac','-b:a','128k',
                    '-movflags','+faststart',str(out)],check=True)


def render_part(i):
    film=WholeFilm(draft=True)
    scene=film.scenes[i]
    key=scene['key']
    target=CEL_STAGE/f'{i:02d}-{key}.mp4'
    used={p.sheet for p in film.spans[i]}
    data=catalog()
    digest=hashlib.sha256(Path(__file__).read_bytes())
    digest.update(json.dumps([scene,film.lines[i],data['timeline'][key]],sort_keys=True).encode())
    for name in sorted(used):
        conf=data['sheets'][name]
        digest.update(json.dumps(conf,sort_keys=True).encode())
        with (ASSETS/conf['file']).open('rb') as source:
            digest.update(hashlib.file_digest(source,'sha256').digest())
    fingerprint=digest.hexdigest()
    stamp=target.with_suffix('.sha256')
    if not (target.is_file() and stamp.is_file() and stamp.read_text()==fingerprint):
        encode(target,scene['end']-scene['start'],lambda out,n,w: film.draw(out,scene['start']+n,w))
        stamp.write_text(fingerprint)
    print(key,scene['end']-scene['start'],flush=True)
    return target


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--jobs',type=int,default=3)
    p.add_argument('--parts',nargs='+',type=int,metavar='SCENE')
    p.add_argument('--range',nargs=2,type=int,metavar=('FIRST','LAST'))
    p.add_argument('--frame',type=int)
    p.add_argument('--gate',action='store_true')
    p.add_argument('--out',type=Path)
    args=p.parse_args()
    CEL_STAGE.mkdir(exist_ok=True)
    if args.frame is not None:
        screen=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H)
        WholeFilm(draft=True).draw(screen,args.frame,W)
        screen.write_to_png(str(args.out))
    elif args.gate:
        film=WholeFilm()
        frames=[n for start,end in GATE_RANGES for n in range(start,end)]
        encode(args.out,len(frames),lambda out,n,w:film.draw(out,frames[n],w))
    elif args.range:
        start,end=args.range
        bare=CEL_STAGE/'audition-video.mp4'
        film=WholeFilm(draft=True)
        encode(bare,end-start,lambda out,n,w:film.draw(out,start+n,w))
        with_audio(bare,args.out,start,end)
    elif args.parts:
        with Pool(args.jobs) as pool:
            pool.map(render_part,[n-1 for n in args.parts],chunksize=1)
    else:
        film=WholeFilm()
        with Pool(args.jobs) as pool:
            rendered=pool.map(render_part,range(len(film.scenes)),chunksize=1)
        concat(rendered,'Good_Morning_Yoonsu_1080p_Whole_Sprites',True)


if __name__=='__main__':
    main()
