import sys,json,math,subprocess,bisect
from pathlib import Path
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor
from PIL import Image,ImageDraw
from stage import plate,titleplate,font,label,bubbleball
from art import generate
R=Path(__file__).resolve().parent
FPS=24
D=json.loads((R/'timeline.json').read_text())
SC=D['scenes']
CAST=('one','y','two','three','sheriff')
BASE={'one':(288,662,152),'y':(545,686,387),'two':(812,662,247),'three':(1030,642,315),'sheriff':(1285,669,365)}
def clip(x):return max(0,min(1,x))
def ease(x):
 t=clip(x);return t*t*(3-2*t)
def lerp(a,b,t):return a+(b-a)*t
def ramp(t,a,b):return clip((t-a)/(b-a))
# World positions are authored across shot boundaries. Each move begins and ends at rest.
MOVES={
1:[('y',460,686,'walk')],2:[('one',235,662,'walk')],3:[],4:[('three',1085,642,'walk'),('y',544,686,'walk')],
5:[('one',305,662,'walk')],6:[],7:[],8:[],9:[],10:[],11:[('three',1078,642,'walk')],12:[],
13:[('y',430,680,'walk'),('one',441,630,'walk')],14:[('one',476,643,'walk')],15:[('one',640,644,'hop')],
16:[('two',817,650,'hop')],17:[('y',690,678,'hop')],18:[('three',963,646,'hop')],
19:[('one',148,443,'walk')],20:[],21:[],22:[('y',479,671,'walk')],23:[('one',380,633,'walk')],24:[],
25:[('one',960,577,'walk'),('two',813,606,'walk')],26:[('three',665,632,'walk')],27:[('one',1070,520,'walk')],28:[('one',1206,341,'climb')],29:[('one',1444,509,'slide')],30:[('one',1434,615,'walk')],
31:[('y',530,685,'walk')],32:[],33:[('two',804,650,'walk')],34:[],35:[],36:[]}
# Use a new establishing angle at each of the six games.
STARTS=[]
for i,s in enumerate(SC,1):
 if (i-1)%6==0:pos={r:BASE[r][:2] for r in CAST}
 if i==25:pos.update(sheriff=(322,668),y=(549,686),one=(943,592),two=(813,617),three=(695,645))
 STARTS.append(pos.copy())
 for r,x,y,_ in MOVES[i]:pos[r]=(x,y)
@lru_cache(200)
def mouths(k):
 f=R/'audio/qa'/f'{k}-lips.json'
 data=json.loads(f.read_text())['mouthCues'];return ([r['start'] for r in data],[r['value'] for r in data])
def lip(e,f):
 t=(f-e['at'])/24;starts,vals=mouths(e['id']);v=vals[max(0,bisect.bisect_right(starts,t)-1)]
 return {'X':'closed','A':'closed','B':'E','C':'E','D':'A','E':'O','F':'O','G':'F','H':'A'}.get(v,'closed')
def state(i,f):
 s=SC[i-1];es=s['events'];ev=next((e for e in es if e['at']<=f<e['end']),None)
 elapsed=(f-s['at'])/24; a=(es[4]['end']-s['at'])/24; dur=(s['end']-s['at'])/24
 # Demonstrations begin after the child has answered. The introduction and chase use longer blocking.
 t=ramp(elapsed,a+.08,dur-.24);v=ease(t)
 actors={}
 for idx,r in enumerate(CAST):
  x,y=STARTS[i-1][r];z=0; act='idle';j=0;m='closed'
  if ev and ev['role']==r:
   m=lip(ev,f)
   dt=(f-ev['at'])/24
   phase=ramp(dt,0,min(1.15,(ev['end']-ev['at'])/24))
   if 0<phase<1:
    act=('point' if r=='sheriff' else 'wave' if ev['id'].startswith('e') else 'pass')
    j=round(24*phase)
  elif (f+idx*29)%107 in (0,1):m='blink'
  if i in (20,21) and r=='y':
   act='peek'; j=round(12*(ease(ramp(elapsed,0,1.1)) if i==20 else 1-ease(ramp(elapsed,dur-2,dur-.3))))
  if i in (7,8,9,10,11,12,32,34) and r in ('one','two','three','y','sheriff') and 0<t<1:
   act='pass';j=round(24*clip((t-(idx%3)*.1)*1.36))
  if i in (1,35,36) and 0<t<1 and r in ('y','sheriff','three'):
   act='wave';j=round(24*t)
  if i==31 and r=='y' and 0<t<1:act='cup';j=round(24*t)
  for moving,xx,yy,how in MOVES[i]:
   if r!=moving:continue
   if how=='slide':
    x=lerp(x,xx,v);y=lerp(y,yy,ease(v))
   elif how=='hop':
    hops=2 if i==17 else 1
    hstep=min(hops-1,int(t*hops));phase=t*hops-hstep
    flight=ramp(phase,.22,.79);z=-4*65*flight*(1-flight)
    zpos=(hstep+ease(flight))/hops
    x=lerp(x,xx,zpos);y=lerp(y,yy,zpos)
    if 0<t<1:act='hop';j=round(24*phase)
   else:
    direction='L' if xx<x else 'R'
    length=math.hypot(xx-x,yy-y)
    x=lerp(x,xx,v);y=lerp(y,yy,v)
    if 0<t<1:
     strength=round(4*min(ease(t/.14),ease((1-t)/.14)))
     act='walk'+direction+str(strength);j=round(((v*max(1,round(length/(62 if r in ('sheriff','y') else 52)))+.25)%1)*24)
   break
  if r=='one' and i==28 and t>.8:
   act='sit';j=round(24*ease(ramp(t,.8,1)))
  if r=='one' and i==29:
   act='sit';j=round(24*(1-ease(ramp(t,.83,1))))
  actors[r]=(round(x),round(y+z),BASE[r][2],(r,act,j,m),round(y))
 return ev,actors,t
def sprite_key(k):return '|'.join(map(str,k))
def atlas():
 keys=set(); exposure=[]
 for i,s in enumerate(SC,1):
  shot=[]
  for n in range(s['at'],s['end']):
   ev,aa,t=state(i,n);record={}
   for r,(x,y,h,k,g) in aa.items():
    keys.add(k);record[r]=(sprite_key(k),x,y)
   shot.append(record)
  exposure.append(shot)
 manifest={}
 for r in CAST:
  rkeys=sorted(k for k in keys if k[0]==r)
  first=generate(*rkeys[0]);w,h=first.size
  for start in range(0,len(rkeys),24):
   sheet=Image.new('RGBA',(w*6,h*4))
   for j,k in enumerate(rkeys[start:start+24]):
    cel=generate(*k); assert cel.size==(w,h)
    x=j%6*w;y=j//6*h;sheet.paste(cel,(x,y))
    manifest[sprite_key(k)]=[f'{r}-{start//24:02}.webp',x,y,w,h]
   sheet.save(R/'sprites'/f'{r}-{start//24:02}.webp',lossless=True,method=1,exact=True)
 (R/'sprites/index.json').write_text(json.dumps(manifest,separators=(',',':')))
 # A compact exposure sheet records the five exact cell IDs and screen anchors at each frame.
 order={key:i for i,key in enumerate(manifest)}
 compact=[[[[order[v[0]],v[1],v[2]] for v in rec.values()] for rec in shot] for shot in exposure]
 (R/'sprites/exposures.json').write_text(json.dumps(dict(roles=CAST,keys=list(manifest),shots=compact),separators=(',',':')))
 print(len(keys),'full-frame cells',D['frames'],'frames',flush=True)
@lru_cache(1)
def index():return json.loads((R/'sprites/index.json').read_text())
@lru_cache(6)
def page(name):
 with Image.open(R/'sprites'/name) as im:return im.convert('RGBA')
@lru_cache(640)
def pic(k,h):
 p,x,y,w,hh=index()[sprite_key(k)]
 im=page(p).crop((x,y,x+w,y+hh))
 return im.resize((round(w*h/hh),h),Image.Resampling.LANCZOS)
@lru_cache(1)
def exposure():
 ex=json.loads((R/'sprites/exposures.json').read_text())
 return ex['shots'],[(r,a,int(j),m) for r,a,j,m in (key.split('|') for key in ex['keys'])]
@lru_cache(192)
def subtitle(en,ko,role):
 im=Image.new('RGBA',(1456,132));d=ImageDraw.Draw(im)
 d.rounded_rectangle((0,0,1455,131),radius=30,fill='#193b40f7' if role!='pause' else '#164f48fa',outline='#ffe6b5',width=3)
 k=39
 while d.textlength(en,font=font(k))>1352:k-=1
 label(d,(728,42),en,k,'#fff7e4');label(d,(728,96),ko,26,'#f7deb9')
 return im
@lru_cache(12)
def heading(ch):
 ko,en=titleplate(ch);im=Image.new('RGBA',(482,87));d=ImageDraw.Draw(im)
 d.rounded_rectangle((0,0,478,82),24,fill='#174a46f0',outline='#f4d49a',width=3)
 label(d,(240,43),ko+'  ·  '+en,26,'#fff5d9')
 return im
BALL=bubbleball(55)
# Handoffs preserve the ball position from one shot into the next.
def prop(i,aa,t):
 start,end={6:('three','three'),7:('three','y'),8:('y','two'),9:('two','three'),10:('three','one'),11:('one','three'),12:('three','y'),
            31:('three','three'),32:('three','one'),33:('one','one'),34:('one','basket'),35:('basket','basket'),36:('basket','basket')}.get(i,(None,None))
 if not start:return None
 def xy(r):
  if r=='basket':return (1316,633)
  x,y,h,*_=aa[r]
  return (x+(38 if r in ('y','sheriff') else -28),y-32)
 x,y=xy(start);xx,yy=xy(end)
 v=ease(ramp(t,.12,.88));px=lerp(x,xx,v);py=lerp(y,yy,v)
 if i==9:
  # Wind up from floor level, release at wrist height, settle the catch to the ground.
  from_h=aa[start][2]*(.27 if start=='one' else .49)
  to_h=aa[end][2]*(.27 if end=='one' else .49)
  height=lerp(from_h,to_h,v)*ease(ramp(t,0,.15))*(1-ease(ramp(t,.83,1)))
  py-=height
 if i==9:py-=4*148*v*(1-v)
 if i==10:
  phase=ramp(t,.15,.84)
  if phase<=.5:
   w=phase*2; height=122*(1-w)+4*75*w*(1-w)
  else:
   w=2*phase-1; height=49*w+4*65*w*(1-w)
  py-=height*ease(ramp(t,0,.15))*(1-ease(ramp(t,.84,1)))
 if i==34:py-=4*96*v*(1-v)
 return round(px),round(py)
def frame(i,n):
 s=SC[i-1];ch=s['chapter'];ev,aa,t=state(i,n)
 im=plate(ch).copy();d=ImageDraw.Draw(im)
 sh,keys=exposure();rec=sh[i-1][n-s['at']]
 for r in sorted(CAST,key=lambda r:aa[r][4]):
  x,y,h,k,g=aa[r];cell,xx,yy=rec[CAST.index(r)]
  assert (keys[cell],xx,yy)==(k,x,y)
  # Ground shadow stays planted while its owner is in flight.
  d.ellipse((x-h*.16,g-6,x+h*.16,g+5),fill='#b78966')
  sole={'y':461/480,'sheriff':461/480,'one':260/269,'two':384/394,'three':563/572}[r]
  sp=pic(keys[cell],h);im.paste(sp,(x-sp.width//2,y-round(sp.height*sole)),sp)
 if ch=='seek':
  # The physical playhouse masks One only while she is behind its wall.
  from stage import house
  house(im,90,289,.92)
 point=prop(i,aa,t)
 if point:
  im.paste(BALL,(point[0]-27,point[1]-27),BALL)
  if i in (34,35,36) and point[0]>=1278 and point[1]>=622:
   d.rounded_rectangle((1255,634,1380,698),radius=8,fill='#ae7845',outline='#7b5736',width=3)
   for yy in (644,664,683):d.line((1258,yy,1376,yy),fill='#e0b27b',width=5)
 if i==31:
  x,y,h,_,_=aa['y']
  # A painted bottle lifts with the drinking hand and settles back down.
  reach=math.sin(math.pi*t)**2
  bx=round(x+48-27*reach);by=round(y-h*.23-64*reach)
  d.rounded_rectangle((bx-12,by-43,bx+12,by),radius=7,fill='#83cfd3',outline='#357e89',width=3)
  d.rounded_rectangle((bx-8,by-51,bx+8,by-42),radius=3,fill='#eccc7e')

 # Cut between locked wide and detail shots. Both cameras sample the same exposure.
 focus={3:865,4:745,7:558,8:679,9:889,10:695,14:500,15:600,16:800,17:664,20:550,21:550,22:390,23:380,27:1010,28:1140,29:1220,31:555,32:760,34:950,35:800}.get(i)
 if focus is not None and (n< s['events'][2]['at'] or n>=s['events'][5]['at']):
  width,height=1256,707
  left=round(max(0,min(1536-width,focus-width/2)))
  im=im.crop((left,33,left+width,33+height)).resize((1536,864),Image.Resampling.BICUBIC)
  d=ImageDraw.Draw(im)
 elif i in (2,5,6,11,13,19,24,26,30,33,36) and n < s['events'][0]['end']:
  who=s['events'][0]['role']; x,y,h,*_=aa[who]
  width,height=990,557; left=round(max(0,min(1536-width,x-width/2)))
  top=round(max(0,min(864-height,y-height+75)))
  im=im.crop((left,top,left+width,top+height)).resize((1536,864),Image.Resampling.BICUBIC)
  d=ImageDraw.Draw(im)
 hdr=heading(ch);im.paste(hdr,(36,27),hdr)
 if ev:
  sub=subtitle(ev['en'],ev['ko'],ev['role']);im.paste(sub,(40,714),sub)
 if ev and ev['role']=='pause':
  d.rounded_rectangle((606,650,930,705),25,fill='#fbe2a9',outline='#855a39',width=2)
  label(d,(768,677),'윤수가 말할 차례',25,'#49372b')
 return im
def shot(i):
 s=SC[i-1];target=R/'qa'/f'{i:02}.mp4'
 args=['ffmpeg','-y','-v','error','-f','rawvideo','-pixel_format','rgb24','-video_size','1536x864','-framerate','24','-i','-','-an','-vf','scale=1920:1080:flags=lanczos,format=yuv420p','-c:v','libx264','-threads','3','-preset','fast','-crf','19','-g','48','-bf','0',str(target)]
 with subprocess.Popen(args,stdin=subprocess.PIPE) as proc:
  for n in range(s['at'],s['end']):proc.stdin.write(frame(i,n).tobytes())
  proc.stdin.close()
  if proc.wait():raise RuntimeError(i)
 print('shot',i,flush=True)
def mux():
 files=R/'qa/shots.txt';files.write_text(''.join(f"file '{i:02}.mp4'\n" for i in range(1,37)))
 subprocess.run(['ffmpeg','-y','-v','error','-f','concat','-safe','0','-i',str(files),'-i',str(R/'mix.wav'),'-c:v','copy','-c:a','aac','-b:a','144k','-movflags','+faststart',str(R/'delivery/Playground_Pals_1080p.mp4')],check=True)
if __name__=='__main__':
 if sys.argv[1]=='atlas':atlas()
 else:
  with ProcessPoolExecutor(4) as pool:list(pool.map(shot,range(1,37)))
  mux()
