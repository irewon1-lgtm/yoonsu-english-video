"""The painted woodland playground is a single registered panorama in every scene."""
from pathlib import Path
from functools import lru_cache
from math import sin,cos,pi
from PIL import Image,ImageDraw,ImageFont,ImageOps
ROOT=Path(__file__).resolve().parent
W,H=1536,864
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
@lru_cache(80)
def font(k):return ImageFont.truetype(FONT,k,index=1)
def label(d,p,s,k,c):d.text(p,s,font=font(k),anchor='mm',fill=c)
@lru_cache(30)
def prop_image(name,w,h):
 im=Image.open(ROOT/'sets'/(name+'.webp')).convert('RGBA')
 im.thumbnail((w,h),Image.Resampling.LANCZOS)
 return im
def bubbleball(n=72):return prop_image('ball',n,n)
@lru_cache(1)
def panorama():return ImageOps.fit(Image.open(ROOT/'sets/playground-painted.png').convert('RGB'),(W,H),method=Image.Resampling.LANCZOS)
def mark(d,pts,color,width,seed):
 # The second dry-pencil stroke is placed on the outer edge of each chalk line.
 for k,(a,b) in enumerate(zip(pts,pts[1:])):
  points=[(round(a[0]+(b[0]-a[0])*i/24),round(a[1]+(b[1]-a[1])*i/24+sin((i+seed+k)*1.7)*.9)) for i in range(25)]
  d.line(points,fill=color,width=width,joint='curve')
  d.line([(x-2,y+3) for x,y in points],fill='#fae7b7',width=1)
@lru_cache(8)
def plate(ch):
 im=panorama().copy();d=ImageDraw.Draw(im)
 if ch=='chalk':
  for i,col in enumerate(('#bf5650','#e9944c','#d6ab48')):
   x=475+i*164;y=675-i*3
   mark(d,[(x-76,y+20),(x-43,y-33),(x+87,y-33),(x+73,y+20),(x-76,y+20)],col,5,i)
   label(d,(x+9,y-8),str(i+1),33,'#ffefcd')
  chalk=prop_image('chalk',77,69);im.paste(chalk,(289,600),chalk)
 if ch=='finish':
  basket=prop_image('basket',175,142);im.paste(basket,(1433-basket.width//2,697-basket.height),basket)
 return im
@lru_cache(1)
def cottage_occluder():
 # Only foreground scenery occludes a child who walks behind the little house.
 scale=W/835
 outline=[(22,250),(19,174),(8,168),(27,131),(45,109),(66,93),(67,83),(82,82),(92,88),(101,89),(112,100),(125,113),(147,134),(160,163),(162,177),(152,185),(153,251),(145,264),(101,266),(49,270),(25,262)]
 mask=Image.new('L',(W,H));ImageDraw.Draw(mask).polygon([(round(x*scale),round(y*scale)) for x,y in outline],fill=255)
 return mask
def house(im,*_):im.paste(panorama(),(0,0),cottage_occluder())
def titleplate(ch):
 return {'gate':('같이 놀자!','Meet at the Gate'),'ball':('빨간 공을 받아!','Pass the Ball'),'chalk':('분필 길을 콩콩','Hopscotch'),'seek':('꼭꼭 숨어라','Hide and Seek'),'slide':('내 차례, 네 차례','Slide Together'),'finish':('내일 또 만나!','One Last Game')}[ch]
