"""Build the home episode using the Wash Day 24fps model → cue → repeat edit."""
import json
from pathlib import Path
import re
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent
FPS, SR = 24, 48000
TITLE = "윤수 방의 작은 별"
DURATION = 144
OPENING, ENDING = 78, 76

def load(stem):
    rate, pcm = wavfile.read(ROOT / 'audio' / (stem + '.wav'))
    assert pcm.ndim == 1 and pcm.dtype == np.int16, stem
    assert rate in (24000, SR), (stem, rate)
    wave = pcm.astype(np.float64) / 32768
    return resample_poly(wave, 2, 1) if rate == 24000 else wave

def stamp(frame):
    ms = round(frame * 1000 / FPS)
    return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"

def build():
    script = json.loads((ROOT / 'story.json').read_text())
    lips = json.loads((ROOT / 'lips.json').read_text())
    ids = [f"{i:02d}" for i in range(len(script))]
    waves = {stem: load(stem) for stem in [*ids, 'cue']}
    step = SR // FPS
    lengths = {stem: (len(wave) + step - 1)//step for stem,wave in waves.items()}
    decisions = [row.get('target', False) for row in script]
    assert sum(decisions) == 12
    for row, target in zip(script,decisions):
        if target:
            words = re.findall(r"[A-Za-z]+(?:'[a-z]+)?", row['line'])
            assert 2 <= len(words) <= 3, row['line']
    full = FPS * DURATION
    spans = [48 + (2*lengths[stem]+lengths['cue']+72+31 if yes else lengths[stem])
             for stem,yes in zip(ids,decisions)]
    spans[0] += 48
    leftover = full - OPENING - ENDING - sum(spans)
    assert leftover >= 0, leftover
    weights = np.array([1.15 if yes else .78 for yes in decisions])
    extra = np.diff(np.r_[0,np.rint(weights.cumsum()*leftover/weights.sum())]).astype(int)
    mix = np.zeros(full*step, dtype=np.float64)
    scenes, clips, turns, repeats = [], [], [], []
    cursor = OPENING

    def clip(stem, role, line, kind, start):
        end = start+lengths[stem]
        at = start*step
        take = waves[stem]
        assert not np.any(mix[at:at+len(take)])
        mix[at:at+len(take)] = take
        cue_data = lips[stem]
        clips.append(dict(wav=stem, role=role, line=line, kind=kind, start=start, end=end,
                          shapes=cue_data if isinstance(cue_data,list) else cue_data['mouthCues']))
        return end

    for i,(row,stem,more,span) in enumerate(zip(script,ids,extra,spans)):
        end = cursor+span+more
        scenes.append(dict(i=i, start=int(cursor),end=int(end), **row))
        initial = int(cursor+(70 if i==0 else 23+round(more*.45)))
        if i==9:
            initial += 8  # show the end of the point before the cloud line
        finish = clip(stem,row['role'],row['line'],'lead',initial)
        if row.get('target'):
            cue_end = clip('cue','S','Yoonsu, your turn!','cue',finish+12)
            repeat = cue_end+12
            stop = clip(stem,row['role'],row['line'],'repeat',repeat)+7
            turns.append([round(stop/FPS,6),round((stop+72)/FPS,6),row['line']])
            repeats.append(round(repeat/FPS,6))
        cursor = end
    assert int(cursor) + ENDING == full and abs(mix).max() < .93
    wavfile.write(ROOT/'mix.wav',SR,np.rint(mix*32767).astype(np.int16))
    norm = lambda n: int(n) if isinstance(n,np.integer) else n
    episode = dict(id='small-star',title=TITLE,turns=turns,repeatStarts=repeats,hints={})
    data = dict(fps=FPS,frames=full,opening=OPENING,ending=ENDING,scenes=scenes,dialogue=clips,episode=episode)
    (ROOT/'timeline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2,default=norm)+'\n')
    (ROOT/'English.srt').write_text('\n\n'.join(
        f"{i+1}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['line']}" for i,s in enumerate(clips))+'\n')
    print(len(clips), 'performances,',len(turns),'turns,',full/FPS,'seconds')

if __name__ == '__main__':
    build()
