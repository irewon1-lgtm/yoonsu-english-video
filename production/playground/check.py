import json,math,wave,hashlib
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
import film
from stage import font
root=Path(__file__).resolve().parent
shots,keys=film.exposure();idx=film.index(); previous=None;peak=0;total=0
assert len(shots)==36 and len(set(s['events'][4]['en'] for s in film.SC))==36
seen=set()
for i,(s,shot) in enumerate(zip(film.SC,shots,strict=True),1):
 assert len(shot)==s['end']-s['at'] and len(s['events'][4]['en'].split())==3
 previous=None
 for t,rec in enumerate(shot):
  assert len(rec)==5
  for j,(c,x,y) in enumerate(rec):
   assert keys[c][0]==film.CAST[j]
   seen.add(c)
   if previous is not None:peak=max(peak,math.dist((x,y),previous[j][1:]))
  previous=rec;total+=1
assert total==15864 and len(seen)==len(keys) and peak<42,peak
# Compare each stored cel to the independently regenerated full-body source drawing.
from art import generate
for num,k in enumerate(keys):
 name,x,y,w,h=idx[film.sprite_key(k)]
 a=film.page(name).crop((x,y,x+w,y+h))
 b=generate(*k); assert b.size==a.size and a.getbbox(),k
 # In transparent areas hidden RGB is irrelevant.
 aa=np.asarray(a);bb=np.asarray(b);assert np.array_equal(aa[:,:,3],bb[:,:,3]) and np.array_equal(aa[aa[:,:,3]>0],bb[bb[:,:,3]>0]),k
with wave.open(str(root/'mix.wav')) as w:
 assert w.getnframes()==total*2000
 for s in film.SC:
  q,m,c,r,p,e=s['events'];assert m['id']==r['id'] and c['id']=='cue' and p['end']-p['at']==96
  w.setpos(p['at']*2000);assert not any(w.readframes(192000))
out=root/'delivery';out.mkdir(exist_ok=True)
# Rebuild a proof strip from rendered exposures at real frame spacing.
c=Image.new('RGB',(1500,1010),'#f6f0df');d=ImageDraw.Draw(c)
d.text((24,12),'놀이터 전신 셀 · 실제 노출 프레임',font=font(32),fill='#214941')
for row,(i,role,title) in enumerate([(4,'y','윤수 · 친구 따라 걷기'),(15,'one','원 · 사방치기'),(16,'two','투 · 두 발 착지'),(29,'one','원 · 미끄럼틀'),(36,'sheriff','경장 · 작별 인사'),(35,'three','쓰리 · 손 흔들기')]):
 s=film.SC[i-1];a=s['events'][4]['end']+2;b=s['end']-6
 if i in (15,16):a+=4;b=a+24
 d.text((18,66+row*157),title,font=font(19),fill='#2b5148')
 for j in range(10):
  n=round(a+(b-a)*j/9);rr=shots[i-1][n-s['at']][film.CAST.index(role)]
  cell=film.pic(keys[rr[0]],96).copy()
  x=22+j*148; y=98+row*157
  flight=film.state(i,n)[1][role]
  dy=round((flight[1]-flight[4])*.32)
  c.paste(cell,(x+(128-cell.width)//2,y+dy),cell)
  d.text((x+28,y+96),f'f{n:05}',font=font(13),fill='#64574c')
c.save(out/'Playground_Motion_Review.jpg',quality=94)
report=dict(frames=total,fps=24,seconds=total/24,actors_per_frame=5,cels=len(keys),sheets=len({v[0] for v in idx.values()}),turns=36,max_anchor_displacement_per_frame=round(peak,2),all_atlas_cells_match_full_drawings=True,silent_response_intervals=36)
(root/'qa/report.json').write_text(json.dumps(report,indent=2));print(report)
