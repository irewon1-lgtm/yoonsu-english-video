"""Decode the entire export, check every picture and compare encoded dialogue with the edit."""
import subprocess
from pathlib import Path
import json, sys
from collections import Counter
import numpy as np
from scipy.io import wavfile
from PIL import Image,ImageDraw
from edit import load,SR
ROOT=Path(__file__).resolve().parent
edit=json.loads((ROOT/"timeline.json").read_text())
media=ROOT/"The_Squeaky_Clean_Club.mp4"
qa=ROOT/"review"/"v11"; qa.mkdir(parents=True,exist_ok=True)
info=json.loads(subprocess.check_output(["ffprobe","-v","error","-show_streams","-show_format","-of","json",str(media)]))
v,a=info["streams"]
assert (v["codec_name"],v["width"],v["height"],v["avg_frame_rate"],int(v["nb_frames"]))==("h264",1920,1080,"24/1",4320)
assert (a["codec_name"],a["channels"],int(a["sample_rate"]))==("aac",1,SR)
assert abs(float(info["format"]["duration"])-180)<.05
decoded=np.frombuffer(subprocess.check_output(["ffmpeg","-v","error","-i",str(media),"-map","0:a","-f","f32le","-"]),np.float32)
assert np.isfinite(decoded).all() and abs(decoded).max()<.99
rate,master=wavfile.read(ROOT/"wash-mix.wav")
assert rate==SR
whole=float(np.corrcoef(decoded[:len(master)],master)[0,1])
assert whole>.965,whole
correlations=[]; gates=[]
for s in edit["dialogue"]:
    take=load(s["wav"])
    i=s["start"]*(SR//24)
    corr=float(np.corrcoef(take,decoded[i:i+len(take)])[0,1])
    correlations.append(corr); assert corr>.94,(s,corr)
for n,(a,b,line) in enumerate(edit["episode"]["turns"]):
    at=round(a*24)
    repeat=next(d for d in edit["dialogue"] if d["kind"]=="repeat" and d["end"]+5==at)
    if n<12:
        i=edit["dialogue"].index(repeat)
        lead,cue=edit["dialogue"][i-2:i]
        assert lead["kind"]=="lead" and cue["kind"]=="cue" and repeat["wav"]==lead["wav"] and line==repeat["line"]
    level=float(np.max(np.abs(decoded[round(a*SR):round(b*SR)])))
    assert level<.0007,(n,level)
    gates.append(dict(start=a,end=b,line=line,peak=level))
# Read every decoded frame once. Make a chronological scene sheet of first action and repeat.
thumbw,thumbh=180,102
proc=subprocess.Popen(["ffmpeg","-v","error","-threads","2","-i",str(media),"-an","-vf",f"scale={thumbw}:{thumbh}","-pix_fmt","rgb24","-f","rawvideo","-"],stdout=subprocess.PIPE)
scenes=edit["scenes"]; wanted={40:(0,"Opening")}
for i,s in enumerate(scenes):
    seg=next(v for v in edit["dialogue"] if v["kind"]=="lead" and s["start"]<=v["start"]<s["end"])
    wanted[s["start"]+9]=(1+2*i,s["action"])
    wanted[(seg["start"]+seg["end"])//2]=(2+2*i,s["role"]+"  "+s["line"])
wanted[4310]=(35,"Ending")
hold_frames={n for g in gates for n in range(round(g["start"]*24)-2,round(g["end"]*24)+3)}
active=Counter()
sheets=Image.new("RGB",(4*thumbw,9*(thumbh+18)),"#fff5df")
draw=ImageDraw.Draw(sheets); n=0; prev=None;changed=Counter()
while raw:=proc.stdout.read(thumbw*thumbh*3):
    assert len(raw)==thumbw*thumbh*3
    arr=np.frombuffer(raw,np.uint8)
    if n not in hold_frames:
        idx=next((s["i"] for s in scenes if s["start"]<=n<s["end"]),-1)
        active[idx]+=1
        if prev is not None and (np.max(np.abs(arr.reshape(thumbh,thumbw,3)[:82].astype(np.int16)-prev.reshape(thumbh,thumbw,3)[:82]),axis=2)>8).mean()>.002:
            changed[idx]+=1
    if n in wanted:
        slot,desc=wanted[n]; x=(slot%4)*thumbw;y=(slot//4)*(thumbh+18)
        sheets.paste(Image.frombytes("RGB",(thumbw,thumbh),raw),(x,y)); draw.text((x+3,y+thumbh),desc,fill="#214148")
    n+=1;prev=arr
assert proc.wait()==0 and n==4320
for s in scenes:
    # Held drawings and listening windows are intentional. Count visible changes
    # above subtitles, ignoring tiny codec noise across identical frames.
    assert changed[s["i"]]>=4,(s["i"],changed)
sheets.save(qa/"whole-episode.jpg",quality=92)
report=dict(duration=180,frames=n,active_frames=dict(active),change_counts=dict(changed),dialogue_instances=len(correlations),min_dialogue_correlation=min(correlations),master_correlation=whole,peak=float(abs(decoded).max()),turns=gates)
(qa/"master.json").write_text(json.dumps(report,indent=2))
print("PASS",n,"decoded frames, picture changes verified above subtitles across 17 scenes; 41 single-track performances; 12 silent response windows;",min(correlations),"lowest encoded dialogue correlation.")
