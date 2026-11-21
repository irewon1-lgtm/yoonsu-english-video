"""Build 1024-square transparent display cels from each approved exposure once."""
from functools import lru_cache
from pathlib import Path
from PIL import Image
import hashlib,json,sys
from .scale import display_master
from ..body.body_motion import _cel
HERE=Path(__file__).resolve().parent
DEST=HERE/'atlases'
def build(key):
    DEST.mkdir(exist_ok=True)
    count=12 if key=='greeting' else 8
    raw=[_cel(key,i,True) for i in range(count)]
    sha=hashlib.sha256(b''.join(im.tobytes() for im in raw)).hexdigest()
    out=DEST/(key+'.webp'); rec=DEST/(key+'.json')
    if out.exists() and rec.exists() and json.loads(rec.read_text())['source_sha256']==sha:return
    atlas=Image.new('RGBA',(4096,((count+3)//4)*1024))
    for n,src in enumerate(raw):
        res=display_master(src)
        if res.size!=(1024,1024):res=res.resize((1024,1024),Image.Resampling.LANCZOS)
        atlas.paste(res,(n%4*1024,n//4*1024))
    tmp=out.with_suffix('.tmp.webp')
    atlas.save(tmp,lossless=True,quality=40,method=1,exact=True)
    tmp.replace(out)
    rec.write_text(json.dumps(dict(grid=[4,(count+3)//4],tile=[1024,1024],anchor=[512,988],native_working_cell=raw[0].size,source_sha256=sha)))
    print(key,count,raw[0].size,out.stat().st_size,flush=True)
@lru_cache(3)
def atlas(key):
    with Image.open(DEST/(key+'.webp')) as im:return im.convert('RGBA')
@lru_cache(48)
def at(key,index):
    x=index%4*1024;y=index//4*1024
    return atlas(key).crop((x,y,x+1024,y+1024))
if __name__=='__main__':
    for key in sys.argv[1:]:build(key)
