"""Compare every displayed master frame with the drawing prescribed by its exposure."""
import subprocess,csv,io,json
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from PIL import Image
import film
R=Path(__file__).resolve().parent
def compare(i):
 s=film.SC[i-1];rows=[]
 args=['ffmpeg','-v','error','-threads','2','-ss',f"{s['at']/24:.8f}",'-i',str(R/'delivery/Playground_Pals_1080p.mp4'),'-frames:v',str(s['end']-s['at']),'-vf','scale=256:144:flags=area','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-']
 with subprocess.Popen(args,stdout=subprocess.PIPE) as proc:
  for n in range(s['at'],s['end']):
   raw=proc.stdout.read(256*144*3);assert len(raw)==256*144*3,(i,n)
   dec=np.frombuffer(raw,np.uint8).reshape(144,256,3)
   ref=np.asarray(film.frame(i,n).resize((256,144),Image.Resampling.BOX))
   delta=np.abs(dec.astype('int16')-ref)
   mae=float(delta.mean());p99=float(np.percentile(delta,99))
   rows.append((n,i,n-s['at'],round(mae,3),p99))
   assert mae<8 and p99<45,(i,n,mae,p99)
  assert proc.wait()==0
 return rows
if __name__=='__main__':
 with ProcessPoolExecutor(4) as p:rows=[row for group in p.map(compare,range(1,37)) for row in group]
 assert [r[0] for r in rows]==list(range(film.D['frames']))
 out=R/'qa/frame-audit'
 with (out/'decoded-frames.csv').open('w') as f:
  w=csv.writer(f);w.writerow(('master_frame','shot','local_frame','rgb_MAE_at_256x144','p99_channel_error'));w.writerows(rows)
 print('Decoded frames',len(rows),'worst mean absolute channel error',max(r[3] for r in rows),flush=True)
