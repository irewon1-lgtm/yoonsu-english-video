from pathlib import Path
import json,collections
from PIL import Image,ImageDraw
import cv2,numpy as np
from film import exposure,CAST,SC,generate
R=Path(__file__).resolve().parent
O=R/'qa/frame-audit';O.mkdir(parents=True,exist_ok=True)
shots,keys=exposure()
groups=collections.defaultdict(list)
for k in keys:groups[(k[0],k[1])].append(k)
def view(k,bg,size):
 im=generate(*k);im.thumbnail((size,size),Image.Resampling.LANCZOS)
 layer=Image.new('RGB',(size,size),bg);layer.paste(im,(0,0),im);return layer
flags=[];report=[]
for role in CAST:
 items=[(fam,sorted(v,key=lambda k:k[2])) for (r,fam),v in groups.items() if r==role]
 seq=[k for _,v in sorted(items) for k in v]
 for page in range(0,len(seq),32):
  cells=seq[page:page+32];out=Image.new('RGB',(8*136,((len(cells)+7)//8)*157),'#314052');d=ImageDraw.Draw(out)
  for j,k in enumerate(cells):
   x=(j%8)*136;y=(j//8)*157
   out.paste(view(k,'#293847' if j%2 else '#f5dfba',132),(x,y))
   d.text((x+5,y+134),f'{k[1]} {k[2]:02}',fill='white')
  out.save(O/f'{role}-{page//32}.jpg',quality=93)
for k in keys:
 arr=np.array(generate(*k));alpha=arr[:,:,3]
 mask=(alpha>30).astype('uint8')
 n,lab,stats,_=cv2.connectedComponentsWithStats(mask)
 parts=[]
 for x,y,w,h,area in stats[1:]:
  box=arr[y:y+h,x:x+w];solid=area/(w*h)
  light=(box[:,:,:3].min(2)>227)&(box[:,:,3]>30)
  if w>65 and h>60 and solid>.93 and light.mean()>.48:parts.append([int(x),int(y),int(w),int(h)])
 if parts:flags.append([k,parts])
 report.append({'key':k[:3],'occupied_pixel_count':int(mask.sum()),'suspect_rectangles':parts})
trace=[]
for i,shot in enumerate(shots):
 runs={}
 for role_ix,r in enumerate(CAST):
  sequence=[]
  for fi,actors in enumerate(shot):
   key=keys[actors[role_ix][0]]
   if not sequence or sequence[-1][1]!=key:sequence.append([fi,key])
  runs[r]=sequence
 trace.append({'shot':i+1,'frames':len(shot),'roles':runs})
(O/'all-poses.json').write_text(json.dumps(report));(O/'all-frame-runs.json').write_text(json.dumps(trace))
print('possible rectangle flags',flags,'frames',sum(map(len,shots)),flush=True)
