"""Lookup of intact photographed poses for the wash-day hygiene close-ups."""
from functools import lru_cache
from pathlib import Path
from PIL import Image

HERE = Path(__file__).resolve().parent
# Normalized editorial holds. Middle brushing cels show a complete reversal
# across the same front teeth. Index 0 approaches, 1 touches, 2 seats the head.
EXPOSURES = {
    'brush': (0,0,1,2,3,4,5,6,7,6,7,7),
    'splash': (0,0,1,2,3,3,4,5,5),
    'cheeks': (0,1,2,2,3,4,5,5),
    'feet': (0,0,1,2,3,4,5,5),
    'toes': (0,1,2,3,4,5,6,7),
}
@lru_cache(maxsize=32)
def _cel(key, index):
    with Image.open(HERE/'frames'/key/f'{index:02d}.webp') as source:
        return source.convert('RGBA')

def cutaway_at(key, u):
    sequence=EXPOSURES[key]
    position=min(len(sequence)-1,int(max(0.0,min(1.0,float(u)))*len(sequence)))
    return _cel(key,sequence[position]).copy()
