"""Cairo framing helpers carried over from Wash Day."""
import io
import math
from pathlib import Path
from functools import lru_cache
from PIL import Image
import cairocffi as cairo

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
def shadow(c,x,y,w,h,alpha=.32):
    c.save();c.translate(x,y);c.scale(w,h)
    g=cairo.RadialGradient(0,0,0,0,0,1)
    g.add_color_stop_rgba(0,.095,.065,.025,alpha);g.add_color_stop_rgba(.52,.12,.08,.03,alpha*.56)
    g.add_color_stop_rgba(1,.12,.08,.04,0);c.set_source(g);c.arc(0,0,1,0,math.tau);c.fill();c.restore()
