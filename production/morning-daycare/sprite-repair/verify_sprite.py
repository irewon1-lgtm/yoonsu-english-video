"""Verify the delivered 2D frame clock, mono English track, and active sprite exposures."""
import argparse
from pathlib import Path
import json
import subprocess

import numpy as np
from scipy.io import wavfile

ROOT=Path(__file__).resolve().parent
FPS=24
RATE=48000
FRAMES=4968
PERSLOT=RATE//FPS

def ffprobe(file,*args):
    command=['ffprobe','-v','error',*args,'-of','json',str(file)]
    return json.loads(subprocess.check_output(command))

def verify_video(file,frames=FRAMES,audio=True):
    meta=ffprobe(file,'-show_streams','-show_format')
    video=[s for s in meta['streams'] if s['codec_type']=='video']
    voice=[s for s in meta['streams'] if s['codec_type']=='audio']
    assert len(video)==1 and len(voice)==int(audio)
    v=video[0]
    assert (v['codec_name'],v['width'],v['height'],v['r_frame_rate'])==('h264',1920,1080,'24/1'),v
    assert abs(float(meta['format']['duration'])-frames/FPS)<.045
    if audio:
        a=voice[0]
        assert a['codec_name']=='aac' and a['sample_rate']=='48000' and a['channels']==1,a
    timing=ffprobe(file,'-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time')
    measured=np.array([float(x['best_effort_timestamp_time']) for x in timing['frames']])
    assert len(measured)==frames and np.max(np.abs(measured-np.arange(frames)/FPS))<.000002
    return {'seconds':frames/FPS,'frames':frames,'width':v['width'],'height':v['height'],'video':'H.264','audio':'mono AAC' if audio else None}

def compare_aac(file,timeline):
    sr,source=wavfile.read(ROOT/'mix.wav')
    assert sr==RATE and source.shape==(FRAMES*PERSLOT,)
    decoded=subprocess.check_output(['ffmpeg','-nostdin','-v','error','-threads','2','-i',str(file),
          '-map','0:a:0','-ar','48000','-ac','1','-f','s16le','-'])
    pcm=np.frombuffer(decoded,dtype='<i2')
    assert len(pcm)>=len(source)
    matches=[]
    for d in timeline['dialogue']:
        a,b=d['start']*PERSLOT,d['end']*PERSLOT
        x=source[a:b].astype(np.float64)
        y=pcm[a:b].astype(np.float64)
        c=np.dot(x,y)/(np.linalg.norm(x)*np.linalg.norm(y))
        matches.append(float(c))
        assert c>.975,(d['wav'],d['kind'],c)
    assert len(matches)==58
    silent=[]
    for s in timeline['scenes']:
        a,b,line=s['turn']
        assert b-a==72
        assert not source[a*PERSLOT:b*PERSLOT].any(),s['key']
        y=pcm[a*PERSLOT:b*PERSLOT].astype(np.float64)
        rms=float(np.sqrt(np.mean(y*y)))/32768
        assert rms<.00048,(s['key'],rms)
        silent.append(rms)
    return {'events':len(matches),'minimum_aac_pcm_correlation':min(matches),'learner_pauses':len(silent),'seconds_each':3,
            'max_pause_rms_full_scale':max(silent),'peak_after_decode':float(np.max(np.abs(pcm.astype(np.int32))))/32768}

def picture_scan(file,timeline):
    # Low-resolution decode measures consecutive picture changes. Edges outside
    # the title/subtitle area are left intact. Static holds for learner turns
    # are explicit in the edit and are separate from the active test sequences.
    w,h=320,180
    frame_size=w*h*3
    cmd=['ffmpeg','-nostdin','-v','error','-threads','2','-i',str(file),'-an','-filter_threads','1',
         '-vf',f'scale={w}:{h}:flags=area','-pix_fmt','rgb24','-f','rawvideo','-']
    target={
        'wake':(.08,5.47),'wash':(10.05,11.73),'shoes':(8.21,10.70),'depart':(8.25,20.60),
        'street':(9.90,13.50),
    }
    regions={s['key']:(s['start']+round(target[s['key']][0]*FPS),s['start']+round(target[s['key']][1]*FPS))
             for s in timeline['scenes'] if s['key'] in target}
    stats={key:[] for key in regions}
    prior=None
    n=0
    black=0
    with subprocess.Popen(cmd,stdout=subprocess.PIPE) as process:
        while packet:=process.stdout.read(frame_size):
            assert len(packet)==frame_size
            image=np.frombuffer(packet,dtype=np.uint8).reshape(h,w,3)
            if image.mean()<3.5:black+=1
            if prior is not None:
                for key,(a,b) in regions.items():
                    if a<=n<b:
                        delta=np.abs(image[25:148].astype(np.int16)-prior[25:148])
                        stats[key].append(float(delta.mean()))
                        break
            prior=image
            n+=1
        assert process.wait()==0
    assert n==FRAMES and black==0
    analysis={}
    for key,d in stats.items():
        a=np.asarray(d)
        assert len(a)>30
        analysis[key]={'frames':len(a),'median_mean_rgb_change':round(float(np.median(a)),4),
                       'very_low_change_frames_lt_0p03':int((a<.03).sum()),'max_mean_rgb_change':round(float(a.max()),4)}
        # Drawings on twos are intentionally exposed on adjacent output
        # frames. The seal checks motion during these phases, not 24 unique
        # drawings per second during intentional contact holds.
        assert int((a>=.03).sum())>=.20*len(a),(key,analysis[key])
    return {'decoded':n,'black_frames':black,'active_intervals':analysis}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('file',type=Path)
    p.add_argument('--gate',action='store_true')
    p.add_argument('--out',type=Path)
    ns=p.parse_args()
    report=verify_video(ns.file,frames=579 if ns.gate else FRAMES,audio=not ns.gate)
    if not ns.gate:
        t=json.loads((ROOT/'timeline.json').read_text())
        report.update(audio_metrics=compare_aac(ns.file,t),picture_metrics=picture_scan(ns.file,t))
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if ns.out:
        ns.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__':
    main()
