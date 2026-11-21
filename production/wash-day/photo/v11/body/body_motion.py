"""Play registered full-body photographic exposures; no synthesized in-betweens."""
from functools import lru_cache
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parent
SCENES={2:"tap",3:"soap_fixed",4:"rub",5:"rinse",6:"face",7:"cheekpat",8:"prepare",
        9:"brush",10:"bow",11:"feet",12:"feet",13:"toescrub2",14:"towel",15:"dab",16:"settled"}
ALTERNATES={4:{"knuckles":"knuckles"},5:{"clean":"rinse"},6:{"scoop":"scoop_waist"},
            10:{"lower_brush":"downbrush","bow":"bow","wipe":"mouthwipe"},
            13:{"lowered":"lower"},14:{"offer":"towel"},15:{"settled":"settled"}}
ORDER={'knuckles':(0,1,2,3,2,1,2,3),'cheekpat':(0,1,2,4,5,6,7),'brush':(1,2,3,4,5,6,5,4,3,6,7)}
HI={'brush':'hi_brush','rub':'hi_rub','feet':'hi_feet','toescrub2':'hi_toescrub2','dab':'hi_dab'}
def nearest(x,cels):
    return cels[min(len(cels)-1,int(max(0.0,min(1.0,x))*len(cels)))]

def body_exposure(scene_i,u,local_seconds=None,*,setup='main'):
    u=max(0.0,min(1.0,u))
    if scene_i in (0,1): return ('greeting',round(u*11))
    if setup!='main':
        key=ALTERNATES[scene_i][setup]
    elif scene_i==10:
        if u < 37/130:
            key,u='downbrush',u*130/37
        elif u < 85/130:
            key,u='bow',(u*130-37)/48
        else:
            key,u='mouthwipe',(u*130-85)/45
    elif scene_i in (12,13):
        split=37/82
        if u<split:
            key,u=('feet' if scene_i==12 else 'toescrub2'),u/split
        else:
            key,u=('toescrub2' if scene_i==12 else 'lower'),(u-split)/(1-split)
    else:
        key=SCENES[scene_i]
    order=ORDER.get(key,range(8))
    return HI.get(key,key),nearest(u,order)

@lru_cache(maxsize=150)
def _cel(key,index,native):
    if key=='greeting':
        with Image.open(ROOT.parent/'greeting'/'greeting.webp') as master:
            x=(index%4)*512;y=(index//4)*512
            return master.crop((x,y,x+512,y+512)).convert('RGBA')
    p=ROOT/'frames'/key/f'{index:02}.png'
    original=ROOT/'native'/key/f'{index:02}.png'
    if native and original.exists() and key not in {'tap','rinse'}:
        with Image.open(original) as im:
            if im.width>=512: return im.convert('RGBA')
    with Image.open(p) as im: return im.convert('RGBA')

def body_at(scene_i,u,local_seconds=None,*,setup='main'):
    """Return the held 512×512 RGBA cel. Sole mark is (256,494)."""
    return _cel(*body_exposure(scene_i,u,local_seconds,setup=setup),False)

def body_native_at(scene_i,u,local_seconds=None,*,setup='main'):
    """Use the native photographic raster if denser. Anchor is (width/2,height*494/512)."""
    return _cel(*body_exposure(scene_i,u,local_seconds,setup=setup),True)
