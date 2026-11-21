from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageFilter
ROOT=Path(__file__).resolve().parent
@lru_cache(8)
def sheet(key):
    with Image.open(ROOT/(key+'.webp')) as im:return im.convert('RGBA')
@lru_cache(60)
def photo_cel(key,n):
    x=n%2*768;y=n//2*432
    return sheet(key).crop((x,y,x+768,y+432))
@lru_cache(3)
def background(place):
    photo=ROOT.parents[1]
    path=photo/('footbath.png' if place=='feet' else 'bath.png')
    with Image.open(path) as im:
        # Locked perspective of the room viewed from the actor's facing lens.
        src=im.convert('RGB')
        return src.crop((int(.08*src.width),int(.09*src.height),int(.81*src.width),int(.82*src.height))).resize((768,432),Image.Resampling.LANCZOS).filter(ImageFilter.GaussianBlur(4.0))
def on_set(cel,place):
    plate=background(place).copy()
    plate.paste(cel,(0,0),cel)
    return plate
