import json,subprocess
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
R=Path(__file__).resolve().parent
BASE=Path('/dev/shm/album-release-20')
OUT=BASE/'stream-shots'
D=json.loads((R/'timeline.json').read_text())
def encode(i):
 s=D['scenes'][i-1]
 release=(s['events'][4]['end']-s['at'])/24
 args=['ffmpeg','-y','-xerror','-v','error','-threads','2','-i',str(R/'qa'/f'{i:02}.mp4'),'-an','-c:v','libx264','-threads','3','-preset','medium','-b:v','1080k','-g','288','-force_key_frames',f'{release:.6f}','-passlogfile',str(OUT/f'log-{i}')]
 dest=OUT/f'{i:02}.mp4'
 subprocess.run(args+['-pass','1','-f','null','-'],check=True)
 subprocess.run(args+['-pass','2',str(dest)],check=True)
 print(i,flush=True)
if __name__=='__main__':
 OUT.mkdir(exist_ok=True)
 with ProcessPoolExecutor(4) as pool:list(pool.map(encode,range(1,37)))
 order=OUT/'list.txt';order.write_text(''.join(f"file '{i:02}.mp4'\n" for i in range(1,37)))
 target=BASE/'media/playground/film.mp4';temp=target.with_name('incoming.mp4')
 subprocess.run(['ffmpeg','-y','-xerror','-v','error','-f','concat','-safe','0','-i',str(order),'-i',str(R/'delivery/Playground_Pals_1080p.mp4'),'-map','0:v:0','-map','1:a:0','-c','copy','-movflags','+faststart',str(temp)],check=True)
 temp.replace(target)
