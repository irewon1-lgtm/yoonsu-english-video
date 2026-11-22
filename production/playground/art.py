"""Complete vector drawings. Every exported cel has an invariant viewBox and floor."""
import math,sys
from pathlib import Path
from functools import lru_cache
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parent/'three'))
from vector import raster
import blocks
from design import path as P,ellipse as E,rect as R,group as G
from math import sin,cos,pi
def grad(name,a,b):
 return f'<linearGradient id="{name}" x2=".55" y2="1"><stop stop-color="{a}"/><stop offset="1" stop-color="{b}"/></linearGradient>'
def svg(body,defs=''):
 return f'<svg xmlns="http://www.w3.org/2000/svg" width="384" height="480" viewBox="0 0 240 300"><defs>{defs}</defs>{body}</svg>'
def seg(x,y,ln,a):
 return x+ln*sin(a*pi/180), y+ln*cos(a*pi/180)
def tintpath(d,c,w):return P(d,'none',c,w)
def eye(x,y,w,h,blink,dog=False):
 if blink:return tintpath(f'M{x-w} {y+1} q{w} 5 {2*w} -1','#46251b',2.3)
 return E(x,y,w,h,'#fff7ed','#694336',.85)+E(x+1.5,y+.3,w*.65,h*.92,'#633e2d')+E(x+2,y+.7,w*.43,h*.72,'#241c1a')+E(x+w*.40,y-h*.44,1.7,1.8,'#fff')
def mouth(x,y,m):
 if m in ('closed','blink'):return P(f'M{x-5.7} {y} q6 4.7 12 -1','none','#783d32',1.55)
 w,h={'A':(6,5.4),'E':(7,3.0),'O':(4.1,5.3),'F':(5.8,1.9)}[m]
 return E(x,y,w,h,'#70362d')+E(x+.2,y+h*.48,w*.57,h*.26,'#df8d83')
def humanhead(m,eyes_closed=False):
 a=E(121,79,43,49,'url(#skin)','#8f624f',1.2)+E(78,87,7,10,'#efb893')+E(165,84,6,9,'#eab28e')
 a+=P('M78 80 Q65 53 79 30 Q94 5 127 11 Q157 10 166 36 Q178 58 165 83 L159 77 Q158 64 156 55 Q148 60 140 60 L137 54 L135 61 L122 63 L119 56 L118 63 L104 64 L100 58 L100 64 L89 65 L83 82Z','url(#hair)','#493328',1.4)
 for k in range(7):
  x=86+10*k;a+=P(f'M{117+k*2} 17 Q{x-4} 28 {x} {50+4*sin(k)}','none','#6a5040',1.3)
 a+=P('M91 72 q10 -5 18 -2 M130 69 q10 -4 18 1','none','#53382e',2.6)
 a+=eye(102,80,8,6.1,m=='blink' or eyes_closed)+eye(140,78,7.5,6.0,m=='blink' or eyes_closed)
 a+=E(94,94,7,2.8,'#efb39b')+E(146,92,6.2,2.6,'#efb39b')+P('M122 85 q-1 6 3 6','none','#c48c73',1.7)+mouth(124,104,m)
 return a
def badge(x,y,scale=1):
 return G(P('M0 -10 Q4 -7 9 -7 Q10 4 0 10 Q-10 4 -9 -7 Q-4 -7 0 -10Z','#f5cb55','#845e34',1.2)+P('M0 -6 L1.8 -2.3 L6 -2 L3 1 L3.8 5 L0 3 L-3.8 5 L-3 1 L-6 -2 L-1.8 -2.3Z','#fff1a3'),f'translate({x} {y}) scale({scale})')
def doghead(m):
 a=E(117,80,49,42,'url(#fur)','#a26325',1.6)
 a+=P('M74 61 C57 61 49 79 54 104 Q55 116 66 117 Q75 115 77 99 L83 69Z','#995222','#71411d',2)
 a+=P('M153 57 Q170 56 177 75 Q183 96 172 102 Q163 100 162 85Z','#b66d2b','#864b21',1.7)
 a+=P('M86 65 q9 -6 18 -2 M127 61 q9 -5 17 0','none','#61391d',3)
 a+=eye(98,74,8.4,10,m=='blink')+eye(138,71,7.9,9.6,m=='blink')
 a+=P('M105 85 Q116 80 133 80 Q150 77 161 85 C176 98 156 114 137 118 Q113 124 93 111 Q83 100 91 93Z','url(#muzzle)','#bd8539',1.35)
 a+=P('M131 84 Q143 78 151 84 Q155 90 143 95 Q136 96 130 90Z','#463729','#382a20',1.1)+E(144,84,3.3,1.4,'#80756b')+mouth(137,105,m)
 a+=P('M68 55 Q61 46 68 38 Q77 32 82 24 Q105 11 135 16 Q156 19 168 35 L162 47 Q121 60 73 60Z','url(#navy)','#203a55',2.2)
 a+=P('M71 52 Q116 54 162 39 L167 46 Q136 63 76 62Z','#304361','#1e3346',1.6)+P('M116 52 Q153 44 166 39 Q180 38 181 43 Q172 52 138 59 Q124 62 116 57Z','#293e50','#203145',1.5)+badge(111,36,1.02)
 return a
def body(role,action,j,m):
 t=j/24; pulse=sin(pi*t)**2
 dog=role=='sheriff'
 step=action.startswith('walk')
 direction=-1 if step and 'L' in action else 1
 strength=(int(action[-1])/4 if step and action[-1].isdigit() else 1)
 reach=action in ('pass','point','wave','peek','cup')
 # Knee compression is drawn by changing leg angles and hip height, with soles fixed.
 bend=pulse if action in ('hop','pass','cup') else 0
 if action=='hop':
  bend=max(max(0,1-abs(t-.18)/.18),.85*max(0,1-abs(t-.83)/.17))
 down=8*bend+(2*sin(2*pi*t)**2 if step else 0)
 lift=-2.6*bend if action=='pass' else 0
 skin='#e9b88e' if not dog else '#eeb751'; sleeve='#387855' if not dog else '#4373a0'
 defs=''.join(grad(*v) for v in [('skin','#ffe1bd','#edba99'),('hair','#513a2f','#261e1f'),('shirt','#52a46c','#31835b'),('navy','#305781','#182b4e'),('denim','#99b7d0','#678cad'),('fur','#ffd16b','#e9a63d'),('muzzle','#ffe29b','#f6c76c')])
 legs=''
 for side in (-1,1):
  n=(t+(0 if side==1 else .5))%1
  # Flat planted foot travels back uniformly; swing foot clears on a smooth arc.
  if step:
   shift=13-52*n if n<.5 else -13+26*((1-cos(2*pi*(n-.5)))/2)
   up=0 if n<.5 else 12*sin(2*pi*(n-.5))**2
   shift*=direction*strength;up*=strength
  else:shift=0;up=0
  x=118+side*17; foot=x+side*2+shift;fy=280-up
  knee=x+5*bend+(shift*.44)+3
  line=f'M{x} {204+down} Q{knee-3} {225+down} {knee} {240-up*.22} Q{knee+2} 255 {foot} {fy-5}'
  legs+=tintpath(line,'#354f66' if not dog else '#25394d',26)+tintpath(line,'url(#denim)' if not dog else 'url(#navy)',23)
  legs+=P(f'M{foot-12} {fy-8} Q{foot+1} {fy-5} {foot+9} {fy-10} L{foot+14} {fy-4} Q{foot+25} {fy-2} {foot+24} {fy+4} Q{foot+8} {fy+9} {foot-13} {fy+5}Z','#335780' if not dog else '#45454d','#374052',1.8)
  legs+=P(f'M{foot-13} {fy+3} Q{foot+3} {fy+6} {foot+23} {fy+1} L{foot+24} {fy+5} Q{foot+5} {fy+10} {foot-13} {fy+7}Z','#eee9dd' if not dog else '#31343e') 
 def arm(side):
  x=117+side*28;y=148
  a=side*9; b=side*5
  if step:a+=side*24*cos(2*pi*t)*strength*direction;b+=side*13*cos(2*pi*t)*strength*direction
  if reach:
   if action=='wave':a+=side*(70 if side==1 else 9)*pulse;b+=side*(139 if side==1 else 12)*pulse
   if action=='point':a+=side*(55 if side==1 else 5)*pulse;b+=side*(82 if side==1 else 4)*pulse
   if action=='pass':a+=side*27*pulse;b+=(68 if side==1 else 42)*pulse
   if action=='peek':a+=side*33*pulse;b-=side*166*pulse
   if action=='cup':a+=side*34*pulse;b-=side*96*pulse
  if action=='hop':a+=side*29*pulse;b+=side*57*pulse
  e=seg(x,y,25,a);w=seg(*e,24,b)
  if action=='peek':
   e=(e[0]+side*9*pulse,e[1]-36*pulse)
   w=(w[0]*(1-pulse)+(121+side*17)*pulse,w[1]*(1-pulse)+88*pulse)
  d=f'M{x} {y} Q{e[0]} {e[1]-3} {e[0]} {e[1]} Q{e[0]+(w[0]-e[0])*.46} {e[1]+(w[1]-e[1])*.47} {w[0]} {w[1]}'
  col='#44664b' if not dog else '#264968'
  ink=tintpath(d,col,18)+tintpath(d,sleeve,15)
  mid=seg(x,y,18,a);ink+=tintpath(f'M{mid[0]} {mid[1]} L{e[0]} {e[1]}','#223a66' if not dog else '#517fa4',14.5)
  ink+=E(*w,7.2,8.1,skin,'#ad8154',.9)
  return ink
 torso=P('M94 131 Q115 124 141 130 Q154 140 151 158 L151 202 Q127 215 87 205 L88 155 Q84 143 94 131Z','url(#navy)' if dog else 'url(#shirt)','#35534c',1.8)
 if not dog:
  torso+=P('M88 151 Q119 156 152 149 L152 161 Q118 168 88 161Z M88 180 Q119 186 152 178 L152 190 Q118 198 88 190Z','#20365e')
  torso+=P('M89 201 Q120 208 151 199 L150 209 Q121 216 89 209Z','#223657')+P('M102 129 L114 141 L120 132 L128 142 L139 128Z','#f8e5bd','#b8a384',1)
 else:
  torso+=P('M92 135 L107 145 L117 134 L126 146 L143 131 L127 127 L105 128Z','#7095ab')+P('M115 139 L121 137 L125 159 L119 167 L114 158Z','#22364d')+badge(137,152,.70)+P('M88 193 Q116 199 151 190 L151 198 Q118 208 88 201Z','#453d32')+R(114,195,12,7,'#edc571',2)
 if dog:
  torso+=P('M86 153 Q80 191 86 199 Q114 212 151 197 Q158 178 149 153 L145 189 Q118 201 90 193Z','url(#navy)')
  torso+=P('M88 192 Q118 198 151 188 L152 196 Q118 207 87 200Z','#473e32')+R(115,195,12,7,'#efcb65',2)
  torso+=P('M93 155 L109 157 L108 169 Q100 174 93 168Z','#42698a','#304d69',1.2)+P('M93 156 L101 162 L109 157','#6487a2')+E(101,162,1.15,1.15,'#f7d891')
  legs=P('M93 183 Q71 197 52 177 Q46 173 48 182 Q57 205 91 203Z','url(#fur)','#ad793b',1.2)+legs
 else:
  torso+=P('M125 145 L125 150 M126 146 L126 149','none','#e7ce9c',1.1)+P('M135 145 L143 144','none','#db9a46',2)
  legs+=P(f'M92 {210+down} q3 10 11 11 M138 {209+down} q-1 9 -8 11','none','#b2c7d6',1.4)
 upper=arm(-1)+R(107,119,26,21,skin,5)+torso+arm(1)+G(doghead(m) if dog else humanhead(m),(f'translate({lift-13:.3f} -7) scale(1.11)' if dog else f'translate({lift:.3f} 5)'))
 if action=='peek':
  # Hands cross in front of the eyes on the closed-eye pose.
  upper=torso+G(humanhead(m,pulse>.83),'translate(0 5)')+arm(-1)+arm(1)
 return raster(svg(legs+G(upper,f'translate(0 {down:.3f})'),defs),384,480)
def generate(role,action,j,m):
 if role in ('y','sheriff'):
  im=body(role,action,j,m)
  return im.transpose(Image.Transpose.FLIP_LEFT_RIGHT) if role=='sheriff' else im
 n={'one':1,'two':2,'three':3}[role];t=j/24;u=sin(t*pi)**2
 walk=action.startswith('walk')
 weight=int(action[-1])/4 if walk and action[-1].isdigit() else 1
 if walk and 'L' in action:t=(1-t)%1
 blk=blocks
 # Explicit square dimensions and constant viewBox keep the numeral and feet registered.
 blk.SIZE=(384,600)
 im=blk.draw(n,'closed' if m=='blink' else m,-.24,float(m=='blink'),t,
             .83*weight if walk else 0,0,0,-.32,(u*.9 if action not in ('idle',) and not walk else 0),performance=action,progress=t)
 # Preserve geometry including numeral; use a constant frame per model.
 box={1:(22,308,362,577),2:(22,183,362,577),3:(22,5,362,577)}[n]
 return im.crop(box)
