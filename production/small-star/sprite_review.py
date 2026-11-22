"""Create downloadable alpha sheets in the same order as the rendered exposures."""
from pathlib import Path
import json
from PIL import Image,ImageDraw
import numpy as np

ROOT=Path(__file__).resolve().parent
motion=ROOT/'motion'
spec=json.loads((motion/'index.json').read_text())
atlas_path=ROOT/'sheets'
atlas_path.mkdir(exist_ok=True)
summary={}
poster=Image.new('RGB',(1200,208*3),'#f7f1e6')
p=ImageDraw.Draw(poster)
for row,key in enumerate(('bed','lamp','wave')):
    record=spec['actions'][key]
    names=record['frames']+record.get('release',{}).get('frames',[])
    w,h=spec['tile']
    sheet=Image.new('RGBA',(4*w,((len(names)+3)//4)*h))
    compare=[]
    for n,name in enumerate(names):
        raw=Image.open(motion/name).convert('RGBA')
        assert raw.size==(w,h)
        alpha=np.array(raw.getchannel('A'))
        visible=np.where(alpha>=220)
        assert visible[0].size>10000 and (alpha==0).mean()>.56
        assert np.count_nonzero(alpha[[0,-1],:])==0 and np.count_nonzero(alpha[:,[0,-1]])==0
        compare.append((int(visible[0].max()),int(visible[0].min())))
        x,y=n%4*w,n//4*h
        sheet.paste(raw,(x,y))
        small=raw.copy()
        small.thumbnail((min(100,1056//len(names)-3),144))
        xpos=126+n*min(95,1056//len(names));ypos=row*208+31
        poster.paste(small,(xpos,ypos),small)
        p.text((xpos+10,ypos+125),str(n+1),fill='#2b243e')
    p.text((21,88+row*208),key.upper(),fill='#423257')
    sheet.save(atlas_path/(key+'.webp'),lossless=True,method=3,exact=True)
    summary[key]=dict(atlas=key+'.webp',cell=spec['tile'],origin=spec['anchor'],cols=4,
                      floor_pixels=[v[0] for v in compare],holds_ms=record['durationsMs']+record.get('release',{}).get('durationsMs',[]),
                      native_cell=record.get('sourceTile'),source_order=record.get('sourceCells'))
(s:=atlas_path/'index.json').write_text(json.dumps(summary,indent=2)+'\n')
poster.save(atlas_path/'order.jpg',quality=92)
print('PASS: three alpha sprite sequences:',[(k,len(v['holds_ms']),min(v['floor_pixels']),max(v['floor_pixels'])) for k,v in summary.items()])
