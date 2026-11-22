"""The Little Star. Fixed photograph plates and discrete Wash Day sprite exposures."""
import argparse
from bisect import bisect_right
from dataclasses import dataclass
from functools import lru_cache
import json
import math
from multiprocessing import Pool
from pathlib import Path
import subprocess
import sys

import cairocffi as cairo
from PIL import Image, ImageFilter
from drawing import color, label, oval, paint, pill, raster, shadow, surface
from edit import FPS, ROOT
from wash_coverage import Shot

ASSETS = ROOT / 'assets'
MOTION = ROOT / 'motion'
sys.path.insert(0, str(ASSETS/'friends'))
from friends_motion import draw_actor, line_viseme

W, H = 1920, 1080
BEDROOM = ASSETS / 'home-plate.png'
PORTRAIT = ASSETS / 'portrait' / 'atlas.png'
PAPER = ROOT / 'star'
NAMES = {'S':'SHERIFF LABRADOR', 'Y':'YOONSU', '1':'ONE', '2':'TWO'}
TAGS = {'S':'#455e9c', 'Y':'#22706a', '1':'#983a61', '2':'#8b5022'}
BOXES = {
    'room': (0,0,1280,720),
    'window': (13,117,612,344.25),
    'outside': (46,159,442,248.625),
    'bed': (307,326,646,363.375),
    'blanket': (411,381,426,239.625),
    'look': (692,181,571,321.1875),
    'cloud': (808,215,385,216.5625),
    'found': (859,244,306,172.125),
}
# The same ceiling light, headboard and window appear at their photographed
# coordinates in the wide camera. Objects are separate tighter, locked cameras.
LEADS = ('room','Y','world','1','Y','2','Y','S','1','Y','2','S','Y','1','Y','S')
PROPS = {3:'window',4:'outside',5:'bed',6:'blanket',8:'look',9:'cloud',10:'found',12:'bed'}
ACTIONS = {
    1: ('greeting',False), 2: ('bed',True), 3: ('bed',False),
    4: ('bed',False), 5: ('bed',True), 6: ('bed',True),
    8: ('lamp',False), 9: ('lamp',False), 10: ('lamp_release',False),
    12: ('sleepy',False), 13: ('wave',False), 14: ('wave',False),
    15: ('wave',False),
}
CAST = [('S',1141,666,300),('1',834,633,91),('2',946,649,169)]
REST_X, GROUND, CHILD_H = 331,664,361

@lru_cache(55)
def texture(path):
    with Image.open(path) as im:
        return surface(im.convert('RGBA'))

@lru_cache(16)
def background(key, focus=False):
    x,y,w,h=BOXES[key]
    with Image.open(BEDROOM) as image:
        if key == 'room' and not focus:
            result = image.convert('RGB')
        else:
            sx,sy = image.width /1280, image.height/720
            result = image.convert('RGB').transform((1536,864),Image.Transform.EXTENT,
                (x*sx,y*sy,(x+w)*sx,(y+h)*sy),Image.Resampling.BICUBIC)
        if focus:
            result = result.filter(ImageFilter.GaussianBlur(6))
        return surface(result)

def transformed_point(camera, x, y):
    sx,sy,w,h=BOXES[camera]
    return (x-sx)*1280/w, (y-sy)*720/h, 1280/w

@lru_cache(20)
def face_tile(shape, blink):
    w,h=836,816
    i='XABCDEFGH'.index(shape)
    x,y=i%3*w,i//3*h
    with Image.open(PORTRAIT) as atlas:
        image=atlas.crop((x,y,x+w,y+h)).convert('RGBA')
    if blink:
        with Image.open(ASSETS/'portrait'/'closed-eyes.png') as lids:
            image.paste(lids,(282,278,601,439))
    return surface(image)

def mouth(clip, frame):
    if clip is None:
        return 'X'
    t = (frame-clip['start']+.5)/FPS
    shape = next((s['value'] for s in clip['shapes'] if s['start']<=t<s['end']),'X')
    return shape if shape in 'XABCDEFGH' else 'X'

def ease(x):
    x = min(1.,max(0.,x))
    return x*x*(3-2*x)

def star(c, frame, camera, play_from, reveal=True):
    # Eighteen drawings share the same pin point. The paper turns once and settles.
    if not reveal:
        return
    local=max(0,frame-play_from)
    idx=min(17,local//2)
    x,y,z=transformed_point(camera,987,353)
    if -80<x<1360 and -80<y<800:
        shadow(c,x+4*z,y+8*z,19*z,19*z,.22)
        art=texture(PAPER/f'{idx:02}.png')
        paint(c,art,x-25*z,y-15*z,50*z,50*z)

def caption(c, role, line, hold=False):
    name='YOUR TURN, YOONSU!' if hold else NAMES[role]
    c.select_font_face('DejaVu Sans',0,1)
    c.set_font_size(38)
    width=max(360,c.text_extents(line)[2]+108)
    x=(1280-width)/2
    pill(c,x,615,width,73,'#383141')
    pill(c,x,610,width,73,'#fff8df')
    c.set_font_size(15)
    tag_width=c.text_extents(name)[2]+46
    pill(c,(1280-tag_width)/2,595,tag_width,26,'#306e62' if hold else TAGS[role])
    label(c,name,640,613,15,'#ffffff',align='center')
    label(c,line,640,660,38,'#2a243b',align='center')

class Sprite:
    def __init__(self):
        self.spec=json.loads((MOTION/'index.json').read_text())
        files = dict(self.spec['actions'])
        if 'lamp' in files and 'release' in files['lamp']:
            files['lamp_release'] = files['lamp']['release']
        self.actions = files
        self.clocks = {}
        for key,data in files.items():
            count=0
            times=[]
            for length in data['durationsMs']:
                count+=length
                times.append(count)
            self.clocks[key]=times

    def at(self, name, elapsed):
        if name not in self.actions:
            return texture(MOTION/self.spec['neutral'])
        times=self.clocks[name]
        data=self.actions[name]
        frames=data['frames']
        i=bisect_right(times,elapsed*1000)
        return texture(MOTION/frames[min(i,len(frames)-1)])

    def child(self,c,x,y,height,name,elapsed,flip=False):
        art=self.at(name,elapsed)
        ax,ay=self.spec['anchor']
        scale=height/629
        shadow(c,x,y+3,height*.14,10)
        c.save()
        c.translate(x,y)
        if flip:
            c.scale(-1,1)
        paint(c,art,-ax*scale,-ay*scale,art.get_width()*scale,art.get_height()*scale)
        c.restore()

def build_shot_list(scene, dialogue, turn):
    i=scene['i']
    first,last=scene['start'],scene['end']
    lead=dialogue[0]
    # Hold before the cue and use a fixed return picture for the spoken turn.
    edits=[(first,'world')]
    if i==0:
        edits.append((first+66,'S'))
    else:
        begin=lead['start'] if i==9 else lead['start']-5
        if i in PROPS and i in {4,6,12}:
            edits[0]=(first,PROPS[i])
        edits.append((begin,LEADS[i]))
    if turn:
        cue,repeat=dialogue[1:]
        edits.extend([((lead['end']+cue['start'])//2,'S'),
                      ((cue['end']+repeat['start'])//2,repeat['role'])])
        edits.append((turn[1]+12,PROPS.get(i,'world')))
    elif i==7:
        edits.append((lead['end']+9,'look'))
    elif i==15:
        edits.append((lead['end']+7,'world'))
    merged=[]
    for n,cam in edits:
        if n<last-8 and (not merged or cam!=merged[-1][1]):
            merged.append((n,cam))
    return [Shot(n,merged[j+1][0] if j+1<len(merged) else last,cam)
            for j,(n,cam) in enumerate(merged)]

class Film:
    def __init__(self):
        self.edit=json.loads((ROOT/'timeline.json').read_text())
        self.scenes=self.edit['scenes']
        self.clips=self.edit['dialogue']
        self.turns=[(round(a*FPS),round(b*FPS),s) for a,b,s in self.edit['episode']['turns']]
        self.dialogue=[[s for s in self.clips if row['start']<=s['start']<row['end']]
                       for row in self.scenes]
        self.by_scene=[next((t for t in self.turns if row['start']<=t[0]<row['end']),None)
                       for row in self.scenes]
        self.edl=[build_shot_list(s,d,t) for s,d,t in zip(self.scenes,self.dialogue,self.by_scene)]
        self.holds={n:a for a,b,_ in self.turns for n in range(a-3,b+4)}
        self.starts=[s['start'] for s in self.scenes]
        self.walk=json.loads((ASSETS/'walk/walk.json').read_text())['frames']
        self.sprite=Sprite()
        self.previous=None

    def world(self,c,i,frame,local,clip,shot_age):
        paint(c,background('room'),0,0,1280,720)
        start=self.scenes[10]['start']
        if i>=10:
            star(c,frame,'room',start)
        beside_lamp=i>=7
        child_x,child_ground,child_height=(771,660,310) if beside_lamp else (REST_X,GROUND,CHILD_H)
        if i==0 and local<len(self.walk):
            scale=CHILD_H/474
            p=self.walk[local]
            x=REST_X+(p['dx']-self.walk[-1]['dx'])*scale
            art=texture(ASSETS/'walk'/p['file'])
            shadow(c,x,GROUND+2,46,10)
            paint(c,art,x-256*scale,GROUND-494*scale,512*scale,512*scale)
        else:
            gesture,flip=ACTIONS.get(i,(None,False))
            if gesture=='sleepy' and gesture not in self.sprite.actions:
                gesture=None
            if i==1 and local>=55:
                gesture=None
            # The head and torso are authored into each exposure. Changing a
            # held cell never modifies the photograph or interpolates a silhouette.
            self.sprite.child(c,child_x,child_ground,child_height,gesture,max(0,shot_age-.083),flip)
        for role,x,y,height in CAST:
            if beside_lamp and role=='1':
                x,y=904,630
            if beside_lamp and role=='2':
                x,y=1018,649
            phase = self.gesture(clip,frame) if clip and clip['role']==role else None
            if role=='1' and i in {3,8,13} and not clip and .12<shot_age<1.24:
                phase=min(1.,(shot_age-.12)/1.12)
            vv=line_viseme(clip,frame) if clip and clip['role']==role else 'X'
            shadow(c,x,y+4,height*.22,10)
            draw_actor(c,role,x,y,height,'room',local/FPS,vv,phase)

    def gesture(self,clip,frame):
        if not clip:
            return None
        if clip['kind']=='repeat':
            return None
        return ease((frame-clip['start']+2)/max(1,clip['end']-clip['start']))

    def portrait(self,c,role,i,frame,clip,shot_age,holding):
        back={3:'window',4:'window',5:'bed',6:'bed',8:'look',9:'cloud',10:'cloud',12:'bed'}.get(i,'room')
        paint(c,background(back,True),0,0,1280,720)
        if role=='Y':
            blink=not holding and clip is None and .18<shot_age<=.26
            head=face_tile(mouth(clip,frame),blink)
            paint(c,head,319,28,642,642*816/836)
        else:
            ht={'S':518,'1':364,'2':489}[role]
            behind={'1':'2','2':'1'}.get(role)
            if behind:
                secondary={'1':148,'2':224}[behind]
                px=965 if role=='1' else 306
                shadow(c,px,573,secondary*.26,10)
                draw_actor(c,behind,px,572,secondary,'room',0)
            px={'S':642,'1':551,'2':725}[role]
            shadow(c,px,601,ht*.26,13)
            draw_actor(c,role,px,600,ht,'room',0,line_viseme(clip,frame),self.gesture(clip,frame))

    def opening(self,c):
        paint(c,background('room'),0,0,1280,720)
        fade=cairo.LinearGradient(0,0,960,100)
        for when,col in [(0,(.08,.055,.13,.96)),(.48,(.11,.08,.17,.76)),(1,(.21,.15,.20,.06))]:
            fade.add_color_stop_rgba(when,*col)
        c.set_source(fade);c.paint()
        label(c,"A little star",73,257,94,'#fff5de','URW Bookman')
        label(c,"in Yoonsu’s room",78,343,58,'#fff5de','URW Bookman')
        label(c,'윤수 방의 작은 별',81,420,31,'#ffe099','Noto Sans CJK KR')
        paint(c,texture(PAPER/'17.png'),644,137,89,89)
        c.set_line_width(3.5)
        c.set_line_cap(cairo.LINE_CAP_ROUND)
        color(c,'#dcb66b')
        c.move_to(84,373);c.line_to(342,373);c.stroke()

    def frame(self,c,frame):
        if frame<self.edit['opening']:
            self.opening(c)
            return
        i=min(len(self.scenes)-1,bisect_right(self.starts,frame)-1)
        sc=self.scenes[i]
        final=frame>=sc['end']
        local=frame-sc['start']
        shot=self.edl[i][-1] if final else next(s for s in self.edl[i] if s.first<=frame<s.last)
        clip=next((s for s in self.dialogue[i] if s['start']<=frame<s['end']),None)
        turn=self.by_scene[i]
        hold=turn and turn[0]-3<=frame<turn[1]+10
        age=(frame-shot.first)/FPS
        if shot.camera=='world':
            self.world(c,i,frame,local,clip,age)
        elif shot.camera in NAMES:
            self.portrait(c,shot.camera,i,frame,clip if clip and clip['role']==shot.camera else None,age,hold)
        else:
            paint(c,background(shot.camera),0,0,1280,720)
            if i>=10:
                star(c,frame,shot.camera,self.scenes[10]['start'])
        if hold:
            caption(c,'Y',turn[2],True)
        elif clip:
            caption(c,clip['role'],clip['line'])
        if final:
            pill(c,397,555,486,76,'#18152d')
            label(c,'Good night, Yoonsu!',640,604,36,'#fff1d0','URW Bookman',align='center')

    def paint(self,out,frame,width):
        source=self.holds.get(frame,frame)
        key=(out,source,width)
        if key!=self.previous:
            ctx=cairo.Context(out)
            ctx.scale(width/1280,width/1280)
            self.frame(ctx,source)
            self.previous=key

def render_piece(item):
    i,first,last=item
    f=Film()
    out=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H)
    folder=ROOT/'shots'
    folder.mkdir(exist_ok=True)
    destination=folder/f'{i:02}.mp4'
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pixel_format','bgr0','-video_size',
         f'{W}x{H}','-framerate',str(FPS),'-i','-','-an','-c:v','libx264','-threads','2',
         '-filter_threads','1','-preset','veryfast','-crf','18','-maxrate','2600k','-bufsize','4300k','-g','48',
         '-vf','scale=out_color_matrix=bt709,format=yuv420p','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709',str(destination)]
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as ffmpeg:
        for n in range(first,last):
            f.paint(out,n,W)
            out.flush()
            ffmpeg.stdin.write(out.get_data())
        ffmpeg.stdin.close()
        if ffmpeg.wait():
            raise RuntimeError(destination)
    print(i,first,last,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--frame',type=int)
    parser.add_argument('--out',type=Path)
    parser.add_argument('--width',type=int,default=1920)
    parser.add_argument('--jobs',type=int,default=3)
    parser.add_argument('--pieces',type=str)
    arg=parser.parse_args()
    f=Film()
    if arg.frame is not None:
        out=cairo.ImageSurface(cairo.FORMAT_RGB24,arg.width,arg.width*9//16)
        f.paint(out,arg.frame,arg.width)
        out.write_to_png(str(arg.out))
    else:
        cut=[0]+f.starts+[f.edit['frames']]
        pieces=[(i,a,b) for i,(a,b) in enumerate(zip(cut,cut[1:]))]
        selected=set(map(int,arg.pieces.split(','))) if arg.pieces else set(range(len(pieces)))
        with Pool(arg.jobs) as pool:
            pool.map(render_piece,[p for p in pieces if p[0] in selected],chunksize=1)
        args=['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i','shots/concat.txt','-i','mix.wav',
              '-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','128k','-movflags','+faststart','The_Little_Star.mp4']
        (ROOT/'shots/concat.txt').write_text(''.join(f"file '{i:02}.mp4'\n" for i,a,b in pieces))
        if all((ROOT/'shots'/f'{i:02}.mp4').exists() for i,a,b in pieces):
            subprocess.run(args,cwd=ROOT,check=True)
