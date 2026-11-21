"""Sample a sequence of rendered transparent action cels over its locked camera plate."""
from functools import lru_cache
from pathlib import Path
import json
from PIL import Image
ROOT=Path(__file__).parent
EXPOSURES=49
NATIVE=(1152,648)
@lru_cache(3)
def _sheet(key,block,dirname):
    with Image.open(ROOT/'sheets'/dirname/f'{block:02d}.webp') as file:
        return file.convert('RGBA')
@lru_cache(7)
def _plate(key):
    with Image.open(ROOT/'plates'/f'{key}.png') as file:
        return file.convert('RGBA')
@lru_cache(7)
def atlas_spec(key):
    config=ROOT/'sheets'/f'{key}.json'
    if config.exists():
        spec=json.loads(config.read_text());return spec['exposures'],spec['folder']
    return EXPOSURES,key
def actor_at(key,u):
    exposures,dirname=atlas_spec(key)
    i=int(max(0,min(1,float(u)))*(exposures-1)+.5)
    b,j=divmod(i,8);w,h=NATIVE;x=j%4*w;y=j//4*h
    return _sheet(key,b,dirname).crop((x,y,x+w,y+h))
def insert_at(key,u):
    fg=actor_at(key,u).resize((768,432),Image.Resampling.LANCZOS)
    return Image.alpha_composite(_plate(key),fg).convert('RGB')

@lru_cache(7)
def plate_at(key):
    """Clean locked-camera RGB set at the native 1152×648 cel resolution."""
    with Image.open(ROOT/'plates_hd'/f'{key}.png') as file:
        return file.convert('RGB')
def native_at(key,u):
    return Image.alpha_composite(plate_at(key).convert('RGBA'),actor_at(key,u)).convert('RGB')
