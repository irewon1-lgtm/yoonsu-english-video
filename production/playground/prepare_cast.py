from pathlib import Path
from PIL import Image,ImageOps
import numpy as np
from grid import slices
R=Path(__file__).resolve().parent
def register(role,family,images,flip=False):
 out=R/'cast'/role;out.mkdir(parents=True,exist_ok=True)
 ims=[im.convert('RGBA') for im in images]
 ims=[im.crop(im.getbbox()) for im in ims]
 pivots=[]
 for im in ims:
  arr=np.asarray(im); strip=arr[int(im.height*.49):int(im.height*.72)]
  cols=np.where(strip[:,:,3]>150)[1]
  pivots.append(float(np.median(cols)) if len(cols) else im.width/2)
 scale=min(460/ims[0].height, 486/max(im.height for im in ims),249/max(max(p,im.width-p) for im,p in zip(ims,pivots)))
 for n,(im,p) in enumerate(zip(ims,pivots)):
  im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
  cel=Image.new('RGBA',(512,512));cel.paste(im,(256-round(p*scale),492-im.height))
  if flip:cel=ImageOps.mirror(cel)
  cel.save(out/f'{family}-{n:02}.webp',lossless=True,method=1)
def special_cells(path):
 # Background of this sheet has a tinted semi-transparent matte. The original
 # drawing has a separate high-opacity foreground; recover its soft boundary.
 import cv2
 a=np.array(Image.open(path).convert('RGBA'))
 opacity=a[:,:,3].astype(float)
 mask=(opacity>216).astype('uint8')
 count,labels,stats,_=cv2.connectedComponentsWithStats(mask)
 keep=np.isin(labels,np.where(stats[1:,4]>500)[0]+1).astype('uint8')
 keep=cv2.morphologyEx(keep,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
 alpha=np.clip((opacity-206)*255/32,0,255)
 a[:,:,3]=(alpha*cv2.dilate(keep,np.ones((3,3),np.uint8))).astype('uint8')
 return slices(Image.fromarray(a),2,4)
if __name__=='__main__':
 for r,name in [('y','child'),('one','one'),('two','two'),('three','three'),('sheriff','sheriff')]:
  for fam,rows,cols in [('sheet',3,3),('talk',2,2),('walk',3,4),('cue',3,4),('special',2,4),('pass',3,4)]:
   path=R/'redesign'/f'{name}-{fam}.png'
   if path.exists():register(r,fam,(special_cells(path) if fam=="special" else slices(Image.open(path),rows,cols)),r=='sheriff')
 for fam,seq in [('talk',[Path(f'/dev/shm/zoo-dream/source/talk{i}.webp') for i in range(8)]),('wave',sorted(Path('/workspace/work/yoonsu-home/motion/wave').glob('*.webp'))),('walk',sorted(Path('/workspace/work/morning-daycare/assets/walk/frames').glob('*.png')))]:
  register('y',fam,[Image.open(p) for p in seq])
