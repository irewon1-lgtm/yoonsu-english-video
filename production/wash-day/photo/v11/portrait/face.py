"""Playback of registered, held photographic dialogue exposures at the film's 24 fps."""
from functools import lru_cache
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
SIZE = 836, 816
SHAPES = 'XABCDEFGH'
EYE_BOX = 282, 278, 601, 439

# (first local video frame, replacement cel). The takes were timed at 24fps from
# their actual mastered dialogue audio and the original voice model's phonemes.
# X rest, A lip seal, B teeth, C narrow vowel, D wide vowel, E open round,
# F pursed, G lip/teeth and H tongue.
TAKES = {
    '01': ((0,'X'),(1,'H'),(3,'C'),(6,'B'),(9,'C'),(11,'B'),(13,'H'),
           (15,'C'),(17,'B'),(20,'C'),(23,'A'),(27,'X')),
    '03': ((0,'X'),(1,'C'),(3,'B'),(5,'C'),(8,'B'),(11,'C'),(13,'A'),
           (15,'B'),(18,'E'),(20,'F'),(22,'A'),(25,'X')),
    '05': ((0,'B'),(2,'C'),(5,'B'),(9,'E'),(12,'G'),(14,'H'),(15,'C'),
           (16,'A'),(18,'C'),(20,'A'),(21,'C'),(23,'H'),(25,'B'),(30,'X')),
    '07': ((0,'A'),(2,'C'),(4,'B'),(8,'C'),(11,'B'),(13,'C'),(14,'D'),
           (16,'C'),(17,'H'),(19,'C'),(25,'B'),(29,'X')),
    '09': ((0,'X'),(1,'C'),(4,'A'),(6,'E'),(8,'C'),(10,'B'),(12,'A'),
           (14,'C'),(17,'B'),(19,'C'),(23,'B'),(24,'H'),(28,'X')),
    '11': ((0,'F'),(2,'E'),(3,'C'),(5,'A'),(7,'C'),(9,'E'),(10,'B'),
           (11,'A'),(13,'C'),(15,'B'),(16,'G'),(18,'C'),(23,'B'),(27,'X')),
    '14': ((0,'A'),(2,'C'),(3,'D'),(5,'C'),(6,'B'),(7,'A'),(8,'C'),
           (10,'H'),(11,'C'),(13,'B'),(15,'C'),(18,'E'),(20,'F'),
           (21,'C'),(23,'H'),(25,'X')),
    '15': ((0,'C'),(1,'D'),(3,'C'),(4,'A'),(6,'B'),(7,'H'),(9,'C'),
           (13,'B'),(14,'C'),(16,'B'),(18,'E'),(21,'F'),(22,'B'),
           (25,'C'),(28,'B'),(30,'X')),
}

# One-shot action cues on the episode's absolute frame clock; no cycle. Blinks
# generally fall at a breath or between contributions, with a two-frame hold.
BLINKS = (269, 650, 772, 1281, 1877, 1989, 2305, 2850, 3636, 3927, 4016)

@lru_cache(maxsize=1)
def atlas():
    with Image.open(HERE/'atlas.png') as sheet:
        return sheet.convert('RGBA')

@lru_cache(maxsize=1)
def closed_lids():
    with Image.open(HERE/'closed-eyes.png') as tile:
        return tile.convert('RGBA')

@lru_cache(maxsize=18)
def image_for(shape, eyes_closed=False):
    """Read-only film cel with straight alpha and 836×816 native film-facing bounds."""
    w,h=SIZE
    index=SHAPES.index(shape)
    x,y=index%3*w,index//3*h
    tile=atlas().crop((x,y,x+w,y+h))
    if eyes_closed:
        tile.paste(closed_lids(),EYE_BOX)
    return tile

def exposure_at(cue, absolute_frame, fps=24):
    """Return (mouth cel ID, closed eyelids) for the requested timeline frame."""
    t=(absolute_frame+.5)/fps
    closed=any(first<=t*24<first+2 for first in BLINKS)
    if not cue or cue.get('role')!='Y' or not cue['start']<=absolute_frame<cue['end']:
        return 'X',closed
    local=(absolute_frame+.5-cue['start'])*24/fps
    for first,shape in reversed(TAKES[cue['wav']]):
        if first<=local:
            return shape,closed
    return 'X',closed

def face_at(cue, absolute_frame, fps=24):
    """Return the cached PIL RGBA portrait for this absolute episode frame."""
    return image_for(*exposure_at(cue,absolute_frame,fps))
