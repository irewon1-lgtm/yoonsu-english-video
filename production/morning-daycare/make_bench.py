"""Four intact pre-shoe bench positions on a registered camera."""
from pathlib import Path
from PIL import Image
import cv2
import numpy as np
from compose_strips import pack

R=Path(__file__).resolve().parent
d=R/'actions/shoes_prepare'
with Image.open(d/'source/bench-actions.png') as asset: raw=asset.convert('RGB')
w,h=raw.size
tile_w,tile_h=w//2,h//2
pieces=[np.array(raw.crop((i%2*tile_w,i//2*tile_h,(i%2+1)*tile_w,(i//2+1)*tile_h))) for i in range(4)]
roi=np.ones((tile_h,tile_w),dtype=np.uint8)*255
roi[:,:]=0
roi[20:tile_h-10,10:int(tile_w*.32)]=255
roi[:int(tile_h*.24),int(tile_w*.87):tile_w-5]=255
anchor=cv2.cvtColor(pieces[0],cv2.COLOR_RGB2GRAY)
mask=np.zeros((tile_h,tile_w),dtype=np.uint8)
mask[:,int(tile_w*.35):]=255
soft=(cv2.GaussianBlur(mask,(0,0),5)/255.)[:,:,None]
frames=[]
for im in pieces:
    gray=cv2.cvtColor(im,cv2.COLOR_RGB2GRAY)
    mat=np.eye(2,3,dtype=np.float32)
    try:
        _,mat=cv2.findTransformECC(anchor,gray,mat,cv2.MOTION_TRANSLATION,
            (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,80,1e-6),inputMask=roi)
    except cv2.error:
        mat=np.eye(2,3,dtype=np.float32)
    mat[:,2]=np.clip(mat[:,2],-4,4)
    aligned=cv2.warpAffine(im,mat,(tile_w,tile_h),
      flags=cv2.INTER_CUBIC|cv2.WARP_INVERSE_MAP,borderMode=cv2.BORDER_REPLICATE)
    composite=(aligned*soft+pieces[0]*(1-soft)).round().astype(np.uint8)
    frames.append(Image.fromarray(composite).convert('RGBA').resize((1280,720),Image.Resampling.LANCZOS))
pack(d,None,frames,[10,10,11,11],[w,h],'Four native photographed 836×470-class positions. Translated fixed wall pixels register each angle. Opaque plates retain bench occlusion.',
 [{'frame':0,'state':'carry loop grasped above floor precedes lowering'},
  {'frame':10,'state':'hold carry loop while base lands'},
  {'frame':20,'state':'release handle, hand braces on seat'},
  {'frame':31,'state':'hips on seat, hands ready'}],
 'day clothes, one shoe already fastened','same staged bench')
