"""Clean the pale backing on the invitation sheet; orient the floating labels."""
from pathlib import Path
import numpy as np,cv2
from PIL import Image,ImageOps
R=Path(__file__).resolve().parent
def cue_matte(image):
 a=np.array(image)
 opaque=a[:,:,3].astype(float)
 # Retain only the contiguous drawn silhouette. Background bloom is below
 # this opacity range, including the vertical edge under the sheriff's cap.
 mask=(opaque>=213).astype('uint8')
 _,lab,stats,_=cv2.connectedComponentsWithStats(mask)
 solid=(lab==(1+np.argmax(stats[1:,4]))).astype('uint8')
 outline=cv2.dilate(cv2.morphologyEx(solid,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8)),np.ones((3,3),np.uint8))
 a[:,:,3]=np.clip((opaque-202)*255/32,0,255)*outline
 a[a[:,:,3]==0]=0
 return Image.fromarray(a)
def left_number(image):
 # The body turns as a whole. Its floating written numeral keeps its reading direction.
 a=np.array(image);alpha=a[:,:,3]
 n,lab,stats,_=cv2.connectedComponentsWithStats(((alpha>60)&(a[:,:,:3].max(2)<110)).astype('uint8'))
 top=sorted((tuple(row)+(i,) for i,row in enumerate(stats[1:],1) if row[4]>300),key=lambda v:v[1])[0]
 x,y,w,h,area,ix=top
 assert h<150 and y<135,(x,y,w,h)
 region=cv2.dilate((lab==ix).astype('uint8'),np.ones((7,7),np.uint8))>0
 yy,xx=np.where(region)
 glyph=np.zeros_like(a);glyph[region]=a[region];a[region]=0;body=ImageOps.mirror(Image.fromarray(a))
 glyph=Image.fromarray(glyph).crop((xx.min(),yy.min(),xx.max()+1,yy.max()+1))
 body.alpha_composite(glyph,(int(511-xx.max()),int(yy.min())))
 return body
