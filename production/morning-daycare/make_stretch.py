"""Register the four complementary morning expressions on the bedroom exit mark."""
from pathlib import Path
from PIL import Image
import numpy as np
from compose_strips import pack,keyed
R=Path(__file__).resolve().parent
d=R/'actions/wake_stretch'
p=d/'source/stretch-original.png'
with Image.open(p) as im:raw=im.convert('RGB')
w,h=raw.size
frames=[]
for i in range(4):
    x,y=i%2*w//2,i//2*h//2
    actor=keyed(raw.crop((x+4,y+4,x+w//2-4,y+h//2-4)))
    im=actor.getchannel('A')
    box=im.getbbox()
    crop=actor.crop(box)
    scale=.54
    cut=crop.resize((round(crop.width*scale),round(crop.height*scale)),Image.Resampling.LANCZOS)
    cel=Image.new('RGBA',(1280,720))
    cel.alpha_composite(cut,(1120-cut.width,673-cut.height))
    frames.append(cel)
with Image.open(R/'actions/wake/plate.webp') as p:plate=p.resize((1280,720),Image.Resampling.LANCZOS)
pack(d,plate,frames,[8,9,10,8],[w,h],'Four independently posed complete photographs',[
 {'frame':0,'state':'Sheriff raises arms and Yoonsu notices'}, {'frame':8,'state':'Sheriff stretches, Yoonsu lifts arms'},
 {'frame':17,'state':'Yoonsu stretches while Sheriff lowers'}, {'frame':27,'state':'both finish and smile'}],
 'slate pajamas / blue uniform','full body')
