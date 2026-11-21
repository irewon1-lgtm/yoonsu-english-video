"""Read the pre-rendered anatomical toe-washing insert in authored frame order."""
from pathlib import Path
from functools import lru_cache
from PIL import Image
HERE=Path(__file__).resolve().parent
@lru_cache(maxsize=24)
def _read(n):
    with Image.open(HERE/'frames'/f'{n:02d}.webp') as image:
        return image.convert('RGB')
def insert_at(phase):
    n=round(max(0.,min(1.,float(phase)))*23)
    return _read(n)
