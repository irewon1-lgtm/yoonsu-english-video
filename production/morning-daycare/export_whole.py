"""Save production artwork and the exact selections made by the rendered edit."""
from pathlib import Path
import argparse
import csv
import json
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from film_whole import ASSETS, ROOT, WholeFilm, catalog, cel_image


def write_exposures(film, directory):
    path=directory/'whole_exposures.csv'
    scenes={}
    previous=None
    active={}
    with path.open('w',newline='') as stream:
        fields=('scene','first','last_exclusive','sheet','cell','mode','role')
        writer=csv.writer(stream)
        writer.writerow(fields)
        for frame in range(film.edit['frames']):
            sc,line,span,cell=film.source_at(frame)
            state=(sc['key'],span.sheet,cell,span.mode,line['role'] if line else '')
            active.setdefault(span.sheet,set()).add(cell)
            scenes.setdefault(sc['key'],set()).add((span.sheet,cell))
            if state==previous:
                continue
            if previous is not None:
                writer.writerow((previous[0],first,frame,*previous[1:]))
            previous,first=state,frame
        writer.writerow((previous[0],first,film.edit['frames'],*previous[1:]))
    return path,active,{k:len(v) for k,v in scenes.items()}


def archive(path, contents):
    with ZipFile(path,'w') as bundle:
        for file,name in contents:
            method=ZIP_STORED if file.suffix.lower()=='.png' else ZIP_DEFLATED
            bundle.write(file,name,compress_type=method)
    print(path.name,path.stat().st_size,flush=True)


def sprite_archives(dir, active, ledger):
    limits=88*1024**2
    parts=[]; block=[]; size=0
    for key in sorted(active):
        setup=catalog()['sheets'][key]
        file=ASSETS/setup['file']
        if size+file.stat().st_size>=limits and block:
            parts.append(block)
            block=[];size=0
        block.append((file,f'assets/whole-scene/{file.name}'))
        size+=file.stat().st_size
    if block:parts.append(block)
    for i,items in enumerate(parts,1):
        number='' if i==1 else f'_{i:02d}'
        archive(dir/f'Good_Morning_Yoonsu_Whole_Sprites{number}.zip',
                items+[(ROOT/'whole-scene.json','whole-scene.json'),(ledger,ledger.name)])
    frames=dir/'.whole_cels'
    frames.mkdir(exist_ok=True)
    for key, indices in active.items():
        sub=frames/key
        sub.mkdir(exist_ok=True)
        for index in indices:
            image=cel_image(key,index)
            file=sub/f'{index+1:02d}.webp'
            image.save(file,lossless=True,method=1)
    ordered=[]
    block=[];size=0
    for file in sorted(frames.glob('*/*.webp')):
        if size+file.stat().st_size>=limits and block:
            ordered.append(block);block=[];size=0
        block.append((file,'cels/'+str(file.relative_to(frames))))
        size+=file.stat().st_size
    if block:ordered.append(block)
    for i,items in enumerate(ordered,1):
        number='' if i==1 else f'_{i:02d}'
        archive(dir/f'Good_Morning_Yoonsu_Whole_Cels{number}.zip',items+[(ledger,ledger.name)])


def main():
    p=argparse.ArgumentParser()
    p.add_argument('destination',type=Path)
    args=p.parse_args()
    dest=args.destination
    dest.mkdir(parents=True,exist_ok=True)
    film=WholeFilm()
    ledger,active,counts=write_exposures(film,dest)
    needed=('film_whole.py','whole_render_tools.py','drawing.py','export_whole.py',
            'timeline.json','whole-scene.json','dialogue.json','lips.json','story.json',
            'mix.wav','Good_Morning_Yoonsu_English.srt','data.js','README_Whole.md')
    items=[(ROOT/name,name) for name in needed]
    items.extend((file,str(file.relative_to(ROOT))) for file in sorted((ROOT/'audio').glob('*.wav')))
    archive(dest/'Good_Morning_Yoonsu_Whole_Edit.zip',items+[(ledger,ledger.name)])
    sprite_archives(dest,active,ledger)
    stats={'scenes':len(counts),'timeline_frames':film.edit['frames'],
           'selected_sheets':len(active),'distinct_tiles':sum(map(len,active.values())),
           'tiles_per_scene':counts}
    (dest/'sprite_counts.json').write_text(json.dumps(stats,indent=2)+'\n')
    print(stats,flush=True)


if __name__=='__main__':
    main()
