"""Playback of immutable poses with explicit integer holds."""
from bisect import bisect_right
from itertools import accumulate
import json
from pathlib import Path
from PIL import Image
from functools import lru_cache

ROOT=Path(__file__).resolve().parent

class Action:
    def __init__(self,key):
        self.key=key
        self.directory=ROOT/'actions'/key
        self.record=json.loads((self.directory/'index.json').read_text())
        self.holds=self.record['exposure_frames']
        self.files=self.record['frames']
        assert self.files and len(self.holds)==len(self.files),key
        assert all(type(i)==int and i>0 for i in self.holds),key
        for f in self.files:
            assert (self.directory/f).is_file(),(key,f)
        plate=self.record.get('plate')
        self.plate=self.directory/plate if plate else None
        self.plates=[self.directory/p for p in self.record.get('plates',[])]
        assert not self.plates or len(self.plates)==len(self.files),key
        self.dest=tuple(self.record.get('dest',[0,0,1,1]))
        self.boundaries=list(accumulate(self.holds))
        self.duration=self.boundaries[-1]

    def index_at(self,offset):
        return min(bisect_right(self.boundaries,max(0,offset)),len(self.files)-1)

    def plate_at(self,offset):
        return self.plates[self.index_at(offset)] if self.plates else self.plate

    def path_at(self,offset):
        return self.directory/self.files[self.index_at(offset)]

@lru_cache(30)
def action(key):
    return Action(key)

def available(key):
    return (ROOT/'actions'/key/'index.json').is_file()

@lru_cache(3)
def actor_manifest():
    return json.loads((ROOT/'assets/walk/walk.json').read_text())

def walk_at(frame):
    records=actor_manifest()['frames']
    pose=records[min(len(records)-1,max(0,frame))]
    return ROOT/'assets/walk'/pose['file'],pose['dx'],pose['contact']
