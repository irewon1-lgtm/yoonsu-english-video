import numpy as np
from PIL import Image
def slices(im,rows,cols):
 im=im.convert('RGBA')
 al=np.asarray(im)[:,:,3]>24
 def divide(m,n):
  a=[0]
  for k in range(1,n):
   middle=round(k*len(m)/n);rad=round(len(m)/n*.16)
   cuts=np.arange(middle-rad,middle+rad+1)
   # Choose an empty gutter nearest its nominal grid line.
   best=cuts[m[cuts]==m[cuts].min()]
   a.append(int(best[np.argmin(abs(best-middle))]))
  return a+[len(m)]
 ys=divide(al.sum(1),rows)
 cells=[]
 for ya,yb in zip(ys,ys[1:]):
  xs=divide(al[ya:yb].sum(0),cols)
  for xa,xb in zip(xs,xs[1:]):
   c=im.crop((xa,ya,xb,yb))
   # Drop stray low-alpha fringe only; keep disconnected numberlings.
   import cv2
   vals=np.array(c)
   n,lab,st,cen=cv2.connectedComponentsWithStats((vals[:,:,3]>13).astype('uint8'))
   ok=np.where(st[1:,4]>17)[0]+1
   keep=cv2.dilate(np.isin(lab,ok).astype('uint8'),np.ones((3,3),'uint8'))>0
   vals[~keep]=0;c=Image.fromarray(vals);c=c.crop(c.getbbox())
   cells.append(c)
 return cells
