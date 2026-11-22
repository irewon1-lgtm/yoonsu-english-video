"""Lossless scene sprites, registered canvas origins, and per-scene exposure ledger."""
from pathlib import Path
from zipfile import ZipFile,ZIP_STORED,ZIP_DEFLATED
from PIL import Image
import argparse,csv,json,hashlib
from exposures import action,ROOT
from film import Film,GATE

def write_atlases(key,out):
    clip=action(key)
    sub=out/key
    sub.mkdir(parents=True,exist_ok=True)
    index=[]
    atlas=None
    cell_w=cell_h=1024
    ncol,nrow=3,2
    capacity=ncol*nrow
    digest=set()
    t=0
    for i,(src,hold) in enumerate(zip(clip.files,clip.holds)):
        path=clip.directory/src
        with Image.open(path) as im:
            im=im.convert('RGBA')
        original=im.size
        alpha=im.getchannel('A')
        bbox=alpha.getbbox()
        assert bbox,src
        trimmed=im.crop(bbox)
        # Preserve native cel bits, even when a full-camera frame needs a wider box.
        page,j=divmod(i,capacity)
        if j==0:
            cell_w=max(1024,original[0])+12
            cell_h=max(1024,original[1])+12
            atlas=Image.new('RGBA',(ncol*cell_w,nrow*cell_h))
        x=6+j%ncol*cell_w
        y=6+j//ncol*cell_h
        atlas.paste(trimmed,(x,y))
        image_sha=hashlib.sha256(trimmed.tobytes()).hexdigest()
        digest.add(image_sha)
        contacts=clip.record.get('contacts',[])
        if isinstance(contacts,list):
            related=[c for c in contacts if isinstance(c,dict) and _related_to(c,t,t+hold)]
        else:
            related=contacts
        index.append(dict(
            cel_id=f'{key}:{i:03d}',atlas=f'page-{page:03d}.webp',
            artwork=str(Path('actions',key,src)),source_size=clip.record.get('source_size'),
            canvas_size=list(original),sprite_rect=[x,y,trimmed.width,trimmed.height],
            trim_offset=list(bbox[:2]),pivot=clip.record.get('pivot',[0,0]),
            local_frame_start=t,exposure_frames=hold,view=clip.record.get('view'),
            costume=clip.record.get('costume'),layer_order=clip.record.get('layer_order',[]),
            contacts=related,sha256_rgba=image_sha))
        t+=hold
        if j+1==capacity or i+1==len(clip.files):
            atlas.save(sub/f'page-{page:03d}.webp',lossless=True,method=1,exact=True)
    (sub/'index.json').write_text(json.dumps(dict(clip=key,frames=index,unique_rasters=len(digest),slot=[cell_w,cell_h]),ensure_ascii=False,indent=2)+'\n')
    return index

def _related_to(mark,start,last):
    n=mark.get('frame',mark.get('at'))
    return isinstance(n,int) and start<=n<last

def build(only_gate=False):
    out=ROOT/('gate-sheets' if only_gate else 'sheets')
    f=Film()
    key_to_scene={s['key']:i for i,s in enumerate(f.scenes)}
    if not only_gate and (ROOT/'actions/wake_stretch/index.json').exists():
        key_to_scene['wake_stretch']=key_to_scene['wake']
    if not only_gate and (ROOT/'actions/shoes_prepare/index.json').exists():
        key_to_scene['shoes_prepare']=key_to_scene['shoes']
    keys=GATE if only_gate else key_to_scene
    stats={}
    with (ROOT/('gate-exposure.csv' if only_gate else 'exposure.csv')).open('w') as table:
        fields=('scene','absolute_first','absolute_last_exclusive','cel_id','source_size','sprite_rect','trim_offset','pivot','exposure_frames','view','costume','contacts','layer_order')
        writer=csv.DictWriter(table,fieldnames=fields)
        writer.writeheader()
        gate_offset=0
        for key in keys:
            records=write_atlases(key,out)
            scene_i=key_to_scene[key]
            first=gate_offset if only_gate else next(z.first for z in f.shots(scene_i) if z.kind=='act' and z.key==key)
            for p in records:
                row={k:p[k] for k in fields if k in p}
                n=first+p['local_frame_start']
                row.update(scene=key,absolute_first=n,absolute_last_exclusive=n+p['exposure_frames'])
                writer.writerow(row)
            hashed={r['sha256_rgba'] for r in records}
            stats[key]=dict(unique_registered_rasters=len(hashed),authored_source=action(key).record.get('source'),native_size=action(key).record.get('source_size'))
            gate_offset+=action(key).duration
    (out/'summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--gate',action='store_true')
    build(p.parse_args().gate)
