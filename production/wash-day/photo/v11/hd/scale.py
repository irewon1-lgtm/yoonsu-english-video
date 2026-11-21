"""Deterministic 2x display master from photographed cels, with fixed alpha geometry."""
from functools import lru_cache
from pathlib import Path
import cv2
import numpy as np
import onnxruntime as ort
from PIL import Image
from scipy.ndimage import distance_transform_edt
HERE=Path(__file__).resolve().parent
@lru_cache(1)
def session():
    o=ort.SessionOptions()
    o.log_severity_level=3
    o.intra_op_num_threads=2
    o.inter_op_num_threads=1
    o.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(str(HERE/"super-resolution-10.onnx"),sess_options=o,providers=['CPUExecutionProvider'])
def display_master(img):
    pixels=np.asarray(img.convert("RGBA"))
    a=pixels[:,:,3]
    ys,xs=np.where(a>1)
    if not len(xs): return Image.new("RGBA",(img.width*2,img.height*2))
    x0,x1=max(0,xs.min()-4),min(img.width,xs.max()+5)
    y0,y1=max(0,ys.min()-4),min(img.height,ys.max()+5)
    im=pixels[y0:y1,x0:x1,:3].copy()
    alpha=a[y0:y1,x0:x1]
    # Extend foreground colours through the transparent padding. No matte colour
    # is introduced at the rim when magnifying premultiplied footage.
    empty=alpha<16
    _,at=distance_transform_edt(empty,return_indices=True)
    im[empty]=im[at[0],at[1]][empty]
    yuv=cv2.cvtColor(im,cv2.COLOR_RGB2YCrCb)
    lum=yuv[:,:,0].astype('float32')/255
    border=10;core=224-2*border
    padded=np.pad(lum,((border,224),(border,224)),mode="edge")
    h,w=lum.shape
    out=np.zeros((h*3,w*3),np.float32)
    for y in range(0,h,core):
        for x in range(0,w,core):
            patch=padded[y:y+224,x:x+224]
            result=session().run(None,{'input':np.ascontiguousarray(patch[None,None])})[0][0,0]
            ph,pw=min(core,h-y),min(core,w-x)
            out[y*3:(y+ph)*3,x*3:(x+pw)*3]=result[border*3:(border+ph)*3,border*3:(border+pw)*3]
    target=(w*2,h*2)
    fine=cv2.resize(np.clip(out,0,1)*255,target,interpolation=cv2.INTER_AREA)
    color=cv2.resize(yuv,target,interpolation=cv2.INTER_CUBIC)
    # Avoid ringing on textured fabric and high contrast hair.
    color[:,:,0]=np.clip(.70*fine+.30*color[:,:,0],0,255).round().astype(np.uint8)
    rgb=cv2.cvtColor(color,cv2.COLOR_YCrCb2RGB)
    coverage=cv2.resize(alpha,target,interpolation=cv2.INTER_LINEAR)
    sprite=np.dstack((rgb,coverage))
    sprite[coverage==0]=0
    master=Image.new("RGBA",(img.width*2,img.height*2));master.paste(Image.fromarray(sprite),(int(x0)*2,int(y0)*2))
    return master
