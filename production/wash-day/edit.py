"""Build a frame-accurate 24 fps edit and a clean mono mix from the editable performances."""
from pathlib import Path
import json
import math
import wave
import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

ROOT = Path(__file__).resolve().parent
FPS = 24
SR = 48000
def load(name):
    rate, samples = wavfile.read(ROOT / "audio" / (name + ".wav"))
    assert samples.ndim == 1, name
    if samples.dtype.kind == "i":
        samples = samples.astype("float64") / (2 ** (samples.dtype.itemsize * 8 - 1))
    else:
        samples = samples.astype("float64")
    factor = math.gcd(rate, SR)
    return resample_poly(samples, SR // factor, rate // factor)

def build():
    script = json.loads((ROOT/"story.json").read_text())
    names = [f"{i:02d}" for i in range(len(script))]
    takes = {name: load(name) for name in names + ["cue"]}
    lengths = {key: math.ceil(len(s) * FPS / SR) for key,s in takes.items()}
    opening, ending = 83, 38
    full = 180*FPS
    timeline, segments, turns, repeats = [], [], [], []
    minimums = []
    for row, name in zip(script, names):
        d = lengths[name]
        minimums.append(18 + (2*d+lengths["cue"]+12+11+5+72 if row["target"] else d) + 25)
    leftover = full - opening - ending - sum(minimums)
    assert leftover >= 0, f"Performances exceed edit by {-leftover / FPS}s"
    weights = [1.6 if r["target"] else 1 for r in script]
    cumulative = np.rint(np.cumsum(weights)*leftover/sum(weights)).astype(int)
    extras = np.diff(np.r_[0,cumulative])
    cursor = opening
    for i,(row,name) in enumerate(zip(script,names)):
        span = int(minimums[i] + extras[i])
        end = cursor + span
        preroll = 18 + int(extras[i] * (.48 if row["target"] else .40))
        at = cursor+preroll
        seg = dict(row, start=at, end=at+lengths[name], wav=name, kind="lead")
        segments.append(seg)
        if row["target"]:
            cue = seg["end"]+12
            segments.append(dict(start=cue,end=cue+lengths["cue"],wav="cue",role="S",line="Yoonsu, your turn!",kind="cue"))
            again = cue+lengths["cue"]+11
            segments.append(dict(seg,start=again,end=again+lengths[name],kind="repeat"))
            stop = again+lengths[name]+5
            turns.append([round(stop/FPS,6),round((stop+72)/FPS,6),row["line"]])
            repeats.append(round(again/FPS,6))
        timeline.append(dict(row,i=i,start=cursor,end=end))
        cursor=end
    assert cursor+ending == full
    out = np.zeros(full * (SR//FPS))
    for seg in segments:
        s = seg["start"]*(SR//FPS)
        clip = takes[seg["wav"]]
        assert not np.any(out[s:s+len(clip)])
        out[s:s+len(clip)] = clip
    # Original four-note theme. Keep every learning utterance and all response windows dry.
    def note(t, pitch, duration, gain, bell=False):
        n = int(duration*SR)
        x = np.arange(n)/SR
        f = 440*2**((pitch-69)/12)
        env = (1-np.exp(-x/.009))*np.exp(-x/(.28 if bell else .43))*np.minimum(1,(duration-x)/.1)
        harmonics = np.sin(2*np.pi*f*x) + .19*np.sin(4*np.pi*f*x) + .07*np.sin((5.98 if bell else 6)*np.pi*f*x)
        s = round(t*SR)
        n = min(len(out)-s,n)
        if n>0: out[s:s+n] += gain*env[:n]*harmonics[:n]
    for time, pitch in [(0,60),(.02,67),(.25,72),(.53,76),(.88,79),(1.26,74),(1.55,76),(2,72),(2.08,64),(2.16,67)]:
        note(.13+time,pitch,.94,.057, pitch>70)
    for time,pitch in [(0,67),(.18,72),(.4,76),(.73,72),(.75,64),(.77,67)]:
        note(cursor/FPS+.03+time,pitch,.77,.052,pitch>70)
    # Little practical sounds run inside picture prerolls only. Leave a clean
    # quarter second ahead of every voice and absolute silence at each mic gate.
    from scipy.signal import butter, sosfilt
    rng=np.random.default_rng(413)
    for shot in timeline:
        act=shot["action"]
        if act not in {"tap","soap","rub","rinse","splash","brush","feet","toes","towel"}: continue
        start=shot["start"]/FPS+.24
        first=next(x["start"]/FPS for x in segments if shot["start"]<=x["start"]<shot["end"])
        dur=min(.88,first-start-.28)
        if dur<.2: continue
        x=np.arange(int(dur*SR))/SR
        if act in {"tap","soap","feet","toes","splash"}:
            fx=np.zeros(len(x))
            for j,delay in enumerate((.05,.24,.47)):
                u=np.maximum(0,x-delay)
                f=780+180*j
                fx += .043*np.sin(2*np.pi*(f*u+1200*u*u))*(1-np.exp(-u/.004))*np.exp(-u/.049)
        else:
            band=(1650,5300) if act=="rinse" else (900,3500)
            noise=sosfilt(butter(3,band,btype="bandpass",fs=SR,output="sos"),rng.normal(0,1,len(x)))
            strokes=(.55+.45*np.cos(2*np.pi*x*(5 if act=="brush" else 2.8)))
            fx=.028*noise*strokes
        envelope=np.minimum(1,x/.05)*np.minimum(1,(dur-x)/.11)
        j=round(start*SR); out[j:j+len(x)] += fx*envelope
    assert np.max(np.abs(out))<.985
    wavfile.write(ROOT/"wash-mix.wav",SR,np.round(out*32767).astype("int16"))
    for s in segments:
        source = json.loads((ROOT/"audio"/(s["wav"]+".json")).read_text())
        s["shapes"] = source["mouthCues"] if isinstance(source,dict) else source
    data=dict(fps=FPS, frames=full, opening=opening,ending=ending,scenes=timeline,dialogue=segments,
              episode=dict(id="wash-day",title="뽀득뽀득 씻기 클럽",turns=turns,repeatStarts=repeats,hints={}))
    (ROOT/"timeline.json").write_text(json.dumps(data,ensure_ascii=False,indent=2))
    def stamp(frame):
        ms=round(1000*frame/FPS)
        return f"{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}"
    (ROOT/"Wash_Day.srt").write_text("\n\n".join(f"{i+1}\n{stamp(s['start'])} --> {stamp(s['end'])}\n{s['line']}" for i,s in enumerate(segments))+"\n")
    print(len(segments),"performances in edit;",len(turns),"speaking turns;",full/FPS,"seconds.")
if __name__=="__main__": build()
