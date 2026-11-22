"""Integer-frame English dialogue, starting cues, exact four-second response windows."""
import argparse
import json
from math import ceil
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import butter, resample_poly, sosfilt

ROOT = Path(__file__).resolve().parent
FPS = 24
RATE = 48000
SAMPLES = RATE // FPS
STARTS = {
    'arrival': 32, 'families': 22, 'hands_up': 54, 'introduce': 20,
    'practice_one': 17, 'practice_two': 17, 'practice_three': 17, 'practice_four': 17,
}
MARGINS = {'hands_up': 24, 'introduce': 19, 'clap': 22, 'goodbye': 32}
AMPLITUDE = {'y': .91, 'teacher': .88, 'mom': .94, 'sheriff': .89, 'friend': .92}

def take(id):
    rate, pcm = wavfile.read(ROOT/'audio'/f'{id}.wav')
    assert rate == 24000 and pcm.ndim == 1 and pcm.dtype == np.int16, (id,rate,pcm.shape)
    return resample_poly(pcm / 32768., 2, 1).astype('float32')

def clap():
    # Three quiet hand contacts can be heard only in the story's applause break.
    t = np.arange(int(.155*RATE)) / RATE
    rng = np.random.default_rng(1403)
    air = sosfilt(butter(2,[310,5500],fs=RATE,btype='bandpass',output='sos'),rng.normal(size=len(t)))
    hand = .45*air+.1*np.sin(2*np.pi*425*t)
    return .21*hand*np.minimum(t/.002,1)*(np.exp(-t/.018)+.25*np.exp(-t/.042))

def timestamps(n):
    ms=round(n*1000/FPS)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def build():
    script=json.loads((ROOT/'script.json').read_text())
    voices={line['id']:take(line['id']) for scene in script['scenes'] for line in scene['lines'] if line['role'] != 'pause'}
    lengths={id:ceil(len(v)/SAMPLES) for id,v in voices.items()}
    frames=sum(sc['seconds']*FPS for sc in script['scenes'])
    mix=np.zeros(frames*SAMPLES,dtype='float32')
    fired_at=[]
    sections=[]
    start=0
    for scene in script['scenes']:
        id=scene['id']
        scene_length=scene['seconds']*FPS
        event_lengths=[96 if d['role']=='pause' else lengths[d['id']] for d in scene['lines']]
        practice=any(d['role']=='pause' for d in scene['lines'])
        gaps=[9]*(len(scene['lines'])-1)
        if practice:
            gaps=[12,8,9,6]
        elif id=='clap':
            gaps=[43,13,13]
        elif id=='introduce':
            gaps=[11,16,12,13]
        elif id=='hands_up':
            gaps=[14,16,14]
        lead=STARTS.get(id,19)
        tail=MARGINS.get(id,23)
        free=scene_length-sum(event_lengths)-sum(gaps)-lead-tail
        # In a packed scene only optional acting pauses shrink.
        if free<0:
            for i in range(len(gaps)-1,-1,-1):
                if id=='clap' and i==0: continue
                delta=min(gaps[i]-4,-free)
                gaps[i]-=delta; free+=delta
        if free<0:
            tail+=free
            free=0
        assert tail>=7,(id,tail)
        if not practice and id!='clap':
            added=min(17,free//len(gaps)) if gaps else 0
            gaps=[s+added for s in gaps]
        pos=start+lead
        lines=[]
        noises=[]
        for i,(row,duration) in enumerate(zip(scene['lines'],event_lengths,strict=True)):
            end=pos+duration
            lines.append({**row,'at':pos,'end':end})
            if row['role']!='pause':
                samples=voices[row['id']]*AMPLITUDE[row['role']]
                at=pos*SAMPLES
                assert not mix[at:at+len(samples)].any(),row['id']
                mix[at:at+len(samples)]=samples
                if id=='clap' and i==0:
                    noises.extend(end+n for n in (11,23,35))
            if i<len(gaps):
                pos=end+gaps[i]
            else:
                pos=end
        assert pos<=start+scene_length-6,(id,pos,start,scene_length)
        sound=clap()
        for n in noises:
            at=n*SAMPLES
            assert not mix[at:at+len(sound)].any()
            mix[at:at+len(sound)] = sound
        sections.append({**scene,'at':start,'end':start+scene_length,'events':lines,'claps':noises})
        for l in lines:
            a,b=l['at'],l['end']
            if l['role']=='pause':
                assert b-a==4*FPS and not mix[a*SAMPLES:b*SAMPLES].any()
            else:
                fired_at.append(l)
        start+=scene_length

    edit={key:script[key] for key in ('title','en','fps')}
    edit.update(frames=frames,scenes=sections)
    (ROOT/'timeline.json').write_text(json.dumps(edit,ensure_ascii=False,indent=2)+'\n')
    wavfile.write(ROOT/'mix.wav',RATE,(mix*32767.).astype(np.int16))
    srt='\n\n'.join(f"{n}\n{timestamps(d['at'])} --> {timestamps(d['end'])}\n{d['en']}" for n,d in enumerate(fired_at,1))
    (ROOT/'Yoonsu_Dream_English.srt').write_text(srt+'\n')
    assert np.max(np.abs(mix))<.98
    for scene in sections:
        print(scene['id'],scene['end']-scene['at'],[(e['id'],e['at']-scene['at'],e['end']-scene['at']) for e in scene['events']],scene['claps'])
    print(frames,len(fired_at),'speech cues, four-second response windows, peak',round(float(np.max(np.abs(mix))),3))

if __name__=='__main__':
    build()
