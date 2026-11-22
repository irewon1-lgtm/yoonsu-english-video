"""Register whole garment-performance drawings against their original slope."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFilter
import cv2,numpy as np
from compose_strips import pack,keyed

ROOT=Path(__file__).resolve().parent
D=ROOT/'actions'/'dress'
def split(name):
    p=D/'source'/name
    with Image.open(p) as image:
        rgb=image.convert('RGB')
    w,h=rgb.size
    panes=[]
    for j in range(4):
        x0,y0=round(j%2*w/2),round(j//2*h/2)
        x1,y1=round((j%2+1)*w/2),round((j//2+1)*h/2)
        panes.append(keyed(rgb.crop((x0+5,y0+5,x1-5,y1-5))))
    return panes,rgb.size

def register(im, scale, x, y):
    a=np.asarray(im.getchannel('A'))
    yy,xx=np.where(a>=185)
    floor=yy.max()
    footprint=xx[(yy>=floor-32)&(yy<floor+1)]
    mid=(float(footprint.min())+float(footprint.max()))/2
    w,h=im.size
    im=im.resize((round(w*scale),round(h*scale)),Image.Resampling.LANCZOS)
    canvas=Image.new('RGBA',(1280,720))
    shadow=Image.new('RGBA',(1280,720))
    ImageDraw.Draw(shadow).ellipse((x-61,y-8,x+61,y+14),fill=(46,34,27,77))
    canvas.alpha_composite(shadow.filter(ImageFilter.GaussianBlur(7)))
    canvas.alpha_composite(im,(round(x-mid*scale),round(y-floor*scale)))
    return canvas

def main():
    a,sa=split('overhead.png')
    b,sb=split('sleeves.png')
    m,sm=split('between.png')
    # Only accepted positions are listed. The trousers remain the same during
    # this entire pullover action; the new pants appear after the scene break.
    seq=[(m[0],sm),(a[0],sa),(m[1],sm),(a[1],sa),(m[2],sm),(a[2],sa),
         (m[3],sm),(a[3],sa),(b[1],sb),(b[2],sb),(b[3],sb)]
    holds=[15,10,10,12,13,11,14,11,13,18,29]
    assert sum(holds)==156
    sizes=[]
    frames=[]
    for im,(w,h) in seq:
        a=np.array(im.getchannel('A'))
        ys,xs=np.where(a>190)
        foot=xs[ys>=ys.max()-int(.070*im.height)]
        span=max(5,int(foot.max()-foot.min()))
        sizes.append([span,im.size])
    for n,((im,_),(span,_)) in enumerate(zip(seq,sizes)):
        # The ankle spacing is a better invariant than outer cell height,
        # which changes as the shirt is raised over the boy's head.
        scale=82/span
        ideal=408/(.9*im.height)
        scale=min(1.13*ideal,max(.86*ideal,scale))
        frames.append(register(im,scale,319,653))
    with Image.open(ROOT/'assets/sets/bedroom.png') as p:
        plate=p.resize((1280,720),Image.Resampling.LANCZOS)
    marks=[{'frame':0,'state':'both hands hold neckline while pajamas still on'},
           {'frame':27,'state':'head passes collar'}, {'frame':61,'state':'one arm emerges'},
           {'frame':85,'state':'other arm moves through second sleeve'},
           {'frame':118,'state':'pinch hem and unfold'},{'frame':139,'state':'both arms free and hem settles'}]
    crop=(12,126,1012,688.5)
    plate=plate.transform((1280,720),Image.Transform.EXTENT,crop,Image.Resampling.BICUBIC)
    frames=[im.transform((1280,720),Image.Transform.EXTENT,crop,Image.Resampling.BICUBIC) for im in frames]
    pack(D,plate,frames,holds,[list(sa),list(sm),list(sb)],'11 separately generated photographic shirt positions, clean keyed and registered to foot support.',marks,
         'slate pajama trousers, leaf green/navy cream collar pullover','three-quarter fixed')
    preview=Image.new('RGB',(5*224,3*140),'#21292e')
    for j,im in enumerate(frames):
        shot=Image.alpha_composite(plate.convert('RGBA'),im).resize((224,126))
        x,y=j%5*224,j//5*140
        preview.paste(shot.convert('RGB'),(x,y))
        ImageDraw.Draw(preview).text((x+9,y+128),str(j),fill='white')
    preview.save(ROOT/'reviews/dress-board.jpg',quality=94)
    print('dress',len(frames),sum(holds),sizes)
if __name__=='__main__': main()
