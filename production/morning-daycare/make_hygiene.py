"""Stage the previously approved contact poses with new bathroom timing and pajamas."""
from pathlib import Path
import argparse,json,sys
import numpy as np
import cv2
from PIL import Image
from compose_strips import pack

R=Path(__file__).resolve().parent
baseline=Path('/workspace/work/wash-day')
sys.path.insert(0,str(baseline))
from photo.v11.macro.cutaways_v11 import actor_at as macro_actor,plate_at as macro_plate
from photo.v11.closeups.cutaways_v11 import cutaway_at
from photo.v11.practicals.practicals import background as backdrop
from photo.v11.hd.masters import at as old_body

SIZE=(1280,720)
RESAMPLE=Image.Resampling.LANCZOS

def bedclothes(sprite,strong=False):
    """Match slate-blue PJs on the isolated coloured knit pixels."""
    s=np.array(sprite.convert('RGBA'))
    hsv=cv2.cvtColor(s[:,:,:3],cv2.COLOR_RGB2HSV)
    h,sat,value=np.moveaxis(hsv,2,0)
    elig=((sat>16)&(h>=37)&(h<150)&(value<245)&(value>21)&(s[:,:,3]>30))
    rows=np.indices(h.shape)[0]
    if not strong:
        elig &= rows > h.shape[0]*.30
    hsv[:,:,0][elig]=107
    hsv[:,:,1][elig]=78
    hsv[:,:,2][elig]=np.uint8(np.clip(74+.26*value[elig],72,140))
    s[:,:,:3]=cv2.cvtColor(hsv,cv2.COLOR_HSV2RGB)
    return Image.fromarray(s)

def fullbody(key,index):
    im=bedclothes(old_body(key,index))
    h=630
    result=Image.new('RGBA',SIZE)
    result.alpha_composite(im.resize((h,h),RESAMPLE),(449,6))
    return result

def composite(key,records,plates,marks):
    dst=R/'actions'/key
    dst.mkdir(exist_ok=True,parents=True)
    plate_files={}
    for name,source in plates.items():
        f=f'set-{name}.webp'
        source.convert('RGB').resize(SIZE,RESAMPLE).save(dst/f,'WEBP',lossless=True,method=1)
        plate_files[name]=f
    cels=[pose.resize(SIZE,RESAMPLE) for pose,_,_ in records]
    lens=(345,112,1129,553)
    for desc in ('wide',):
        if desc in plates:
            original=plates[desc].convert('RGB').resize(SIZE,RESAMPLE)
            original.crop(lens).resize(SIZE,RESAMPLE).save(dst/plate_files[desc],'WEBP',lossless=True,method=1)
    for j,(_,desc,_) in enumerate(records):
        if desc=='wide':
            cels[j]=cels[j].crop(lens).resize(SIZE,RESAMPLE)
    holds=[hold for _,_,hold in records]
    pack(dst,None,cels,holds,[1152,648],"Approved Wash Day v11 timed primitive and actual shot layers; revised scenes, costume palette, camera cut clocks and order.",marks,'slate pajamas','fixed camera per contact action')
    p=dst/'index.json'
    d=json.loads(p.read_text())
    d['plates']=[plate_files[key] for _,key,_ in records]
    p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
    print(key,len(records),sum(holds))

def wash():
    bath=Image.open(R/'assets/bath.png')
    plates={'tap':macro_plate('tap'),'face':backdrop('bath'),'wide':bath,'towel':macro_plate('towel_pickup')}
    seq=[]
    # Open the tap after the hand makes contact, then move to the hands and face.
    for i,u in enumerate([0,.12,.22,.32,.43,.54,.68,.81,.92]):
        seq.append((bedclothes(macro_actor('tap',u),True),'tap',3))
    for i in (0,1,2,3):
        seq.append((fullbody('scoop_waist',i),'wide',6))
    for n in (.18,.26,.4,.53,.69,.84):
        seq.append((bedclothes(cutaway_at('splash',n)),'face',5))
    for i in (0,1,2,3,4,5,6):
        seq.append((fullbody('hi_dab',i),'wide',4))
    # Reverse the photographed placement arc after drying; the towel rests on
    # the same countertop and the single faucet returns to its initial stop.
    seq.extend((bedclothes(macro_actor('towel_pickup',v),True),'towel',3) for v in [.8,.6,.4,.2,.08])
    seq.extend((bedclothes(macro_actor('tap',v),True),'tap',3) for v in [.81,.61,.43,.25,0])
    marks=[{'frame':12,'state':'turn valve after grip'}, {'frame':39,'state':'cup hands below spout'},
           {'frame':65,'state':'water to face and withdraw'}, {'frame':92,'state':'towel contact'},
           {'frame':120,'state':'return microfiber towel to counter'}, {'frame':133,'state':'close faucet'}]
    composite('wash',seq,plates,marks)

def brush(cup):
    bath=Image.open(R/'assets/bath.png')
    stage={'face':backdrop('bath'),'wide':bath}
    seq=[(fullbody('prepare',i),'wide',4) for i in (0,2,4,6,7)]
    seq.extend((bedclothes(cutaway_at('brush',v)),'face',6)
               for v in [.12,.21,.30,.40,.49,.57,.66,.74,.81,.75,.86,.91])
    seq.extend((fullbody('downbrush',v),'wide',3) for v in (1,3,5,7))
    with Image.open(cup) as raw:
        w,h=raw.size
        for j in range(4):
            x0=round(w*(j%2)/2);y0=round(h*(j//2)/2)
            panel=raw.crop((x0,y0,round(x0+w/2),round(y0+h/2))).convert('RGB')
            name=f'cup-{j}'
            stage[name]=panel
            seq.append((Image.new('RGBA',SIZE),name,[10,12,12,12][j]))
    # The cup insert is an opaque scene plate with a transparent cel; each
    # already-authored sink frame should instead be retained as the acting cel.
    for n in range(len(seq)-4,len(seq)):
        _,name,hold=seq[n]
        seq[n]=(stage[name].convert('RGBA'),name,hold)
    marks=[{'frame':12,'state':'pick up toothbrush'}, {'frame':31,'state':'bristles first touch'},
           {'frame':63,'state':'short strokes across same front teeth'},
           {'frame':100,'state':'lower toothbrush before cup'}, {'frame':104,'state':'grip cup'},
           {'frame':126,'state':'cup rim at lips'}, {'frame':138,'state':'set down cup'}]
    composite('brush',seq,stage,marks)

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--cup',type=Path)
    p.add_argument('--wash',action='store_true')
    opts=p.parse_args()
    if opts.wash:wash()
    if opts.cup:brush(opts.cup)
