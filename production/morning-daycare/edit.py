"""Integer-frame edit based on the reference Wash Day lesson layout."""
from pathlib import Path
from math import ceil, gcd
import json
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent
FPS = 24
SR = 48000
SAMPLES_PER_FRAME = SR // FPS
TITLE = "좋은 아침, 어린이집 가자!"

def load_take(stem):
    rate,samples = wavfile.read(ROOT/'audio'/f'{stem}.wav')
    assert samples.ndim==1 and samples.dtype==np.int16, (stem,rate,samples.shape,samples.dtype)
    exact=rate==SR
    audio=samples.astype(np.float64)/32768
    factor=gcd(rate,SR)
    return audio if exact else resample_poly(audio,SR//factor,rate//factor)

def timestamp(frame):
    ms = round(frame*1000/FPS)
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"

def build():
    story=json.loads((ROOT/'story.json').read_text())
    script={d['id']:d for d in json.loads((ROOT/'dialogue.json').read_text())}
    lips=json.loads((ROOT/'lips.json').read_text())
    takes={stem: load_take(stem) for stem in [*script,'cue']}
    length={stem:ceil(len(take)/SAMPLES_PER_FRAME) for stem,take in takes.items()}
    full=sum(s['seconds'] for s in story)*FPS
    assert len(story)==15 and 220*FPS<=full<=240*FPS
    mix=np.zeros(full*SAMPLES_PER_FRAME,dtype=np.float64)
    scenes,phrases,guide=[],[],[]
    cursor=0

    def add(stem,role,line,kind,start):
        finish=start+length[stem]
        pos=start*SAMPLES_PER_FRAME
        samples=takes[stem]
        assert not np.any(mix[pos:pos+len(samples)])
        mix[pos:pos+len(samples)]=samples
        shapes=lips[stem] if isinstance(lips[stem],list) else lips[stem]['mouthCues']
        phrases.append(dict(wav=stem,role=role,line=line,kind=kind,start=start,end=finish,shapes=shapes))
        return finish

    for index,source in enumerate(story,1):
        end=cursor+source['seconds']*FPS
        stem=source['line']
        row=script[stem]
        start=cursor+round(source['leadSecond']*FPS)
        lead=add(stem,row['role'],row['line'],'lead',start)
        turn=None
        cue_start=repeat_start=None
        if source.get('target'):
            cue_start=lead+10
            cue_end=add('cue','S','Yoonsu, your turn!','cue',cue_start)
            repeat_start=cue_end+10
            stop=add(stem,row['role'],row['line'],'repeat',repeat_start)+7
            turn=[stop,stop+72,row['line']]
            assert turn[1]+9<=end,(stem,turn,end)
            guide.append((turn,repeat_start))
        assert lead+12<=end
        scenes.append(dict(source,i=index,start=cursor,end=end,turn=turn,lead=start,cue=cue_start,repeat=repeat_start))
        cursor=end
    assert cursor==full and len(guide)==12 and abs(mix).max() < .95
    seconds=lambda n:round(n/FPS,6)
    ep=dict(id='morning-daycare',title=TITLE,
            turns=[[seconds(a),seconds(b),line] for (a,b,line),_ in guide],
            repeatStarts=[seconds(n) for _,n in guide],hints={})
    data=dict(fps=FPS,frames=full,scenes=scenes,dialogue=phrases,episode=ep)
    (ROOT/'timeline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data.js').write_text('const episode = '+json.dumps(ep,ensure_ascii=False,indent=2)+';\n')
    lines=[(d['start'],d['end'],d['line']) for d in phrases]
    lines.extend((a,b,line) for (a,b,line),_ in guide)
    text='\n\n'.join(f"{i+1}\n{timestamp(a)} --> {timestamp(b)}\n{line}"
                      for i,(a,b,line) in enumerate(sorted(lines)))
    (ROOT/'Good_Morning_Yoonsu_English.srt').write_text(text+'\n')
    wavfile.write(ROOT/'mix.wav',SR,np.rint(mix*32767).astype(np.int16))
    print(len(phrases),'recorded events;',len(guide),'response windows;',full/FPS,'seconds; peak',float(abs(mix).max()))

if __name__=='__main__':
    build()
