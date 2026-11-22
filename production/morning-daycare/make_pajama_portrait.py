"""Keep the approved eyes and visemes intact while registering the bedtime shirt."""
import math
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import numpy as np
R=Path(__file__).resolve().parent
folder=R/'assets/portrait'
old=Image.open(folder/'atlas.png').convert('RGBA')
w,h=836,816
out=Image.new('RGBA',old.size)
fabric=Image.new('L',(w,h))
d=ImageDraw.Draw(fabric)
d.polygon([(0,816),(0,730),(238,646),(274,598),(317,589),(337,600),(339,625),
           (350,650),(370,668),(397,688),(420,705),(439,680),(464,646),
           (480,616),(505,593),(542,594),(574,613),(619,654),(790,736),
           (836,765),(836,816)],fill=255)
fabric=fabric.filter(ImageFilter.GaussianBlur(1.5))
weights=np.asarray(fabric).astype(np.float32)/255
stars=Image.new('RGBA',(w,h))
grid=[(151,771),(206,729),(242,803),(309,743),(349,774),(389,809),(455,767),
      (489,729),(534,798),(591,697),(618,761),(682,809),(730,757)]
p=ImageDraw.Draw(stars)
for n,(x,y) in enumerate(grid):
    a=n*.56
    points=[(x+math.cos(a+i*math.pi/5)*(8 if i%2==0 else 3.4),
             y+math.sin(a+i*math.pi/5)*(8 if i%2==0 else 3.4)) for i in range(10)]
    p.polygon(points,fill=(231,218,184,213))
for i in range(9):
    x,y=(i%3)*w,(i//3)*h
    tile=old.crop((x,y,x+w,y+h))
    arr=np.array(tile); rgb=arr[:,:,:3].astype(np.float32)
    lum=rgb@np.array([.2126,.7152,.0722])
    light=(lum-82)*.22
    woven=np.stack((87+light,108+light,122+light),-1).clip(0,255)
    arr[:,:,:3]=np.uint8(np.round(rgb*(1-weights[:,:,None])+woven*weights[:,:,None]))
    patched=Image.fromarray(arr)
    use=stars.copy()
    use.putalpha(Image.fromarray(np.uint8(np.array(use.getchannel('A'))*weights*(arr[:,:,3].astype('float32')/255))))
    patched.alpha_composite(use)
    out.paste(patched,(x,y))
out.save(folder/'pajama-atlas.png',compress_level=7)
