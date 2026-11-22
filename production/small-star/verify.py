"""Verify the exported dialogue and every practice transition."""
from pathlib import Path
import subprocess
import json
import numpy as np
from scipy.io import wavfile
from edit import ROOT,SR,FPS,load

def ffprobe(file):
    return json.loads(subprocess.check_output(['ffprobe','-v','error','-show_streams',
                                               '-show_format','-of','json',str(file)]))

def verify(file):
    data=json.loads((ROOT/'timeline.json').read_text())
    info=ffprobe(file)
    video,audio=info['streams']
    assert (video['codec_name'],video['width'],video['height'],int(video['nb_frames']),video['avg_frame_rate'])==(
        'h264',1920,1080,data['frames'],'24/1')
    assert audio['codec_name']=='aac' and audio['channels']==1 and int(audio['sample_rate'])==SR
    assert abs(float(info['format']['duration'])-data['frames']/FPS)<.03
    a=np.frombuffer(subprocess.check_output(['ffmpeg','-v','error','-i',str(file),
        '-map','0:a','-f','f32le','-']),np.float32)
    rate,pcm=wavfile.read(ROOT/'mix.wav')
    mix=pcm.astype(np.float64)/32768
    assert len(a)>=len(mix) and np.isfinite(a).all()
    assert np.max(np.abs(a))<.94
    waveforms=[]
    previous_end=0
    for line in data['dialogue']:
        at=line['start']*SR//FPS
        stem=load(line['wav'])
        end=at+len(stem)
        assert previous_end<=at and not np.any(mix[previous_end:at])
        previous_end=end
        assert np.max(np.abs(mix[at:end]-stem))<2/32768
        corr=float(np.corrcoef(stem,a[at:end])[0,1])
        assert corr>.985,(line['line'],corr)
        waveforms.append([line['wav'],line['kind'],round(corr,6)])
    assert not np.any(mix[previous_end:])
    for first,last,phrase in data['episode']['turns']:
        start=round(first*FPS)
        idx=next(i for i,line in enumerate(data['dialogue'])
                 if line['kind']=='repeat' and line['end']+7==start)
        lead,cue,repeated=data['dialogue'][idx-2:idx+1]
        assert cue['wav']=='cue' and lead['wav']==repeated['wav'] and repeated['line']==phrase
        quiet_max=float(np.max(np.abs(a[round(first*SR):round(last*SR)])))
        assert quiet_max<1e-4,(phrase,quiet_max)
    report=dict(file=str(file),duration=float(info['format']['duration']),frame_count=data['frames'],
                waveform_by_line=waveforms,monophonic=True,digital_peak=float(np.max(np.abs(a))),
                response_windows=len(data['episode']['turns']))
    print('PASS',report['frame_count'],'frames;',len(waveforms),'single-voice events;',
          report['response_windows'],'silent response windows; min PCM/AAC correlation',min(x[2] for x in waveforms))
    (ROOT/'review'/'export_audio.json').write_text(json.dumps(report,indent=2)+'\n')

if __name__=='__main__':
    import sys
    verify(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'The_Little_Star.mp4')
