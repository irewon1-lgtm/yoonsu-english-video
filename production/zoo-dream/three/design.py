"""Vector primitives and the illustration palette for the kitchen set."""
from math import sin,cos,pi
from vector import raster
from functools import lru_cache
def path(d,fill,stroke='none',w=2):
 return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{w}" stroke-linejoin="round" stroke-linecap="round"/>'
def ellipse(x,y,rx,ry,col,line='none',sw=1):
 return f'<ellipse cx="{x}" cy="{y}" rx="{rx}" ry="{ry}" fill="{col}" stroke="{line}" stroke-width="{sw}"/>'
def rect(x,y,w,h,c,r=0,edge='none',sw=1):
 return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{c}" stroke="{edge}" stroke-width="{sw}"/>'
def group(s,t):return f'<g transform="{t}">{s}</g>'
def grad(id,a,b):
 return f'<linearGradient id="{id}" x1="0" y1="0" x2=".65" y2="1" gradientUnits="objectBoundingBox"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
def svg(s,w,h,defs='',vb=None):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{vb or f"0 0 {w} {h}"}"><defs>{defs}</defs>{s}</svg>'
def use(s,x,y,scale=1,angle=0):return group(s,f'translate({x} {y}) rotate({angle}) scale({scale})')
def leaf(x,y,a,color,scale=1):
 return use(path('M0 0 Q-14 -8 -9 -26 Q7 -23 0 0Z',color),x,y,scale,a)
def kitchen():
 defs=grad('wall','#ffe9c3','#f2cfa2')+grad('sky','#9fdbdb','#fff2ca')+grad('cab','#78b9a1','#4a9085')+grad('wood','#ffcc8c','#e2a56d')+grad('floor','#e9caa1','#f6d7b2')
 a=rect(0,0,1280,720,'url(#wall)')+rect(0,0,1280,14,'#cf9063')+rect(0,14,1280,8,'#e8b080')
 # Large arched-top window and the distant rolling orchard.
 wshape='M435 302 V141 Q435 35 603 35 H704 Q865 35 865 141 V302 Z'
 defs+=f'<clipPath id="win">{path(wshape,"white")}</clipPath>'
 a+=path(wshape,'#fdf3d7','#bf9773',16)
 view=rect(430,25,438,281,'url(#sky)')+ellipse(745,93,37,37,'#fff1bd')
 for x,y in [(515,94),(640,126),(800,135)]:view+=ellipse(x,y,27,5,'#fff6dd')+ellipse(x-5,y-5,14,7,'#fff6dd')
 view+=path('M425 232 Q520 150 616 210 T879 184 V315 H425Z','#a7c99c')
 view+=path('M415 247 Q554 192 647 246 T880 213 V315 H415Z','#80b897')
 for x,y,sz in [(469,257,.9),(570,243,.55),(795,244,.78),(830,257,.9),(684,261,.44)]:
  tree=rect(-3,-28,6,35,'#9e9076')+path('M-21 -23 Q-39 -36 -22 -47 Q-22 -70 -4 -64 Q12 -78 20 -56 Q41 -52 29 -35 Q26 -20 4 -24Z','#70a888')
  view+=use(tree,x,y,sz)
 a+=f'<g clip-path="url(#win)">{view}</g>'+rect(642,40,12,268,'#fbebcc')+rect(437,165,425,8,'#fbebcc')+rect(418,299,462,15,'#d3a678',7)+rect(411,292,475,13,'#fff4dc',5)
 # Open shelves and ceramic vessels, with a set of hanging ladles.
 for x,y,w in [(43,143,314),(51,251,294),(944,132,300)]:
  a+=rect(x+8,y+8,w-10,12,'#d6af88',4)+rect(x,y,w,13,'#ab7358',5)+rect(x,y-2,w,5,'#e2ac80',3)
 pots=['#679c96','#f0ae81','#e5c276','#81bca8','#ce867b']
 def jar(x,y,n,c):
  return use(path('M-16 -42 Q-21 -35 -20 -17 L-18 -4 Q-15 2 13 0 Q19 0 19 -8 L20 -29 Q21 -39 15 -43Z',c)+rect(-16,-47,33,7,'#ad805e',3)+rect(-11,-27,23,12,'#fff1d6',4)+path('M-12 -34 L-13 -16','none','#ffffff',2),x,y,n)
 for i in range(5):a+=jar(77+i*62,143, .70+.12*((i+1)%3),pots[i])
 for i in range(4):a+=jar(982+i*68,131,.84+.11*(i%2),pots[4-i])
 for i in range(4):
  x=72+50*i; a+=use(path('M-19 -20 H16 V-10 Q16 0 4 0 H-5 Q-18 0 -19 -13Z',pots[i])+path('M15 -17 Q31 -20 26 -9 Q22 -5 16 -6','none',pots[i],4),x,250,1.1)
 for i in range(3):a+=ellipse(289,246-i*4,27,4,'#f5e7c1','#b5947e',1.5)
 a+=rect(960,181,254,7,'#bd9474',4)
 for i in range(4):
  x=985+i*62
  a+=ellipse(x,184,4,6,'none','#816b5a',2)+path(f'M{x} 191 V223','none','#aa8263',4)+use(ellipse(0,0,9,12,['#a1b2a2','#d9ae87','#80ada5','#d29c76'][i])+path('M-3 -7 L-4 2','none','#f7e3c0',2),x,231)
 # Counter tiles, sideboard and inset doors.
 a+=rect(0,321,1280,99,'#e7d6b8')
 for j in range(3):
  for i in range(-1,18):
   x=i*83+(j%2)*40; y=323+j*32
   a+=rect(x,y,80,29,['#f8ead1','#f5e5ca','#f8e6c8'][(i+2*j)%3],4)
 a+=rect(0,409,1280,162,'url(#cab)')+rect(0,397,1280,18,'#af765b',3)+rect(0,394,1280,8,'#fbd6a8',2)
 for i in range(8):
  x=i*165+10; a+=rect(x,430,149,108,'none',7,'#51968a',3)+rect(x+8,437,133,92,'none',4,'#88bca2',2)+rect(x+58,445,32,6,'#d1ab73',3)
 a+=rect(0,550,1280,16,'#527f72')+rect(0,566,1280,154,'url(#floor)')
 for x in range(-900,2000,120):
  a+=path(f'M{640+(x-640)*.55} 567 L{x} 720','none','#d4ad89',2)
 for y in (596,647):a+=rect(0,y,1280,2,'#dfb995')
 # Potted basil, cutting boards and cozy crockery.
 for x,y,sc in [(104,396,1.08),(895,393,.85)]:
  herb=''
  for j in range(8):
   dx=sin(2.2*j)*26; dy=40+j%3*10
   herb+=path(f'M0 -15 Q{dx} -30 {dx} {-dy}','none','#537d64',2)+leaf(dx,-dy,(-1)**j*42,['#7eaa75','#5f9475','#8eb176'][j%3],.65)
  a+=use(herb+path('M-21 -24 H21 L16 -2 Q0 4 -16 -2Z','#d1886a')+rect(-23,-27,46,8,'#eda282',3),x,y,sc)
 for x,y,r,col in [(1110,397,-6,'#bc895d'),(1157,397,8,'#dab084')]:
  a+=use(path('M-24 0 V-69 Q-24 -77 -11 -77 L-8 -92 Q-2 -104 5 -95 L10 -78 Q27 -78 27 -66 V0Z',col,'#ae805e',2)+ellipse(0,-88,3,3,'#f3d5aa'),x,y,1,r)
 # Utensil crock, kitchen towel.
 a+=use(path('M-8 -12 L-16 -55 M0 -17 L5 -60 M8 -13 L22 -58','none','#a27c65',4)+ellipse(-16,-59,6,9,'#ac886d')+ellipse(23,-61,6,9,'#d7ad78')+path('M-20 -31 Q0 -36 20 -31 L16 -2 H-15Z','#7ea8a7'),1210,396)
 return svg(a,1280,720,defs)
