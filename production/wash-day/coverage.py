"""Camera cuts and action clocks for the 24 fps Wash Day edit."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Shot:
    first: int
    last: int  # exclusive
    camera: str

# Before and after a spoken turn, show a different part of the same action.
# These are actual camera angles: body=ensemble, medium=closer two-shot,
# detail=macro, character name=dialogue lens.
LEAD_ANGLES = [
    ("walk","walk"), ("medium","Y"), ("body","detail"), ("medium","Y"),
    ("body","detail"), ("medium","Y"), ("body","detail"), ("detail","Y"),
    ("medium","detail"), ("body","Y"), ("medium","body"), ("detail","Y"),
    ("body","detail"), ("medium","detail"), ("body","Y"), ("medium","Y"), ("detail","detail")
]
TAIL_ANGLES = {2:"detail",3:"detail",4:"body",5:"detail",6:"medium",7:"detail",
               9:"detail",10:"medium",12:"body",13:"medium",14:"detail",15:"body"}

def make_cuts(scene, dialogue, turn):
    idx=scene["i"]
    first, end=scene["start"],scene["end"]
    lead=dialogue[0]
    intro, main=LEAD_ANGLES[idx]
    if idx==14: intro="pickup"
    if idx==3: intro="soap_start"
    if idx==16: intro="book_open"
    changes=[(first,intro)]
    if idx==0:
        changes.append((first+66,"S"))
    elif idx==1:
        # End the entrance shot with a separate, closer view of his muddy hands.
        changes.append((lead["start"]-5,main))
    elif idx==16:
        changes.extend([(first+45,"book_turn"),(first+101,"book_settle")])
    elif main!=intro:
        changes.append((lead["start"]-8,main))
    if turn:
        cue,repeat=dialogue[1:]
        changes.extend([((lead["end"]+cue["start"])//2,"S"),
                        ((cue["end"]+repeat["start"])//2,repeat["role"]),
                        (turn[1]+10,TAIL_ANGLES[idx])])
    # Keep coverage through the gaps between lines. A silent gap does not make a new cut.
    merged=[]
    for start,camera in changes:
        if not merged or merged[-1][1]!=camera: merged.append((start,camera))
    return [Shot(s, merged[j+1][0] if j+1<len(merged) else end,camera)
            for j,(s,camera) in enumerate(merged)]

def action_progress(frame, scene, turn):
    # Remove the held frames from the running action. This same function is
    # used on both sides of the interactive seek, including the stand-alone MP4.
    first,end=scene["start"],scene["end"]
    held=0
    if turn:
        a,b=turn[:2]
        held=max(0,min(frame,b)-a)
        end-=b-a
    return min(1,max(0,(frame-first-held)/max(1,end-first-1)))

def steady_frame(frame,turn):
    if not turn: return frame
    a,b=turn[:2]
    if a-2<=frame<=b+2: return a-2
    return frame if frame<a else frame-(b-a+4)
