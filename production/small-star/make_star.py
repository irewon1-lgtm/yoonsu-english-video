"""Rasterize independent cut-paper drawings about one fixed pin."""
from pathlib import Path
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

d=Path(__file__).resolve().parent/'star'
d.mkdir(exist_ok=True)
rng=np.random.default_rng(700)
size=200
y,x=np.mgrid[:size,:size]
grain=rng.normal(0,.8,(size,size))
for n, angle in enumerate((27,23,15,5,-8,-19,-25,-21,-14,-6,3,9,12,10,7,3,1,0)):
    yaw=math.radians(angle)
    pin=np.array([100.,57.])
    center=np.array([100.,119.])
    roll=math.radians(angle*.32)
    rot=np.array([[math.cos(roll),-math.sin(roll)],[math.sin(roll),math.cos(roll)]])
    def transform(p):
        q=np.array(p)-pin
        q[0]*=math.cos(yaw)
        return tuple(pin+rot@q)
    vertices=[]
    for i in range(10):
        theta=-math.pi/2+i*math.pi/5
        radius=66 if i%2==0 else 32
        vertices.append(transform(center + radius*np.array([math.cos(theta),math.sin(theta)])))
    alpha=Image.new('L',(size,size))
    a=ImageDraw.Draw(alpha)
    a.polygon(vertices,fill=255)
    light=np.clip(.42+.002*(x-90)-.003*(y-100),0,.78)
    rolled=np.sin(yaw)*.12
    channels=np.stack([244+10*light+grain,175+64*(light+rolled)+grain,65+93*(light+rolled)+grain],axis=-1)
    paper=Image.fromarray(np.uint8(np.clip(channels,0,255))).convert('RGBA')
    paper.putalpha(alpha)
    lines=ImageDraw.Draw(paper)
    lines.line([vertices[0],vertices[4],vertices[8]],fill=(255,232,154,255),width=3)
    lines.ellipse((95,53,105,63),fill=(247,220,159,255))
    paper.resize((144,144),Image.Resampling.LANCZOS).save(d/f'{n:02}.png')
