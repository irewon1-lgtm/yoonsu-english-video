from pathlib import Path
from PIL import Image,ImageOps
R=Path(__file__).resolve().parent
def drawing_key(r,a,j,m):
 family='talk'
 n=({'closed':0,'blink':0,'E':1,'A':2,'O':3,'F':1} if r!='y' else {'closed':0,'blink':7,'E':1,'A':3,'O':4,'F':5})[m]
 def pose(frames):
  return frames[round(j*(len(frames)-1)/24)]
 if a.startswith('walk') or a=='turn':
  family='walkL' if 'L' in a else 'walk'
  n=round((j%24)*(65 if r=='y' else 11)/24)
 elif a=='hop':
  family='sheet';n=pose(range(9) if r=='y' else [0,1,2,3,4,5,0])
 elif a=='sit':
  family='sheet';n=pose([0,1,6,6])
 elif a in ('peek','cup'):
  family='special';n=round(3*j/12) if a=='peek' else pose([4,5,6,7,7,6,5,4])
 elif a in ('wave','pass','point'):
  if r=='y':
   family='wave' if a=='wave' else 'pass';n=pose(list(range(9 if a=='wave' else 12)))
  elif r=='sheriff' and a in ('point','wave'):
   family='cue';n=pose(range(12))
  else:
   family='sheet';n=pose({'sheriff':[0,1,2,3,4,5,6,0],'one':[0,1,7,8,0],'two':[0,6,7,6,0],'three':([0,6,7,6,0] if a=='wave' else [0,1,4,5,3,0])}[r])
 return r,family,n,'cel'
def generate(r,f,n,_):
 p=R/'cast'/r/f'{f.removesuffix("L")}-{n:02}.webp'
 with Image.open(p) as im:
  cel=im.convert('RGBA')
 return ImageOps.mirror(cel) if f.endswith('L') else cel
