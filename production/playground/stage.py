"""Playground scenic plates on one consistent park ground plane."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
from functools import lru_cache
import math
ROOT=Path(__file__).resolve().parent
W,H=1536,864
FONT='/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'
@lru_cache(80)
def font(k):return ImageFont.truetype(FONT,k,index=1)
def label(d,p,s,k,c):d.text(p,s,font=font(k),anchor='mm',fill=c,stroke_width=0)
def slides(d,x,y,s):
 def pts(a):return [(round(x+u*s),round(y+v*s)) for u,v in a]
 def line(a,c,w):d.line(pts(a),fill=c,width=round(w*s),joint='curve')
 def poly(a,c):d.polygon(pts(a),fill=c)
 def eye(u,v,r,c):d.ellipse(pts([(u-r,v-r),(u+r,v+r)]),fill=c)
 for a,b in [((0,38),(-9,220)),((83,42),(86,221)),((53,54),(-62,220))]:
  line([a,b],'#456264',10)
 for n in range(8):
  v=65+n*18;u=46-n*12;line([(u-14,v),(u+14,v)],'#eec57f',7)
 poly([(-18,53),(93,53),(93,68),(-18,68)],'#c48248')
 for u in (0,81):line([(u,-44),(u,51)],'#93542d',9)
 poly([(-29,-43),(36,-87),(109,-42),(98,-29),(-21,-29)],'#db694e')
 poly([(-27,-44),(36,-88),(53,-78),(-12,-42)],'#f49d65')
 # Smooth downhill flume and two raised rounded rails.
 path=[]
 for i in range(75):
  t=i/74;path.append((80+220*t,55+154*(t*t*(3-2*t))))
 line(path,'#185d7c',29);line([(u,v-4) for u,v in path],'#56aec2',22);line([(u,v-11) for u,v in path],'#9ce1d5',5)
 for u,v in ((0,48),(82,45)):eye(u,v,2,'#fbe6a8')
def house(im,x,y,s):
 d=ImageDraw.Draw(im)
 def p(xy):return [(x+a*s,y+b*s) for a,b in xy]
 d.polygon(p([(0,0),(230,0),(230,180),(0,180)]),fill='#b27848',outline='#875636',width=3)
 for i in range(10):d.line(p([(6+22*i,3),(6+22*i,178)]),fill='#cf9663',width=2)
 d.rounded_rectangle(p([(91,65),(171,181)]),radius=round(33*s),fill='#593f38')
 d.rectangle(p([(91,142),(171,180)]),fill='#593f38')
 d.polygon(p([(-18,4),(102,-71),(245,1),(238,17),(-14,17)]),fill='#42897d',outline='#326557',width=2)
 d.line(p([(-18,1),(102,-72),(245,-1)]),fill='#8bc39e',width=7)
 d.rounded_rectangle(p([(17,40),(68,94)]),radius=5,fill='#acd6cf',outline='#f4db9f',width=5)
 for a in [[(43,40),(43,94)],[(19,67),(67,67)]]:d.line(p(a),fill='#f3e0b6',width=4)
def bench(d,x,y):
 for ox in (10,170):d.rounded_rectangle((x+ox,y-45,x+ox+13,y+5),6,fill='#51716b')
 for dy in (-87,-66,-44):d.rounded_rectangle((x,y+dy,x+199,y+dy+15),6,fill='#c98148',outline='#9e693e',width=2)
def bubbleball(n=72):
 im=Image.new('RGBA',(n,n));d=ImageDraw.Draw(im);d.ellipse((2,2,n-3,n-3),fill='#df6047',outline='#913e36',width=3)
 d.arc((n*.19,-n*.08,n*.88,n*1.08),72,260,fill='#ffbb74',width=4)
 d.arc((n*.1,n*.11,n*.82,n*.74),183,244,fill='#ffe1a9',width=4)
 return im
@lru_cache(8)
def plate(ch):
 park=ImageOps.fit(Image.open(ROOT/'sets/park.png').convert('RGB'),(W,H))
 d=ImageDraw.Draw(park)
 # The same equipment stays on the same side of the park.
 slides(d,1120,284,1.08);house(park,90,289,.92);bench(d,630,422)
 if ch=='chalk':
  for i in range(3):
   x=475+i*164;y=675-i*3;d.line([(x-76,y+20),(x-43,y-33),(x+87,y-33),(x+73,y+20),(x-76,y+20)],fill='#ffedd2',width=5,joint='curve')
   label(d,(x+9,y-6),str(i+1),32,'#fff6e0')
 if ch=='finish':
  d.rounded_rectangle((1255,609,1380,698),radius=13,fill='#b5804c',outline='#765332',width=3)
  for y in (631,652,673):d.line((1257,y,1377,y),fill='#e4ba83',width=5)
 return park
def titleplate(ch):
 titles={'gate':('같이 놀자!','Meet at the Gate'),'ball':('빨간 공을 받아!','Pass the Ball'),'chalk':('분필 길을 콩콩','Hopscotch'),'seek':('꼭꼭 숨어라','Hide and Seek'),'slide':('내 차례, 네 차례','Slide Together'),'finish':('내일 또 만나!','One Last Game')}
 return titles[ch]
