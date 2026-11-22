"""Prep flat-key motion drawings into complete, registered, editable scene cels."""
from pathlib import Path
import json
from PIL import Image
import numpy as np
import cv2
from scipy.ndimage import distance_transform_edt

def keyed(image):
    rgb=np.asarray(image.convert('RGB'))
    v=rgb.astype(np.float32)
    r,g,b=np.moveaxis(v,2,0)
    excess=g-np.maximum(r,b)
    key=(g>159)&(excess>29)
    n,labels,stats,_=cv2.connectedComponentsWithStats((~key).astype(np.uint8))
    assert n>1
    areas=stats[1:,4]
    modes=np.flatnonzero(areas>=areas.max()*.10)+1
    certain=np.isin(labels,modes)
    solid=cv2.erode(certain.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    reach=cv2.dilate(certain.astype(np.uint8),np.ones((3,3),np.uint8)).astype(bool)
    matte=np.where(solid,1,np.clip((140-excess)/124,0,1)*reach)
    _,(ys,xs)=distance_transform_edt(~solid,return_indices=True)
    near=reach & ~solid
    out=np.dstack((rgb,np.round(matte*255).astype(np.uint8)))
    out[near,:3]=rgb[ys[near],xs[near]]
    out[~reach]=0
    return Image.fromarray(out)

def cut_grid(file,columns,rows):
    with Image.open(file) as src:
        src=src.convert('RGB')
    w,h=src.size
    return [keyed(src.crop((round(x*w/columns),round(y*h/rows),
                  round((x+1)*w/columns),round((y+1)*h/rows)))) for y in range(rows) for x in range(columns)]

def choose_bbox(im):
    strong=im.getchannel('A').point(lambda a:255 if a>=200 else 0)
    return strong.getbbox()

def place(im,target):
    # Confirm the target on the actual camera and use the same intended foot /
    # seat / object mark for all cels describing the same support condition.
    x,y,h=target
    l,t,r,b=choose_bbox(im)
    s=h/(b-t)
    pos=(round(x-s*(l+r)/2),round(y-s*b))
    return im.resize((round(im.width*s),round(im.height*s)),Image.Resampling.LANCZOS),pos

def pack(dst,plate,frames,holds,native_size,description,contacts,costume,view):
    dst.mkdir(exist_ok=True,parents=True)
    cels=dst/'cels'
    cels.mkdir(exist_ok=True)
    files=[]
    for n,im in enumerate(frames):
        name=f'cels/{n:03d}.webp'
        im.save(dst/name,'WEBP',lossless=True,method=1,exact=True)
        files.append(name)
    if plate:
        plate.convert('RGB').save(dst/'plate.webp','WEBP',lossless=True,method=1)
    doc=dict(frames=files,exposure_frames=holds,source_size=native_size,
             layer_order=['set','fixed props','performance','foreground'],costume=costume,
             view=view,contacts=contacts,source=description)
    if plate:
        doc['plate']='plate.webp'
    (dst/'index.json').write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
