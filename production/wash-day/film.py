"""Render the 1080p photographic Wash Day episode from complete sprite exposures."""
import argparse
import json
import math
from functools import lru_cache
from pathlib import Path
import sys
import subprocess
import io
import cairocffi as cairo
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parent
PHOTO=ROOT/"photo"
sys.path.insert(0,str(PHOTO))
from coverage import make_cuts, steady_frame
from photo.v11.body.body_motion import body_exposure
from photo.v11.hd.masters import at as master_cel
from photo.v11.portrait.face import exposure_at as expression, image_for
from photo.v11.friends.friends_motion import draw_actor, line_gesture, line_viseme
from photo.v11.practicals.practicals import photo_cel,on_set
from photo.v11.macro.cutaways_v11 import native_at
from photo.v11.closeups.cutaways_v11 import cutaway_at
from photo.v11.toe_contact.toe_contact import insert_at as toe_contact_at
FPS=24
W,H=1920,1080
def color(c,v):
    h=v.lstrip("#")
    c.set_source_rgb(*(int(h[i:i+2],16)/255 for i in (0,2,4)))
def oval(c,x,y,rx,ry,col):
    c.save(); c.translate(x,y); c.scale(rx,ry); c.arc(0,0,1,0,2*math.pi); c.restore()
    color(c,col); c.fill()
def pill(c,x,y,w,h,col):
    r=h/2
    c.new_path(); c.arc(x+w-r,y+r,r,-math.pi/2,math.pi/2); c.arc(x+r,y+r,r,math.pi/2,math.pi*1.5); c.close_path(); color(c,col); c.fill()
def label(c,s,x,y,size,col,face="DejaVu Sans",align="left",weight=1):
    c.select_font_face(face,0,weight); c.set_font_size(size)
    xb,yb,width,height,xa,ya=c.text_extents(s)
    if align=="center": x-=xb+width/2
    c.move_to(x,y); color(c,col); c.show_text(s)
def bubble(c,x,y,r,light="#72c5bf"):
    c.new_path(); c.arc(x,y,r,0,2*math.pi); color(c,light); c.set_line_width(2.5); c.stroke()
    c.new_path(); c.arc(x,y,r*.76,3.5,4.55); c.set_line_width(max(2,r*.085)); c.set_line_cap(cairo.LINE_CAP_ROUND); color(c,"#f7fff3"); c.stroke()
def caption(c,role,line,waiting=False):
    names={"S":"SHERIFF LABRADOR","1":"ONE","2":"TWO","Y":"YOONSU"}
    tag = "YOUR TURN" if waiting else names[role]
    col = "#297165" if waiting else {"S":"#2c607f","1":"#a9444d","2":"#97521e","Y":"#297459"}[role]
    c.select_font_face("DejaVu Sans",0,1); c.set_font_size(37)
    textw=c.text_extents(line)[2]
    w=max(380,textw+100); x=(1280-w)/2
    pill(c,x,604,w,72,"#b3a895"); pill(c,x,600,w,72,"#fff9e9")
    c.set_font_size(14); tw=c.text_extents(tag)[2]+34
    pill(c,640-tw/2,584,tw,27,col)
    label(c,tag,640,604,14,"#fffdf3",align="center")
    label(c,line,640,649,37,"#203c43",align="center")
def chapter(c,name):
    # Small scene heading appears only at the introduction of the routine.
    c.select_font_face("URW Bookman",0,1); c.set_font_size(23)
    w=c.text_extents(name)[2]+42
    pill(c,57,50,w,42,"#fff4d9"); label(c,name,78,79,23,"#335c5a","URW Bookman")
@lru_cache(maxsize=110)
def raster(name):
    file=Path(name)
    if file.suffix.lower()==".png":
        return cairo.ImageSurface.create_from_png(str(file))
    with Image.open(file) as im:
        return surface(im.convert("RGB"))
def surface(im):
    b=io.BytesIO(); im.save(b,format="PNG",compress_level=0); b.seek(0)
    return cairo.ImageSurface.create_from_png(b)
def paint(c,s,x,y,w,h):
    c.save();c.rectangle(x,y,w,h);c.clip();c.translate(x,y)
    c.scale(w/s.get_width(),h/s.get_height());c.set_source_surface(s,0,0)
    c.get_source().set_filter(cairo.FILTER_BILINEAR);c.paint();c.restore()
def plate(c,file):
    paint(c,raster(str(file)),0,0,1280,720)
@lru_cache(maxsize=6)
def defocus(name):
    with Image.open(PHOTO/name) as im:
        # Natural-looking change of focus for dialogue; background still belongs to the actual set.
        return surface(im.convert("RGB").resize((1008,567),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(7)))
def cast(c,role,x,ground,height,action,t,v,gesture=None):
    draw_actor(c,role,x,ground,height,action,t,v,gesture_phase=gesture)
def shadow(c,x,y,w,h,alpha=.32):
    c.save();c.translate(x,y);c.scale(w,h)
    g=cairo.RadialGradient(0,0,0,0,0,1)
    g.add_color_stop_rgba(0,.095,.065,.025,alpha);g.add_color_stop_rgba(.52,.12,.08,.03,alpha*.56)
    g.add_color_stop_rgba(1,.12,.08,.04,0);c.set_source(g);c.arc(0,0,1,0,math.tau);c.fill();c.restore()
def sat(x): return min(1,max(0,x))
MAC = ("","","tap","soap","rub","rinse","splash","cheeks","brush","brush","spit","feet","feet","toes","towel","towel","book")

def title(c,t):
    plate(c,PHOTO/"keyart.png")
    fade=cairo.LinearGradient(0,0,765,0);fade.add_color_stop_rgba(0,.014,.07,.085,.66);fade.add_color_stop_rgba(.68,.02,.09,.10,.42);fade.add_color_stop_rgba(1,.03,.10,.10,0)
    c.rectangle(0,0,770,720);c.set_source(fade);c.fill()
    label(c,"The",83,243,55,"#ffda91","URW Bookman")
    label(c,"Squeaky",78,342,100,"#fff9e8","URW Bookman")
    label(c,"Clean Club",78,434,92,"#fff9e8","URW Bookman")
    c.set_line_width(4);c.set_line_cap(cairo.LINE_CAP_ROUND);color(c,"#f7c681")
    c.move_to(86,469);c.curve_to(187,458,327,460,445,467);c.stroke()
    label(c,"with Yoonsu and friends",84,512,27,"#fff2d1","URW Bookman",weight=0)
@lru_cache(maxsize=96)
def portrait_surface(*exposure):
    return surface(image_for(*exposure))

def model(c,actor,seg,frame,action,clock,v,gesture):
    bg="footbath.png" if action in {"feet","toes"} else "bath.png"
    paint(c,defocus(bg),-240,-92,1710,962)
    local=clock/FPS
    if actor=="Y":
        head=portrait_surface(*expression(seg,frame,FPS))
        width=722
        paint(c,head,638-width/2,27,width,width*head.get_height()/head.get_width())
    elif actor=="S":
        cast(c,"S",640,878,805,action,local,v,gesture)
    else:
        height=490 if actor=="1" else 582
        who="2" if actor=="1" else "1"
        cast(c,who,957 if actor=="1" else 340,584,284 if who=="2" else 197,action,local,"X")
        cast(c,actor,575 if actor=="1" else 716,580,height,action,local,v,gesture)
@lru_cache(maxsize=1)
def walk_exposures():
    return json.loads((PHOTO/"v9/walk/walk.json").read_text())["frames"]

@lru_cache(65)
def body_surface(key,index):
    return surface(master_cel(key,index))
def wide(c,i,camera,action,clock,role,shape,u,setup,local,gesture):
    seated=action in {"feet","toes"}
    x={2:703,3:703,4:703,5:748,6:730,7:730,8:727,9:727,10:727}.get(i,664)
    ground=625 if i in {2,3,4,5,6,7} else 617
    if i==5: ground=556
    child_h=615 if seated else 590
    size=child_h*512/474
    if camera=="walk":
        frames=walk_exposures()
        step=frames[min(local,len(frames)-1)]
        x=325+step["dx"]*child_h/474
        texture=raster(str(PHOTO/"v9/walk"/step["file"]))
    else:
        key,index=body_exposure(i,u,local/FPS,setup=setup)
        texture=body_surface(key,index)
    c.save()
    if camera=="medium":
        # A separate camera axis for a new action setup. Keep hands and shoes in frame.
        zoom=1.11 if i==5 else 1.23
        center_y=300 if i==5 else 326
        tx=max(1280*(1-zoom),min(0,640-x*zoom))
        ty=max(720*(1-zoom),min(0,355-center_y*zoom))
        c.translate(tx,ty)
        c.scale(zoom,zoom)
    if i in {2,5}:
        plate(c,PHOTO/"v11/set/basin.png")
    else:
        plate(c,PHOTO/"bath.png")
    if i==5:
        # The rinse fitting is centered at local (405,204). Its supply pipe
        # attaches to the fixed countertop, with the spout above the bowl.
        px=x+(405-256)*child_h/474
        py=ground+(204-494)*child_h/474
        paint(c,raster(str(PHOTO/"v11/set/riser.png")),px-4,py+2,8,369-py)
    if i==5:
        shadow(c,x,627,132,16)
        paint(c,raster(str(PHOTO/"v11/set/step.png")),x-111,538,224,88)
    shadow(c,x-7,ground+3,116 if seated else 78,12)
    for r,px,y,h in (("S",263,603,374),("1",1006,605,130),("2",1134,605,223)):
        shadow(c,px,y+2,h*.21,h*.032)
        cast(c,r,px,y,h,action,clock/FPS,shape if r==role else "X",gesture if r==role else None)
    paint(c,texture,x-size*.5,ground-size*494/512,size,size)
    if i in {2,5}:
        # Registered occlusion by the upper lip of the photographed ceramic bowl.
        # A freestanding pipe below the sink would project through its cabinet doors.
        c.save()
        if i==2: c.rectangle(926,369,66,266)
        else: c.rectangle(804,369,180,80)
        c.clip()
        plate(c,PHOTO/"v11/set/basin.png")
        c.restore()
    c.restore()

@lru_cache(64)
def insert_surface(key,step):
    u=step/120
    if key=="toe_contact": return surface(toe_contact_at(u))
    if key in {"brush","splash","cheeks","feet","toes"}:
        cel=cutaway_at(key,u)
        return surface(on_set(cel,"feet" if key in {"feet","toes"} else "bath"))
    if key in {"rub_photo","soap_photo","book_open","book_settle"}:
        source,order={
            "rub_photo":("rub",[0,1,3,4,5]),
            "soap_photo":("soap",[0,1,2,3,4,5]),
            "book_open":("book",[0,0,1]),
            "book_settle":("book",[4,5,5,5])}[key]
        index=order[min(len(order)-1,int(u*len(order)))]
        return surface(on_set(photo_cel(source,index),"bath"))
    return surface(native_at(key,u))

def demonstration(c,surf,caption_rail):
    if not caption_rail:
        paint(c,surf,0,0,1280,720)
        return
    # Keep the enacted contact above the English line. The lens is fixed over
    # the whole shot, including silent handles before/after the spoken model.
    c.save()
    c.rectangle(0,0,1280,629)
    c.clip()
    paint(c,surf,0,-91,1280,720)
    c.restore()
    color(c,"#193d3b");c.rectangle(0,629,1280,91);c.fill()
    color(c,"#c7aa74");c.rectangle(0,629,1280,3);c.fill()

def phase(frame,cut,all_cuts,cameras):
    visible=[s for s in all_cuts if s.camera in cameras]
    before=sum(s.last-s.first for s in visible if s.last<=cut.first)
    length=sum(s.last-s.first for s in visible)
    return sat((before+frame-cut.first)/max(1,length-1))

class Film:
    def __init__(self):
        self.edit=json.loads((ROOT/"timeline.json").read_text())
        self.scenes=self.edit["scenes"]
        self.clips=self.edit["dialogue"]
        self.turns=[(round(a*FPS),round(b*FPS),s) for a,b,s in self.edit["episode"]["turns"]]
        self.hold_source={n:a for a,b,_ in self.turns for n in range(a-2,b+3)}
        self.previous=None
        self.cues=[[d for d in self.clips if shot["start"]<=d["start"]<shot["end"]] for shot in self.scenes]
        self.turn_by_scene=[next((q for q in self.turns if s["start"]<=q[0]<s["end"]),None) for s in self.scenes]
        self.edl=[make_cuts(s,self.cues[i],self.turn_by_scene[i]) for i,s in enumerate(self.scenes)]
        self.edl[-1]=make_cuts({**self.scenes[-1],"end":self.edit["frames"]},self.cues[-1],None)
    def frame(self,c,frame):
        if frame<self.edit["opening"]:
            title(c,frame/FPS)
            return
        scene=next((s for s in self.scenes if s["start"]<=frame<s["end"]),self.scenes[-1])
        i=scene["i"]
        act=scene["action"]
        turn=self.turn_by_scene[i]
        clips=self.cues[i]
        seg=next((s for s in clips if s["start"]<=frame<s["end"]),None)
        speaker=seg["role"] if seg else ""
        shape=line_viseme(seg,frame,FPS) if speaker in {"S","1","2"} else "X"
        gesture=line_gesture(seg,frame) if seg and speaker in {"S","1","2"} else None
        cuts=self.edl[i]
        cut=next(s for s in cuts if s.first<=frame<s.last)
        camera=cut.camera
        clock=steady_frame(frame,turn)-sum(b-a+4 for a,b,_ in self.turns if b<scene["start"])
        if camera in {"pickup","soap_start","book_open","book_turn","book_settle"}:
            key={"pickup":"towel_pickup","soap_start":"soap","book_turn":"book"}.get(camera,camera)
            u=sat((frame-cut.first)/max(1,cut.last-cut.first-1))
            if camera=="soap_start":u*=.42
            if camera=="book_turn":u=.12+.86*u
            paint(c,insert_surface(key,round(u*120)),0,0,1280,720)
        elif camera=="detail":
            u=phase(frame,cut,cuts,{"detail"})
            key=MAC[i]
            if i==3:key="soap_photo"
            if i==4:key="rub_photo"
            if i==13:key="toe_contact"
            # Re-enter the cheek shot on the released hand pose. The preceding
            # closed-eye exposure already played before the response window.
            if i==7 and cut==cuts[-1] and frame<cut.first+4:
                u=phase(cut.first+4,cut,cuts,{"detail"})
            # End with the supported foot before the dialogue cut.
            if i==11:u=min(u*.5,59/120)
            rail=i in {2,4,6,8,12,13} and any(cut.first<d["end"] and d["start"]<cut.last for d in clips)
            demonstration(c,insert_surface(key,round(u*120)),rail)
        elif camera in {"walk","medium","body"}:
            setup="main"
            if i==6 and cut==cuts[0]: setup="scoop"
            if i==15 and cut==cuts[-1]: setup="settled"
            if i==4 and cut==cuts[-1]: setup="knuckles"
            group={"body","medium"}
            u=phase(frame,cut,cuts,group) if camera in group else 0
            if i in {4,6,15}:
                u=sat((frame-cut.first)/max(1,cut.last-cut.first-1))
            wide(c,i,camera,act,clock,speaker,shape,u,setup,frame-scene["start"],gesture)
        else:
            face_frame=turn[0]-2 if turn and turn[0]-2<=frame<=turn[1]+2 else frame
            model(c,camera,seg if camera==speaker else None,face_frame,act,clock,shape if camera==speaker else "X",gesture if camera==speaker else None)
        if turn and turn[0]-2<=frame<=turn[1]+9:
            caption(c,"Y",turn[2],True)
        elif seg:
            if camera=="detail" and i in {2,4,6,8,12,13}:
                c.save();c.translate(0,42);caption(c,speaker,seg["line"]);c.restore()
            else:caption(c,speaker,seg["line"])
        elif i in {2,6,8,11} and frame<clips[0]["start"]-12:
            chapter(c,{2:"Hands",6:"Face",8:"Teeth",11:"Feet"}[i])
        if frame>=self.scenes[-1]["end"]:
            pill(c,508,602,264,65,"#fff1d9")
            label(c,"The End",640,648,39,"#27514e","URW Bookman","center")
    def paint(self,surf,frame,width):
        source=self.hold_source.get(frame,frame)
        render_key=(surf,source,width)
        if render_key==self.previous: return
        c=cairo.Context(surf)
        c.scale(width/1280,width/1280)
        self.frame(c,source)
        self.previous=render_key
def render_piece(args):
    idx,f0,f1=args
    f=Film(); dest=ROOT/"shots"; dest.mkdir(exist_ok=True)
    output=dest/f"{idx:02d}.mp4"
    cmd=["ffmpeg","-v","error","-y","-filter_threads","1","-f","rawvideo","-pix_fmt","bgr0","-s",f"{W}x{H}","-r",str(FPS),"-i","-","-an","-c:v","libx264","-threads","2","-preset","veryfast","-crf","19","-maxrate","2700k","-bufsize","4400k","-vf","scale=out_color_matrix=bt709,format=yuv420p","-colorspace","bt709","-color_primaries","bt709","-color_trc","bt709","-g","48",str(output)]
    surf=cairo.ImageSurface(cairo.FORMAT_RGB24,W,H)
    with subprocess.Popen(cmd,stdin=subprocess.PIPE) as proc:
        try:
            for n in range(f0,f1):
                f.paint(surf,n,W); surf.flush(); proc.stdin.write(surf.get_data())
        finally:
            proc.stdin.close()
        if proc.wait(): raise RuntimeError(output)
    print("shot",idx,"frames",f0,f1,flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(); p.add_argument("--frame",type=int); p.add_argument("--out",type=Path)
    p.add_argument("--width",type=int,default=1920); p.add_argument("--jobs",type=int,default=2)
    opt=p.parse_args()
    film=Film()
    if opt.frame is not None:
        width=opt.width; height=width*9//16
        surf=cairo.SVGSurface(str(opt.out),width,height) if opt.out.suffix==".svg" else cairo.ImageSurface(cairo.FORMAT_RGB24,width,height)
        film.paint(surf,opt.frame,width)
        if opt.out.suffix==".png": surf.write_to_png(str(opt.out))
        surf.finish()
    else:
        from multiprocessing import Pool
        cuts=[0]+[s["start"] for s in film.scenes]+[film.edit["frames"]]
        with Pool(opt.jobs) as pool: pool.map(render_piece,[(i,a,b) for i,(a,b) in enumerate(zip(cuts,cuts[1:]))],chunksize=1)
        (ROOT/"shots"/"concat.txt").write_text("".join(f"file '{i:02d}.mp4'\n" for i in range(len(cuts)-1)))
        subprocess.run(["ffmpeg","-v","error","-y","-f","concat","-safe","0","-i",str(ROOT/"shots"/"concat.txt"),"-i",str(ROOT/"wash-mix.wav"),"-map","0:v","-map","1:a","-c:v","copy","-c:a","aac","-b:a","112k","-movflags","+faststart",str(ROOT/"The_Squeaky_Clean_Club.mp4")],check=True)
