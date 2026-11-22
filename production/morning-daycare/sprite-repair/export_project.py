"""Package the exact art used by the 2D edit and its exposure table."""
import argparse
from pathlib import Path
import csv
import json
from zipfile import ZipFile, ZIP_STORED, ZIP_DEFLATED
from film import Film, ROOT, best_sheet, clip

CAP=72*1024**2

def output_zip(dest, paths):
    with ZipFile(dest,'w') as z:
        for p in sorted(paths):
            kind=ZIP_STORED if p.suffix in {'.webp','.jpg','.png'} else ZIP_DEFLATED
            z.write(p,p.relative_to(ROOT),compress_type=kind)
    print(dest.name,dest.stat().st_size,flush=True)

def main():
    p=argparse.ArgumentParser()
    p.add_argument('destination',type=Path)
    p.add_argument('--edit-only',action='store_true')
    a=p.parse_args()
    out=a.destination.resolve()
    out.mkdir(parents=True,exist_ok=True)
    f=Film()
    r=ROOT/'exposures.csv'
    paths=set()
    actor_metrics={}
    used={}
    with r.open('w',newline='') as file:
        writer=csv.writer(file,lineterminator="\n")
        writer.writerow(('scene','first','last_exclusive','path_or_atlas','cell','exposure_frames','type'))
        prior=None
        first=0
        last=f.data['frames']
        for frame in range(last):
            scene,voice,take,cel=f.info(frame)
            if take.kind in {'clip','retime','still'}:
                c=clip(take.key)
                name=str(c.folder.relative_to(ROOT))
                if name not in used:
                    paths.add(c.folder/'index.json')
                    paths.update(c.folder/x for x in c.frames)
                    if c.record.get('plate'): paths.add(c.folder/c.record['plate'])
                    if c.record.get('plates'): paths.update(c.folder/x for x in c.record['plates'])
                    if 'overrides' in name:
                        paths.update(x for x in (c.folder/'sprites').glob('*') if x.is_file())
                        if (c.folder/'sprite-atlas.webp').is_file():paths.add(c.folder/'sprite-atlas.webp')
                        if (c.folder/'sprite-index.json').is_file():paths.add(c.folder/'sprite-index.json')
                used.setdefault(name,set()).add(cel)
            else:
                source=best_sheet(take.key)
                name=str(source.relative_to(ROOT))
                used.setdefault(name,set()).add(cel)
                paths.add(source)
            row=(scene['key'],name,cel,take.kind)
            if prior!=row:
                if prior is not None:
                    writer.writerow((prior[0],first,frame,prior[1],prior[2],frame-first,prior[3]))
                prior=row
                first=frame
        writer.writerow((prior[0],first,last,prior[1],prior[2],last-first,prior[3]))
    paths={x for x in paths if x.is_file()}
    essentials=['README.md','References.md','requirements.txt','film.py','edit.py','drawing.py','whole_render_tools.py','whole-scene.json',
                'extra-sheets.json','timeline.json','story.json','dialogue.json','lips.json','data.js','mix.wav',
                'Good_Morning_Yoonsu_English.srt','exposures.csv','verify_sprite.py','assemble_intermediates.py','stabilize_sheets.py',
                'overrides/dialogue/index.json']
    print('Asset bytes',sum(f.stat().st_size for f in paths),flush=True)
    output_zip(out/'Good_Morning_Yoonsu_2D_Edit.zip',
               [ROOT/name for name in essentials]+list((ROOT/'audio').glob('*.wav')))
    if a.edit_only:
        print('Replaced the edit archive and its exposure table',flush=True)
        return
    size=0
    group=[]
    idx=1
    for path in sorted(paths):
        bytesize=path.stat().st_size
        if size+bytesize>CAP and group:
            output_zip(out/f'Good_Morning_Yoonsu_2D_Sprites_{idx:02d}.zip',group)
            idx+=1
            size=0
            group=[]
        size+=bytesize
        group.append(path)
    if group:
        output_zip(out/f'Good_Morning_Yoonsu_2D_Sprites_{idx:02d}.zip',group)
    report={'output_frames':last,'unique_staged_exposures':sum(len(v) for v in used.values()),'sprite_part_count':idx,
            'selected_frames_by_source':{p:len(ids) for p,ids in sorted(used.items())}}
    (ROOT/'reviews/sprite-counts.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(report,flush=True)

if __name__=='__main__':
    main()
