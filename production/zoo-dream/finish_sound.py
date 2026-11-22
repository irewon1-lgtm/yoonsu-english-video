from pathlib import Path
import json,math,wave
import parselmouth as pm
from parselmouth.praat import call
from scipy.io import wavfile
import numpy as np
p=Path('script.json');doc=json.loads(p.read_text())
# A short, original call-and-response tune in C. Keep consonants unpitched.
motifs=[[60,64,67,67],[64,65,67,69,67],[67,69,67,65,64,62],[64,65,67,64,62,60],[67,64,60]]
for s in doc['scenes']:
 if s['id'] in ('music','encore'):
  lines=s['lines'][2:] if s['id']=='music' else s['lines'][1:]
  for j,e in enumerate(lines):
   if e['role']=='sheriff':continue  # Spoken handoff at the end of the encore.
   path=Path('audio')/(e['id']+'.wav')
   snd=pm.Sound(str(path));man=call(snd,'To Manipulation',.01,80,600)
   tier=call(man,'Extract pitch tier')
   call(tier,'Remove points between',0,snd.duration)
   notes=motifs[j];step=snd.duration/len(notes)
   for k,m in enumerate(notes):
    hz=440*2**((m-69)/12)
    call(tier,'Add point',step*(k+.1),hz)
    call(tier,'Add point',step*(k+.84),hz*1.006)
   call([tier,man],'Replace pitch tier')
   data=call(man,'Get resynthesis (overlap-add)').values[0]
   data*=min(1.,.78/max(abs(data)))
   wavfile.write(path,24000,(data*32767).astype('int16'))
 for e in s['lines']:
  if e['role']!='pause' and not Path('audio',e['id']+'.wav').is_file():raise FileNotFoundError(e)
 total=0
 for e in s['lines']:
  if e['role']=='pause':total+=96
  else:
   with wave.open('audio/'+e['id']+'.wav') as w:total+=math.ceil(w.getnframes()/1000)
 overhead={'hands_up':151,'clap':128}.get(s['id'],85 if s['view']=='practice' else 98)
 s['seconds']=math.ceil((total+overhead)/24)
p.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+'\n')
