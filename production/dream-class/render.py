import numpy as np
"""Draw, expose and render full-body 2D sprite cels for the open-class film."""
import argparse
from bisect import bisect_right
from dataclasses import asdict, dataclass
from functools import lru_cache
from math import cos, pi, sin
from pathlib import Path
import json
import subprocess

from PIL import Image, ImageDraw, ImageFont


ROOT=Path(__file__).resolve().parent
WIDTH,HEIGHT=1536,864
FPS=24
CANVAS=(WIDTH,HEIGHT)
CELL=(408,496)
ANCHOR=(204,477)
ACTOR_HEIGHT=445
LANES=(4,4)
SHEET_SIZE=LANES[0]*LANES[1]
SHAPES={'question_one':'sun', 'teacher_star':'star', 'hands_up':'star', 'apple':'apple'}
AMPLITUDES={'X':0., 'A':.02, 'B':.19, 'C':.54, 'D':.97, 'E':.75, 'F':.59, 'G':.27, 'H':.60}
PAPER='#fff2d8'
INK='#362839'
TEAL='#163e3e'
CREAM='#fff1d5'
GOLD='#ffce6e'
FONT_REG='/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'
FONT_BOLD='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
FONT_SERIF='/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc'
FILM='Yoonsu_I_Have_a_Dream_1080p.mp4'

@dataclass(frozen=True)
class Actor:
    role:str
    x:float
    ground:float
    height:float
    kind:str='idle'
    look:float=0.
    variant:int=0

@dataclass(frozen=True)
class Pose:
    role:str
    kind:str
    look:float
    variant:int
    gesture:int
    mouth:str
    blink:int
    motion:int

def ease(u):
    u=min(1.,max(0.,u))
    return u*u*(3-2*u)

def curve(frame,a,b):
    return ease((frame-a)/max(1,b-a))

def pulse(frame, center, radius):
    return max(0.,1.-((frame-center)/radius)**2) if abs(frame-center)<radius else 0.

def value(num):
    return round(max(0,min(1,num))*48)

@lru_cache(maxsize=64)
def font(size, mode='regular'):
    source={'regular':FONT_REG,'bold':FONT_BOLD,'serif':FONT_SERIF}[mode]
    return ImageFont.truetype(source,size,index=1)

def centered(d, x, y, s, size, fill, mode='regular'):
    d.text((x,y),s,font=font(size,mode),fill=fill,anchor='mm',stroke_width=0)

def fitted(d,x,y,text,size,color, max_width=1200, mode='bold'):
    while font(size,mode).getlength(text)>max_width and size>18:
        size-=1
    centered(d,x,y,text,size,color,mode)

@lru_cache(maxsize=5)
def plate(name):
    disk=ROOT/'sets'/f'{name}.png'
    with Image.open(disk) as image:
        return image.convert('RGBA')

def shadow(im, x, y, w, strength=1.):
    shadow_width=int(w)
    h=max(12,shadow_width//4)
    offset=(round(x-shadow_width/2),round(y-h/2))
    layer=Image.new('RGBA',(shadow_width,h))
    d=ImageDraw.Draw(layer)
    for i in range(6):
        d.ellipse((i*2,i*.85,shadow_width-i*2,h-i*.85),fill=(76,44,35,int((20+i*3)*strength)))
    im.alpha_composite(layer,offset)

@lru_cache(maxsize=48)
def chair_sprite(size,color):
    w=round(size*.7)
    h=round(size)
    im=Image.new('RGBA',(w,h))
    d=ImageDraw.Draw(im)
    k=h/200
    def box(a):
        x,y,X,Y=a
        return (round(x*k),round(y*k),round(X*k),round(Y*k))
    def block(coords,radius,fill,outline=None,width=2):
        d.rounded_rectangle(box(coords),radius=round(radius*k),fill=fill,outline=outline,width=max(1,round(width*k)))
    block((23,15,118,91),20,'#b77443','#795042',4)
    block((29,20,112,80),16,'#daa36b')
    for x in (26,100):
        block((x,76,x+13,192),7,'#ac7045','#794d3e',3)
    for x in (15,111):
        block((x,122,x+15,198),7,'#c88a50','#794d3e',3)
    block((12,107,127,139),10,color,'#795040',3)
    d.line((box((24,112,116,112))[:2],box((24,112,116,112))[2:]),fill='#fff1d295',width=max(1,round(3*k)))
    return im

def chair(im,x,y,height,color='#a3bda4'):
    tex=chair_sprite(round(height),color)
    im.alpha_composite(tex,(round(x-tex.width/2),round(y-tex.height)))

@lru_cache(maxsize=9)
def card(icon,size):
    im=Image.new('RGBA',(size,size))
    d=ImageDraw.Draw(im)
    mid=(size*.5,size*.51)
    d.rounded_rectangle((7,11,size-3,size-3),radius=int(size*.095),fill='#132e3280')
    d.rounded_rectangle((2,2,size-9,size-9),radius=int(size*.096),fill=PAPER,outline='#b97956',width=3)
    d.rounded_rectangle((11,11,size-18,size-18),radius=int(size*.07),outline='#e3bb8b',width=2)
    glyph=Image.open(ROOT/'icons'/(icon+'.png')).convert('RGBA')
    side=round(size*.66)
    glyph=glyph.resize((side,side),Image.Resampling.LANCZOS)
    im.alpha_composite(glyph,((size-side)//2,(size-side)//2))
    return im

@lru_cache(maxsize=140)
def caption(en, ko, role):
    layer=Image.new('RGBA',CANVAS)
    d=ImageDraw.Draw(layer)
    pause=role=='pause'
    wide=1140
    left=(WIDTH-wide)//2
    d.rounded_rectangle((left+3,737,left+wide+3,843),radius=28,fill='#19252b48')
    d.rounded_rectangle((left,731,left+wide,837),radius=26,fill='#243448f7' if not pause else '#194542fa',outline='#ead3a5',width=2)
    role_colors={'y':'#9ed2bc','friend':'#ffaf8b','teacher':'#ffe397','mom':'#f2bdcc','sheriff':'#a8c5ff','pause':'#ffe08b'}
    d.rounded_rectangle((left+28,761,left+35,811),radius=3,fill=role_colors[role])
    fitted(d,WIDTH/2,766,en,41,'#fff7de',mode='bold',max_width=1050)
    fitted(d,WIDTH/2,812,ko,24,'#ffdec0' if pause else '#f4e5d4',mode='regular',max_width=1050)
    return layer

@lru_cache(maxsize=22)
def board_layer(key):
    layer=Image.new('RGBA',CANVAS)
    d=ImageDraw.Draw(layer)
    if key=='title':
        fitted(d,766,205,'I Have a Dream',51,'#fff2cf',max_width=620,mode='serif')
        centered(d,765,280,'윤수의 꿈 발표',27,'#e7cc9d','bold')
        d.line((589,311,941,311),fill='#ddce9870',width=2)
    elif key=='finish':
        centered(d,768,181,'I have a dream.',34,'#fcebc4','serif')
        centered(d,768,231,'What’s yours?',37,'#ffe19a','serif')
        centered(d,768,290,'윤수는 어떤 꿈을 꾸니?',23,'#f8e5bb','bold')
    elif key:
        # The same practice card remains in place during the prompt and answer.
        d.rounded_rectangle((374,97,1162,313),radius=32,fill='#6f49265c')
        d.rounded_rectangle((370,91,1158,307),radius=32,fill='#fbedd6',outline='#e1af64',width=3)
        centered(d,765,138,'I Have a Dream',24,'#73514a','bold')
        fitted(d,766,210,key,59,'#22464d',max_width=697,mode='bold')
        centered(d,764,267,'천천히, 윤수 목소리로',22,'#9b6553','regular')
    return layer

class Film:
    def __init__(self):
        self.data=json.loads((ROOT/'timeline.json').read_text())
        self.scenes=self.data['scenes']
        self.starts=[s['at'] for s in self.scenes]
        self.lips={}
        for s in self.scenes:
            for event in s['events']:
                if event['role']=='pause':continue
                name=event['id']
                p=ROOT/'audio'/'qa'/f'{name}-lips.json'
                if p.is_file():
                    cues=json.loads(p.read_text())['mouthCues']
                    self.lips[name]=([c['start'] for c in cues],[c['value'] for c in cues])

    def sample(self,n):
        scene=self.scenes[bisect_right(self.starts,n)-1]
        event=next((entry for entry in scene['events'] if entry['at']<=n<entry['end']),None)
        return scene,event,n-scene['at']

    def steps(self, scene, local):
        key=scene['id']
        if key=='arrival':
            return 'hero',[
                Actor('teacher',407,722,535,'open',1.),
                Actor('y',740,737,407,'brave',-.45),
                Actor('mom',1055,732,525,'open',-.35)]
        if key=='families':
            return 'audience',self.audience(local,scene,False,children=True)
        if key in {'question_one','teacher_star','apple'}:
            return 'teacher',[
                Actor('teacher',344,806,648,'point',.9),
                Actor('friend',1245,769,394,'seated',-.85,0 if key!='apple' else 1),
                Actor('y',1004,778,404,'seat',-.95) if key!='question_one' else Actor('friend',989,770,369,'seated',-.75,1),
                *([Actor('sheriff',1348,775,385,'encourage',-1.)] if key=='teacher_star' else [])]
        if key in {'shy','try_smaller'}:
            return 'child',[
                Actor('y',537,737,557,'shy' if key=='shy' else ('breathe' if 30<=local<71 else 'seat'),.95),
                Actor('sheriff',1115,733,555,'breathe' if key=='try_smaller' and 24<=local<72 else 'encourage',-1.)]
        if scene['view']=='practice':
            return 'child',[
                Actor('teacher',270,745,515,'open',.85),
                Actor('y',715,739,438,'brave',.8),
                Actor('sheriff',1118,734,496,'encourage',-1.)]
        if key=='hands_up':
            return 'child',[
                Actor('teacher',295,762,604,'open',1.),
                Actor('y',764,735,590,'raise',-.68),
                Actor('sheriff',1249,744,467,'listen',-1.)]
        if key=='mom_smile':
            return 'audience',self.audience(local,scene,False,children=True)
        if key=='introduce':
            x=941-138*curve(local,152,209)
            kind='seat' if local<116 else 'stand' if local<145 else 'walk' if 152<=local<210 else 'brave'
            return 'child',[
                Actor('teacher',302,780,611,'open',1.),
                Actor('y',x,739,505,kind,-.28 if local<209 else .05),
                Actor('sheriff',1244,742,430,'listen',-1.)]
        if key=='clap':
            return 'audience',self.audience(local,scene,True,children=False)
        if key=='goodbye':
            return 'hero',[
                Actor('y',542,736,406,'brave',.4),
                Actor('mom',787,737,498,'open',-.35),
                Actor('sheriff',1067,736,407,'encourage',-1.)]
        raise KeyError(key)

    @staticmethod
    def audience(local,scene,clapping,children):
        kind='clap' if clapping else 'seated'
        guardians=[Actor('parent',x,550,325,kind,0.,i) for i,x in enumerate((255,548,1000,1290))]
        guardians.insert(2,Actor('mom',770,552,430,kind,0.))
        pupils=[Actor('pupil',83+152*i,711,272,kind,0.,i if i<4 else i-1)
                if i!=4 else Actor('y',83+152*i,711,280,'classseat',0.) for i in range(10)]
        return guardians+pupils

    def mouths(self,event,n):
        if event is None or event['role']=='pause':
            return 'X'
        elapsed=(n-event['at'])/FPS+.016
        cues=self.lips.get(event['id'])
        if cues:
            return cues[1][max(0,bisect_right(cues[0],elapsed)-1)]
        return 'BDEB'[int(elapsed*8)%4] if elapsed>.08 and n+3<event['end'] else 'X'

    def pose(self,actor,scene,event,n,local,mouth):
        key=scene['id']
        role=actor.role
        speaking=event is not None and event['role']==role
        if role=='friend' and key=='apple' and actor.variant!=1:speaking=False
        if role=='friend' and key=='question_one' and actor.variant!=0:speaking=False
        if role=='friend' and key=='clap' and actor.variant!=0:speaking=False
        phoneme=mouth if speaking else 'X'
        gesture=0.
        motion=0.
        kind=actor.kind
        if role=='y':
            if key=='hands_up':
                # Full-body one-frame cels from anticipation through contact and release.
                gesture=curve(local,20,47)*(1-curve(local,157,176))
            elif kind=='stand':
                motion=curve(local,116,145)
            elif kind=='walk':
                # Heel rises and lands through two slow, small steps.
                motion=((local-152)/29)%1 if local>=154 else 0.
            elif kind=='breathe':
                kind='breathe'
                motion=curve(local,30,70)
                # Keep the seated pose while taking a breath.
            elif key=='introduce' and kind=='brave':
                gesture=.16*pulse(local,256,22)
        if role=='sheriff':
            if kind=='breathe':
                gesture=curve(local,25,49)*(1-curve(local,50,71))
            elif kind=='encourage':
                if speaking:
                    gesture=curve(n,event['at'],event['at']+12)*(1-curve(n,event['end']-11,event['end']))
                if event and event['role']=='pause':
                    kind='listen'
            elif kind=='cheer':
                gesture=.8*pulse(local,99,20)+.55*pulse(local,154,18)
        if role in {'teacher','mom','friend','parent'}:
            if kind=='clap':
                # Hands touch on the exact audio transient frames on the front row.
                delay=0 if role in {'mom','friend'} else 2
                gesture=max((pulse(n,center+delay,8) for center in scene['claps']),default=0.)
            elif kind in {'open','point'} and speaking:
                gesture=.9*curve(n,event['at'],event['at']+13)*(1-curve(n,event['end']-12,event['end']))
            elif kind=='seated' and speaking:
                gesture=.44*curve(n,event['at'],event['at']+13)*(1-curve(n,event['end']-12,event['end']))
        blink=0
        salt=int(actor.x+actor.height*1.9+len(key)*21)
        cycle=(n+salt)%(111+salt%17)
        if cycle in range(4) and phoneme in {'X','A','B'}:
            blink=(17,36,48,23)[cycle]
        return Pose(role,kind,actor.look,actor.variant,value(gesture),phoneme,blink,value(motion))

    def layout(self,n):
        sc,event,local=self.sample(n)
        angle,cast=self.steps(sc,local)
        mouth=self.mouths(event,n)
        return sc,event,local,angle,cast,[self.pose(a,sc,event,n,local,mouth) for a in cast]

    def draw(self,n,bank):
        scene,event,local,angle,cast,poses=self.layout(n)
        key=scene['id']
        canvas=plate(angle).copy()
        target=scene.get('icon')
        if target and scene['view']!='practice':
            size=232 if key in {'question_one','teacher_star','apple'} else 160
            art=card(target,size)
            canvas.alpha_composite(art,(840 if key!='hands_up' else 848,155 if key!='hands_up' else 118))
        if key=='arrival':
            canvas.alpha_composite(board_layer('title'))
        if key=='goodbye':
            canvas.alpha_composite(board_layer('finish'))
        if scene['view']=='practice':
            practice=next(item for item in scene['events'] if item['role']=='pause')
            listening = n < scene['events'][1]['at']
            canvas.alpha_composite(board_layer('Listen to your teacher.' if listening else practice['en']))
            if target:
                canvas.alpha_composite(card(target,102),(376,111))
        for a,p in zip(cast,poses,strict=True):
            if angle!='audience' and a.role=='y' and (p.kind in {'seat','raise','shy','stand','breathe','walk'} or key=='introduce'):
                chair_x=941 if key=='introduce' else a.x
                pass
            shadow(canvas,a.x,a.ground-1,a.height*.46,.74)
        for a,p in zip(cast,poses,strict=True):
            im=bank.scaled(p,round(a.height))
            scale=a.height/ACTOR_HEIGHT
            anchor=(a.x-ANCHOR[0]*scale,a.ground-ANCHOR[1]*scale)
            canvas.alpha_composite(im,(round(anchor[0]),round(anchor[1])))
        if event:
            canvas.alpha_composite(caption(event['en'],event['ko'],event['role']))
        if event and event['role']=='pause':
            d=ImageDraw.Draw(canvas)
            remaining=(event['end']-n+FPS-1)//FPS
            for i in range(4):
                x=714+i*32
                d.ellipse((x,694,x+12,706),fill='#ffe1a2' if i<remaining else '#6c8e89',outline='#25494a',width=1)
            centered(d,765,667,'윤수 차례야',25,'#fff3cb','bold')
        return canvas

@lru_cache(maxsize=8)
def page_image(index):
    with Image.open(ROOT/'sprites'/f'cells-{index:04}.webp') as img:
        return img.convert('RGBA')

class SpriteBank:
    def __init__(self):
        path=ROOT/'sprites'/'index.json'
        self.cells={Pose(**entry['pose']):entry['cell'] for entry in json.loads(path.read_text())['cells']}

    @lru_cache(maxsize=160)
    def scaled(self,pose,height):
        page,slot=divmod(self.cells[pose],SHEET_SIZE)
        col,row=slot%LANES[0],slot//LANES[0]
        w,h=CELL
        im=page_image(page).crop((col*w,row*h,(col+1)*w,(row+1)*h))
        scale=height/ACTOR_HEIGHT
        if height==ACTOR_HEIGHT:
            return im
        return im.resize((round(w*scale),round(h*scale)),Image.Resampling.LANCZOS)

def photo_key(p):
    if p.role=='pupil':return 'classkid'+str(p.variant)
    if p.role=='y':
        if p.kind=='classseat':return 'classy'+str(2 if p.mouth not in {'A','X'} else 0)
        if p.kind=='raise' and p.gesture>0:
            return 'raise'+str(round(p.gesture*11/48))
        if p.kind=='walk':
            return 'walk'+str(min(59,round(p.motion*59/48)))
        return 'talk'+str({'X':0,'A':0,'B':1,'C':2,'D':3,'E':4,'F':5,'G':2,'H':6}[p.mouth] if p.blink<39 else 7)
    if p.role=='sheriff':
        return 'sheriff'+str(int(p.mouth not in {'X','A','B'}))
    if p.role=='teacher':
        return 'person'+str(int(p.gesture>=18))
    if p.role=='mom':
        return ('seated'+str(round(p.gesture*3/48)) if p.kind=='clap' else 'seated0' if p.kind=='seated' else 'person2')
    if p.role=='parent':
        return 'classparent'+str(p.variant)
    if p.kind in {'seated','clap'}: return 'seated5' if p.variant else 'seated4'
    return 'person6' if p.variant else 'person4'

@lru_cache(maxsize=110)
def photo_cel(key):
    source=Image.open(ROOT/'source'/(key+'.webp')).convert('RGBA')
    h=round(ACTOR_HEIGHT*.75) if key.startswith('seated') else ACTOR_HEIGHT
    w=round(source.width*h/source.height)
    im=source.resize((w,h),Image.Resampling.LANCZOS)
    alpha=np.asarray(im.getchannel('A'))
    y,x=np.where(alpha[-18:]>90)
    anchor=round(float(np.mean(x))) if len(x) else w//2
    out=Image.new('RGBA',CELL)
    out.alpha_composite(im,(ANCHOR[0]-anchor,ANCHOR[1]-h))
    return out

def redraw(p):
    return photo_cel(photo_key(p))

def assemble(film):
    folder=ROOT/'sprites'
    folder.mkdir(exist_ok=True)
    needed={}
    exposures=[]
    for n in range(film.data['frames']):
        sc,ev,loc,angle,cast,poses=film.layout(n)
        cells=[]
        for actor,pose in zip(cast,poses):
            if pose not in needed:
                needed[pose]=len(needed)
            cells.append(dict(role=actor.role,cell=needed[pose],x=actor.x,ground=actor.ground,height=actor.height))
        exposures.append(dict(frame=n,scene=sc['id'],actors=cells))
    original=list(needed)
    palette={}
    representatives={}
    for pose in original:
        key=photo_key(pose)
        if key not in palette:
            palette[key]=len(palette)
            representatives[pose]=palette[key]
        needed[pose]=palette[key]
    for record in exposures:
        for actor in record['actors']:
            actor['cell']=needed[original[actor['cell']]]
    page=Image.new('RGBA',(CELL[0]*LANES[0],CELL[1]*LANES[1]))
    for pose,i in representatives.items():
        slot=i%SHEET_SIZE
        page.alpha_composite(redraw(pose),(slot%LANES[0]*CELL[0],slot//LANES[0]*CELL[1]))
        if slot==SHEET_SIZE-1 or i==len(representatives)-1:
            index=i//SHEET_SIZE
            page.save(folder/f'cells-{index:04}.webp',lossless=True,method=1,exact=True)
            page=Image.new('RGBA',page.size)
    (folder/'index.json').write_text(json.dumps(dict(cell_size=CELL,anchor=ANCHOR,columns=LANES[0],
             rows=LANES[1],base_height=ACTOR_HEIGHT,cells=[dict(cell=i,pose=asdict(p)) for p,i in needed.items()]),
             ensure_ascii=False,indent=2)+'\n')
    (folder/'exposures.json').write_text(json.dumps(exposures,separators=(',',':'))+'\n')
    print(len(representatives),'full-body cels in',1+(len(representatives)-1)//SHEET_SIZE,'lossless sprite sheets',flush=True)

def encode(film,bank,first,end,target, _width=1920):
    out_height=(_width*9)//16
    args=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','rawvideo','-pixel_format','rgba','-video_size','1536x864',
          '-framerate',str(FPS),'-i','-','-an','-vf',f'scale={_width}:{out_height}:flags=lanczos,format=yuv420p',
          '-c:v','libx264','-threads','3','-preset','fast','-crf','19','-g','48','-bf','0','-movflags','+faststart',str(target)]
    with subprocess.Popen(args,stdin=subprocess.PIPE) as stream:
        for n in range(first,end):
            image=film.draw(n,bank)
            stream.stdin.write(image.tobytes())
        stream.stdin.close()
        status=stream.wait()
    if status:raise subprocess.CalledProcessError(status,args)

def mux(parts,target,time=0):
    listing=target.with_suffix('.concat.txt')
    listing.write_text(''.join(f"file '{path.resolve()}'\n" for path in parts))
    cmd=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(listing),
        '-ss',str(time),'-i',str(ROOT/'mix.wav'),'-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','160k',
        '-shortest','-movflags','+faststart',str(target)]
    subprocess.run(cmd,check=True)

def shot(i):
    f=Film(); bank=SpriteBank()
    sc=f.scenes[i]
    target=ROOT/'qa'/f'{i+1:02d}-{sc["id"]}.mp4'
    encode(f,bank,sc['at'],sc['end'],target)
    print(sc['id'],sc['end']-sc['at'],'frames',flush=True)
    return target

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--build-sprites',action='store_true')
    p.add_argument('--frame',type=int)
    p.add_argument('--scene')
    p.add_argument('--out',type=Path,default=ROOT/'delivery'/FILM)
    p.add_argument('--jobs',type=int,default=4)
    p.add_argument('--width',type=int,default=1920)
    a=p.parse_args()
    f=Film()
    if a.build_sprites:
        assemble(f)
    elif a.frame is not None:
        f.draw(a.frame,SpriteBank()).convert('RGB').save(a.out)
    elif a.scene:
        target=next(s for s in f.scenes if s['id']==a.scene)
        temp=a.out.with_name(a.out.stem+'-video.mp4')
        encode(f,SpriteBank(),target['at'],target['end'],temp,a.width)
        mux([temp],a.out,target['at']/FPS)
    else:
        from concurrent.futures import ProcessPoolExecutor
        a.out.parent.mkdir(exist_ok=True)
        with ProcessPoolExecutor(max_workers=a.jobs) as pool:
            files=list(pool.map(shot,range(len(f.scenes))))
        mux(files,a.out)
        print(a.out,flush=True)

if __name__=='__main__':
    main()
