"""Morning Daycare renderer. Draw unchanged exposures and compose fixed planes."""
import argparse
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import json
import hashlib
import sys
import subprocess
from multiprocessing import Pool

import cairocffi as cairo
from PIL import Image,ImageFilter
from drawing import color,label,paint,pill,shadow,surface
from edit import FPS,ROOT
from exposures import action,available,walk_at

ASSETS=ROOT/'assets'
W,H=1920,1080
WIDTH,HEIGHT=1280,720
sys.path.insert(0,str(ASSETS/'friends'))
from friends_motion import draw_actor,line_viseme

CAST={
    'S':('SHERIFF LABRADOR','#46558a'),
    'Y':('YOONSU','#246757'),
    'G':('PARENT','#765159'),
    'T':('TEACHER','#815039'),
}
GATE=('wake','shoes','depart')
TITLE='Good Morning, Yoonsu!'
STAGE={
    'bedroom':(858,637,335,320,646,269),
    'bath':(640,650,350,278,626,270),
    'kitchen':(607,644,342,956,627,273),
    'entry':(530,649,346,1006,628,282),
    'street':(495,625,322,823,625,269),
    'school':(518,622,339,253,626,267),
}
ACTION_FIRST={'alarm','wake','mirror','search','arrive'}

@lru_cache(95)
def texture(path:Path):
    with Image.open(path) as im:
        image=im.convert('RGBA' if 'A' in im.mode or 'transparency' in im.info else 'RGB')
        return surface(image)

@lru_cache(10)
def background(key,soft=False):
    path=ASSETS/'sets'/f'{key}.png'
    if key=='bath':
        path=ASSETS/'bath.png'
    if not path.exists() and key=='bedroom':
        path=ASSETS/'bedroom-reference.png'
    if not soft:
        return texture(path)
    with Image.open(path) as im:
        return surface(im.convert('RGB').filter(ImageFilter.GaussianBlur(7)))

def draw(c,asset,x=0,y=0,w=WIDTH,h=HEIGHT):
    paint(c,asset,x,y,w,h)

@lru_cache(28)
def head_image(shape='X',blink=False,pajamas=False):
    names='XABCDEFGH'
    idx=names.index(shape)
    w,h=836,816
    x,y=idx%3*w,idx//3*h
    filename='pajama-atlas.png' if pajamas else 'atlas.png'
    with Image.open(ASSETS/'portrait'/filename) as sheet:
        im=sheet.crop((x,y,x+w,y+h)).convert('RGBA')
    if blink:
        with Image.open(ASSETS/'portrait/closed-eyes.png') as eyes:
            im.paste(eyes,(282,278))
    return surface(im)

def mouth(segment,n):
    if not segment:
        return 'X'
    elapsed=(n-segment['start']+.5)/FPS
    return next((s['value'] for s in segment['shapes'] if s['start']<=elapsed<s['end']),'X')

def show_cel(c,key,offset):
    clip=action(key)
    plate=clip.plate_at(offset)
    if plate:
        draw(c,texture(plate))
    else:
        # Independent full-camera opaque exposures define their own stage.
        color(c,'#141b23')
        c.paint()
    x,y,w,h=clip.dest
    draw(c,texture(clip.path_at(offset)),x*WIDTH,y*HEIGHT,w*WIDTH,h*HEIGHT)

def label_caption(c,who,line,wait=False,upper=False):
    caption,color_=CAST[who]
    caption='YOUR TURN, YOONSU!' if wait else caption
    c.select_font_face('DejaVu Sans',0,1)
    c.set_font_size(35)
    w=max(363,c.text_extents(line)[2]+95)
    x=(WIDTH-w)/2
    y=87 if upper else 605
    pill(c,x,y+4,w,70,'#2c3d49')
    pill(c,x,y,w,70,'#fff7e2')
    c.set_font_size(15)
    tw=c.text_extents(caption)[2]+42
    pill(c,(WIDTH-tw)/2,y-13,tw,25,'#2f735d' if wait else color_)
    label(c,caption,WIDTH/2,y+4,15,'#ffffff',align='center')
    label(c,line,WIDTH/2,y+49,35,'#233b49',align='center')

def title(c,ending=False):
    if ending:
        pill(c,481,88,318,56,'#234e65')
        label(c,'See you soon!',640,125,32,'#fff6d4','URW Bookman',align='center')
        return
    grad=cairo.LinearGradient(0,0,830,280)
    grad.add_color_stop_rgba(0,.055,.18,.22,.92)
    grad.add_color_stop_rgba(.57,.10,.26,.30,.44)
    grad.add_color_stop_rgba(1,.10,.26,.30,0)
    c.set_source(grad)
    c.paint()
    label(c,'Good Morning,',71,194,85,'#fff6dc','URW Bookman')
    label(c,'Yoonsu!',73,290,110,'#ffdf9f','URW Bookman')
    label(c,'좋은 아침, 어린이집 가자!',79,351,29,'#fff4dc','Noto Sans CJK KR')

def planar_child(c,img,x,y,h,*,anchor=(384,707),native_h=629):
    sc=h/native_h
    shadow(c,x,y+3,h*.14,10)
    draw(c,img,x-anchor[0]*sc,y-anchor[1]*sc,img.get_width()*sc,img.get_height()*sc)

def stage_y(c,scene,pose,age):
    x,feet,height,*_=STAGE[scene['set']]
    key=scene['key']
    if pose=='walk':
        path,dx,feet_contact=walk_at(age)
        scale=height/474
        center=x+(dx-272.35)*scale
        planar_child(c,texture(path),center,feet,height,anchor=(256,494),native_h=474)
    else:
        costume=scene['costume']
        candidate='pajama.webp' if costume.startswith('pajamas') else 'day.webp'
        if pose=='wave':
            number=min(8,max(0,age//3))
            tex=texture(ASSETS/'late/wave'/f'{number:02}.webp')
        else:
            source=ASSETS/'base'/candidate
            tex=texture(source if source.exists() else ASSETS/'base/day.webp')
        planar_child(c,tex,x,feet,height)

def sheriff(c,x,feet,height,n,seg=None,gesture=None):
    shadow(c,x,feet+4,height*.2,10)
    draw_actor(c,'S',x,feet,height,'morning',n/FPS,line_viseme(seg,n),gesture)

def world(c,scene,n,seg,pose='idle'):
    _,_,_,sx,sy,sh=STAGE[scene['set']]
    draw(c,background(scene['set']))
    stage_y(c,scene,pose,n-scene['start'])
    local=n-scene['start']
    gesture=None
    if seg and seg['role']=='S':
        gesture=min(1.,(n-seg['start'])/max(1,seg['end']-seg['start']-1))
    elif local in range(4,39):
        gesture=(local-4)/34
    sheriff(c,sx,sy,sh,n,seg if seg and seg['role']=='S' else None,gesture)

@lru_cache(8)
def conversation_plate(key,place):
    clip=action(key)
    plate=clip.plate_at(0)
    if plate is None:
        return background(place,True)
    with Image.open(plate) as image:
        return surface(image.convert('RGB').filter(ImageFilter.GaussianBlur(6)))

def dialogue_image(c,scene,seg,n):
    draw(c,conversation_plate(scene['key'],scene['set']))
    who=seg['role'] if seg else ''
    exposed=seg if who=='Y' else None
    blink=not seg and n-scene['lead'] in {48,49}
    y=head_image(mouth(exposed,n),blink,scene['costume'].startswith('pajamas'))
    pose_height=570
    hero_right=scene['set'] in {'bedroom','school'}
    hero_x=675 if hero_right else 158
    dog_x=380 if hero_right else 891
    # An approved head-and-shoulders two-shot with the listening Sheriff beside
    # Yoonsu. Action inserts carry all hand and prop contacts.
    draw(c,y,hero_x,156,552,pose_height)
    phase=None
    if who=='S':
        phase=(n-seg['start'])/max(1,seg['end']-seg['start']-1)
    sheriff(c,dog_x,787,535,n,seg if who=='S' else None,phase)

@dataclass(frozen=True)
class Shot:
    first:int
    last:int
    kind:str
    key:str
    offset:int=0

def assemble(scene,utterances):
    key=scene['key']
    first,last=scene['start'],scene['end']
    turn=scene['turn']
    action_clip=action(key)
    slot=first if key in ACTION_FIRST else (turn[1]+7 if turn else first)
    assert slot+action_clip.duration<=last,(key,slot,action_clip.duration,last)
    cuts=[]
    if slot>first:
        begin=first
        if key=='shoes' and available('shoes_prepare'):
            ready=action('shoes_prepare')
            assert first+ready.duration<scene['lead']-5
            cuts.append(Shot(first,first+ready.duration,'act','shoes_prepare'))
            begin+=ready.duration
        cuts.append(Shot(begin,slot,'hold',key))
    cuts.append(Shot(slot,slot+action_clip.duration,'act',key))
    finish=slot+action_clip.duration
    if key=='wake' and available('wake_stretch'):
        follow=action('wake_stretch')
        assert finish+follow.duration<scene['lead']-5
        cuts.append(Shot(finish,finish+follow.duration,'act','wake_stretch'))
        finish+=follow.duration
    if finish<last:
        cuts.append(Shot(finish,last,'hold',key,action_clip.duration-1))
    # Dialogue overlays are timed separately from the action. The learned line
    # may start at a still position, but the wait never advances a physical action.
    return cuts

class Film:
    def __init__(self):
        self.edit=json.loads((ROOT/'timeline.json').read_text())
        self.scenes=self.edit['scenes']
        self.starts=[s['start'] for s in self.scenes]
        self.lines=[[] for _ in self.scenes]
        for seg in self.edit['dialogue']:
            self.lines[bisect_right(self.starts,seg['start'])-1].append(seg)


    def shots(self,i):
        if not available(self.scenes[i]['key']):
            raise FileNotFoundError(self.scenes[i]['key']+' missing from scheduled action plates')
        return assemble(self.scenes[i],self.lines[i])

    def frame(self,c,n):
        i=bisect_right(self.starts,n)-1
        sc=self.scenes[i]
        turn=sc['turn']
        current=next((d for d in self.lines[i] if d['start']<=n<d['end']),None)
        shot=next(s for s in self.shots(i) if s.first<=n<s.last)
        loc=n-shot.first+shot.offset if shot.kind=='act' else shot.offset
        sync_range=self.lines[i]
        first,last=sync_range[0]['start']-5,sync_range[-1]['end']+4
        paired=sc['key'] not in {'alarm','street','arrive'}
        if paired and shot.kind=='hold' and first<=n<last:
            dialogue_image(c,sc,current,n)
        else:
            show_cel(c,shot.key,loc)
        if sc['key']=='socks' and shot.kind=='act':
            phase=None if loc<70 or loc>=116 else (loc-70)/45
            c.save()
            c.translate(1280,0)
            c.scale(-1,1)
            sheriff(c,159,660,273,n,gesture=phase)
            c.restore()
        if turn and turn[0]-2<=n<=turn[1]+2:
            label_caption(c,'Y',turn[2],True,True)
        elif current:
            label_caption(c,current['role'],current['line'],False,shot.kind=='act')
        if sc['key']=='socks' and n-sc['start']<27:
            pill(c,47,42,233,42,'#204852')
            label(c,'A moment later',64,71,24,'#fff8df','URW Bookman')
        if n<58:
            title(c)
        if self.edit['frames']-52<=n:
            title(c,True)

    def paint(self,surf,n,width):
        c=cairo.Context(surf)
        c.scale(width/WIDTH,width/WIDTH)
        self.frame(c,n)

def encode(path,count,draw_frame,*,width=W):
    height=width*9//16
    out=cairo.ImageSurface(cairo.FORMAT_RGB24,width,height)
    spec=['ffmpeg','-nostdin','-v','error','-y','-f','rawvideo','-pixel_format','bgr0',
          '-video_size',f'{width}x{height}','-framerate',str(FPS),'-i','-','-an','-filter_threads','1',
          '-vf','scale=out_color_matrix=bt709,format=yuv420p','-c:v','libx264','-threads','2','-preset','veryfast',
          '-crf','18','-maxrate','2900k','-bufsize','4600k','-g','48','-colorspace','bt709','-color_trc','bt709',
          '-color_primaries','bt709','-movflags','+faststart',str(path)]
    with subprocess.Popen(spec,stdin=subprocess.PIPE) as ffmpeg:
        for n in range(count):
            draw_frame(out,n,width)
            out.flush()
            ffmpeg.stdin.write(out.get_data())
        ffmpeg.stdin.close()
        if ffmpeg.wait():
            raise RuntimeError(path)

def shot_fingerprint(f,i):
    sc=f.scenes[i]
    clip=action(sc['key'])
    h=hashlib.sha256(json.dumps([sc,f.lines[i],clip.record],sort_keys=True).encode())
    sources=[Path(__file__),ROOT/'drawing.py',ROOT/'exposures.py',ASSETS/'portrait/atlas.png',
             ASSETS/'portrait/pajama-atlas.png',ASSETS/'portrait/closed-eyes.png',
             ASSETS/'friends/sheriff-2x.png',ASSETS/'friends/atlas.json',ASSETS/'friends/friends_motion.py']
    sources.extend(clip.directory/path for path in sorted(set(clip.files)))
    if clip.plate:
        sources.append(clip.plate)
    elif clip.plates:
        sources.extend(sorted(set(clip.plates)))
    else:
        bg=ASSETS/'bath.png' if sc['set']=='bath' else ASSETS/'sets'/f"{sc['set']}.png"
        if bg.is_file():
            sources.append(bg)
    extras={'wake':'wake_stretch','shoes':'shoes_prepare'}
    optional=extras.get(sc['key'])
    if optional and available(optional):
        follow=action(optional)
        sources.append(follow.directory/'index.json')
        sources.extend(follow.directory/source for source in follow.files)
        if follow.plate:
            sources.append(follow.plate)
    for path in sources:
        with path.open('rb') as inp:
            h.update(hashlib.file_digest(inp,'sha256').digest())
    return h.hexdigest()

def render_piece(i):
    f=Film()
    sc=f.scenes[i]
    clips=ROOT/'shots'
    clips.mkdir(exist_ok=True)
    path=clips/f'{i+1:02d}.mp4'
    fingerprint=shot_fingerprint(f,i)
    stamp=path.with_suffix('.sha256')
    if path.is_file() and stamp.is_file() and stamp.read_text()==fingerprint:
        print(sc['key'],'cached',flush=True)
        return
    temp=path.with_suffix('.new.mp4')
    encode(temp,sc['end']-sc['start'],lambda c,n,w:f.paint(c,sc['start']+n,w))
    temp.replace(path)
    stamp.write_text(fingerprint)
    print(sc['key'],sc['end']-sc['start'],flush=True)

def concat(paths,name,with_mix=False):
    manifest=ROOT/'shots'/f'{name}.txt'
    manifest.parent.mkdir(exist_ok=True)
    lines=['file '+"'"+str(p).replace("'","'\\''")+"'\n" for p in paths]
    manifest.write_text(''.join(lines))
    cmd=['ffmpeg','-nostdin','-y','-v','error','-f','concat','-safe','0','-i',str(manifest)]
    if with_mix:
        cmd+=['-i',str(ROOT/'mix.wav'),'-map','0:v','-map','1:a',
              '-c:a','aac','-b:a','128k']
    cmd+=['-c:v','copy','-movflags','+faststart',str(ROOT/(name+'.mp4'))]
    subprocess.run(cmd,check=True)

def gate(*keys):
    dest=ROOT/'shots'
    dest.mkdir(exist_ok=True)
    paths=[]
    durations=[]
    for key in (keys or GATE):
        clip=action(key)
        path=dest/f'check-{key}.mp4'
        def draw_gate(out,n,w):
            c=cairo.Context(out)
            c.scale(w/WIDTH,w/WIDTH)
            show_cel(c,key,n)
        encode(path,clip.duration,draw_gate)
        paths.append(path)
        durations.append(clip.duration)
        print(key,clip.duration,'frames in verification',flush=True)
    if not keys:
        assert 24*FPS<=sum(durations)<=30*FPS,durations
    concat(paths,'Animation_Check_1080p' if not keys else 'Motion_Review')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--gate',nargs='*')
    p.add_argument('--frame',type=int)
    p.add_argument('--width',type=int,default=W)
    p.add_argument('--out',type=Path)
    p.add_argument('--pieces')
    p.add_argument('--jobs',type=int,default=3)
    a=p.parse_args()
    if a.gate is not None:
        gate(*a.gate)
    elif a.frame is not None:
        out=cairo.ImageSurface(cairo.FORMAT_RGB24,a.width,a.width*9//16)
        Film().paint(out,a.frame,a.width)
        out.write_to_png(str(a.out))
    else:
        f=Film()
        indices=[int(i)-1 for i in a.pieces.split(',')] if a.pieces else range(len(f.scenes))
        with Pool(a.jobs) as workers:
            workers.map(render_piece,indices,chunksize=1)
        parts=[ROOT/'shots'/f'{i+1:02}.mp4' for i in range(len(f.scenes))]
        if all(p.is_file() for p in parts):
            concat(parts,'Good_Morning_Yoonsu_1080p',True)
