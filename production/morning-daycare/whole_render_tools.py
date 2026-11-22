"""Shared typography and video encoding for the storyboard."""
import subprocess
from pathlib import Path
import cairocffi as cairo
from drawing import color, label, pill, shadow

ROOT=Path(__file__).resolve().parent
FPS=24
W,H=1920,1080
WIDTH,HEIGHT=1280,720

CAST={
    'S':('SHERIFF LABRADOR','#46558a'),
    'Y':('YOONSU','#246757'),
    'G':('PARENT','#765159'),
    'T':('TEACHER','#815039'),
}

TITLE='Good Morning, Yoonsu!'

def mouth(segment,n):
    if not segment:
        return 'X'
    elapsed=(n-segment['start']+.5)/FPS
    return next((s['value'] for s in segment['shapes'] if s['start']<=elapsed<s['end']),'X')

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
