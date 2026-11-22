"""Assemble the continuous edition from its integer-frame story and mono WAVs."""

from math import ceil, gcd
from pathlib import Path
import json

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent
FPS = 24
SR = 48000
SAMPLES_PER_FRAME = SR // FPS
TITLE = '좋은 아침, 어린이집 가자!'


def take(stem):
    rate, pcm = wavfile.read(ROOT/'audio'/f'{stem}.wav')
    assert pcm.ndim == 1 and pcm.dtype == np.int16, (stem, rate, pcm.shape, pcm.dtype)
    divisor = gcd(rate, SR)
    return resample_poly(pcm.astype(np.float64)/32768, SR//divisor, rate//divisor)


def timestamp(frame):
    ms = round(frame*1000/FPS)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'


def build():
    story = json.loads((ROOT/'story.json').read_text())
    lines = json.loads((ROOT/'dialogue.json').read_text())
    script = {r['id']: r for r in lines}
    script['cue'] = dict(role='S', line='Yoonsu, your turn!')
    lips = json.loads((ROOT/'lips.json').read_text())
    assert set(lips) == set(script) and len(lines) == 28
    takes = {stem: take(stem) for stem in script}
    lengths = {stem: ceil(len(wav)/SAMPLES_PER_FRAME) for stem,wav in takes.items()}
    total_frames = sum(round(scene['seconds']*FPS) for scene in story)
    assert len(story) == 15 and total_frames == 207*FPS
    mix = np.zeros(total_frames*SAMPLES_PER_FRAME, dtype=np.int16)
    scenes, dialogue, turns, repeats, captions = [], [], [], [], []
    first = 0
    for index, source in enumerate(story,1):
        last = first + round(source['seconds']*FPS)
        stem = source['line']
        line = script[stem]['line']
        lead = first + round(source['leadSecond']*FPS)
        cue = lead + lengths[stem] + 10
        repeat = cue + lengths['cue'] + 10
        start_wait = repeat + lengths[stem] + 7
        stop_wait = start_wait + 72
        assert source['target'] and stop_wait+7 <= last, (source['key'],stop_wait,last)
        turn = [start_wait,stop_wait,line]
        events = [(stem,'lead',lead), ('cue','cue',cue), (stem,'repeat',repeat)]
        extras = []
        for extra in source['extra']:
            wav = extra['wav']
            if 'localSecond' in extra:
                start = first + round(extra['localSecond']*FPS)
            else:
                start = stop_wait + extra['afterTurnFrames']
            events.append((wav,'story',start))
            extras.append(dict(wav=wav,start=start,end=start+lengths[wav]))
        prior_end = first
        for wav,kind,start in sorted(events,key=lambda event:event[2]):
            end = start + lengths[wav]
            assert prior_end <= start < end <= last, (source['key'],kind,wav,prior_end,start,end,last)
            assert end <= start_wait or start >= stop_wait, (source['key'],wav,turn)
            first_sample = start*SAMPLES_PER_FRAME
            samples = np.rint(takes[wav]*32768)
            assert np.max(np.abs(samples)) < .95*32768, wav
            mix[first_sample:first_sample+len(samples)] = samples.astype(np.int16)
            shapes = lips[wav]
            dialogue.append(dict(wav=wav,role=script[wav]['role'],line=script[wav]['line'],
                                 kind=kind,start=start,end=end,shapes=shapes))
            captions.append((start,end,script[wav]['line']))
            prior_end = end
        scenes.append(dict(source,i=index,start=first,end=last,turn=turn,lead=lead,cue=cue,
                           repeat=repeat,story=extras))
        captions.append(tuple(turn))
        turns.append(turn)
        repeats.append(repeat)
        first = last
    assert first == total_frames and len(turns) == 15 and len(dialogue) == 58
    seconds = lambda n: round(n/FPS,6)
    episode = dict(id='morning-daycare',title=TITLE,
                   turns=[[seconds(a),seconds(b),line] for a,b,line in turns],
                   repeatStarts=[seconds(n) for n in repeats],hints={})
    data = dict(fps=FPS,frames=total_frames,scenes=scenes,dialogue=dialogue,episode=episode)
    (ROOT/'timeline.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    (ROOT/'data.js').write_text('const episode = '+json.dumps(episode,ensure_ascii=False,indent=2)+';\n')
    text = '\n\n'.join(f'{i}\n{timestamp(a)} --> {timestamp(b)}\n{line}'
                       for i,(a,b,line) in enumerate(sorted(captions),1))
    (ROOT/'Good_Morning_Yoonsu_English.srt').write_text(text+'\n')
    wavfile.write(ROOT/'mix.wav',SR,mix)
    print(total_frames,'frames, 58 dialogue events, 15 three-second response windows; peak',
          np.max(np.abs(mix.astype(np.int32)))/32768)
    for scene in scenes:
        print(scene['key'], scene['start'], scene['end'], scene['lead'], scene['turn'][:2],
              [(audio['wav'],audio['start'],audio['end']) for audio in scene['story']])


if __name__ == '__main__':
    build()
