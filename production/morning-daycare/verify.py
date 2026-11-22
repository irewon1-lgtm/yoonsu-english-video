"""Verify synchronized readable output; visual acting assessment is kept separate."""
import sys,subprocess,json
from pathlib import Path
import numpy as np
from scipy.io import wavfile
from edit import SR,FPS,ROOT,load_take

def probe(file):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(file)]))

def verify_media(file,expected,with_audio=False):
    r=probe(file)
    video=r['streams'][0]
    assert (video['codec_name'],video['width'],video['height'],video['avg_frame_rate'],video['r_frame_rate'],int(video['nb_frames']))==(
        'h264',1920,1080,'24/1','24/1',expected)
    assert abs(float(r['format']['duration'])-expected/FPS)<.05
    if with_audio:
        a=r['streams'][1]
        assert a['codec_name']=='aac' and a['channels']==1 and int(a['sample_rate'])==SR
    width,height=160,90
    cmd=['ffmpeg','-v','error','-threads','2','-i',str(file),'-filter_threads','1','-vf',f'scale={width}:{height}:flags=area',
         '-pix_fmt','gray','-an','-f','rawvideo','-']
    black=[]
    with subprocess.Popen(cmd,stdout=subprocess.PIPE) as decode:
        for n in range(expected):
            raw=decode.stdout.read(width*height)
            assert len(raw)==width*height,n
            tile=np.frombuffer(raw,np.uint8)
            if np.percentile(tile,95)<15:
                black.append(n)
        assert not decode.stdout.read(1)
        assert decode.wait()==0
    assert not black,black
    print('PASS decoded',expected,'chronological 1080p/24 frames;',len(black),'black',flush=True)
    return r

def verify_final(file):
    e=json.loads((ROOT/'timeline.json').read_text())
    verify_media(file,e['frames'],True)
    a=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(file),
                                            '-map','0:a','-f','f32le','-']),np.float32)
    rate,pcm=wavfile.read(ROOT/'mix.wav')
    assert len(a)>=len(pcm) and np.isfinite(a).all() and abs(a).max()<.97 and rate==SR
    results=[]
    last=0
    step=SR//FPS
    for seg in e['dialogue']:
        wav=load_take(seg['wav'])
        start=seg['start']*step
        end=start+len(wav)
        assert start>=last and not np.any(pcm[last:start])
        assert np.max(abs(pcm[start:end].astype(np.float64)/32767-wav))<.00002
        corr=float(np.corrcoef(wav,a[start:end])[0,1])
        assert corr>.985,(seg,corr)
        results.append((seg['wav'],seg['kind'],round(corr,6)))
        last=end
    assert not np.any(pcm[last:]) and len(results)==39
    wins=[]
    for t,r in zip(e['episode']['turns'],e['episode']['repeatStarts']):
        start,end,line=t
        d=next(d for d in e['dialogue'] if d['start']==round(r*FPS) and d['kind']=='repeat')
        lead=next(k for k in e['dialogue'] if k['wav']==d['wav'] and k['kind']=='lead')
        assert round(start*FPS)==d['end']+7 and lead['line']==d['line']==line
        assert abs(end-start-3)<1e-5
        peak=float(np.max(abs(a[round(start*SR):round(end*SR)])))
        assert peak<.0001,(line,peak)
        wins.append((line,start,end,peak))
    assert len(wins)==12
    (ROOT/'reviews/final-audio.json').write_text(json.dumps(dict(pcm_correlations=results,turns=wins),indent=2))
    print('PASS 39 dry dialogue events and 12 silent response windows; min source correlation',min(d[2] for d in results))

if __name__=='__main__':
    if '--gate' in sys.argv:
        from exposures import action
        verify_media(ROOT/'Animation_Check_1080p.mp4',sum(action(n).duration for n in ('wake','shoes','depart')))
    else:
        verify_final(ROOT/'Good_Morning_Yoonsu_1080p.mp4')
