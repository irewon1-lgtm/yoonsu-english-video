"""Register a set of complete authored cels to one camera and store their exposures."""
from pathlib import Path
import json
import sys
import cv2
import numpy as np
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parent
DEST=ROOT/'assets'/'registered'
TARGET=(832,468)
CAMERAS={
    'wash':(.18,.13,.88,.96),
    'brush':(.16,.12,.89,.96),
    'breakfast-eat':(.16,.16,.80,.95),
    'bag-find':(.08,.11,1.,1.),
}

def cels(path, grid=(2,3)):
    with Image.open(path) as image:
        raw=image.convert('RGB')
    cols,rows=grid
    tiles=[]
    for i in range(cols*rows):
        x,y=i%cols,i//cols
        rect=(round(x*raw.width/cols)+2,round(y*raw.height/rows)+2,
              round((x+1)*raw.width/cols)-2,round((y+1)*raw.height/rows)-2)
        tiles.append(np.asarray(ImageOps.fit(raw.crop(rect),TARGET,method=Image.Resampling.LANCZOS)))
    return tiles

def locked_set(ref,tiles,protected):
    """Measure camera shifts in the static exterior and leave the protected action intact."""
    h,w=ref.shape[:2]
    x0,y0,x1,y1=(round(v*n) for v,n in zip(protected,(w,h,w,h)))
    protect=np.zeros((h,w),np.uint8);protect[y0:y1,x0:x1]=255
    mask=255-protect
    mask[:9]=0;mask[-9:]=0;mask[:,:9]=0;mask[:,-9:]=0
    # The feather falls outside the complete body and prop action.
    edge=np.clip(cv2.distanceTransform(255-protect,cv2.DIST_L2,3)/26.,0,1)
    g=cv2.cvtColor(ref,cv2.COLOR_RGB2GRAY)
    result=[ref];checks=[(1.0,0.0,0.0)]
    for pose in tiles[1:]:
        y=cv2.cvtColor(pose,cv2.COLOR_RGB2GRAY)
        warp=np.eye(2,3,dtype=np.float32)
        try:
            cc,warp=cv2.findTransformECC(g,y,warp,cv2.MOTION_TRANSLATION,
                            (cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,35,.0004),mask,3)
        except cv2.error:
            cc=0.
        dx,dy=map(float,warp[:,2])
        if cc>=.90 and max(abs(dx),abs(dy))<=9:
            pose=cv2.warpAffine(pose,warp,(w,h),flags=cv2.INTER_LANCZOS4|cv2.WARP_INVERSE_MAP,
                                borderMode=cv2.BORDER_REFLECT101)
        elif cc<.90 or max(abs(dx),abs(dy))>9:
            # No forced shift when the stationary texture does not establish it.
            dx=dy=0.
        locked=np.rint(pose*(1-edge[:,:,None])+ref*edge[:,:,None]).astype(np.uint8)
        result.append(locked)
        checks.append((round(float(cc),4),round(dx,2),round(dy,2)))
    return result,checks

def main():
    setup=json.loads(Path(sys.argv[1]).read_text())
    DEST.mkdir(parents=True,exist_ok=True)
    manifest={}
    stats={}
    for name,(new_path,ordering) in setup.items():
        old=cels(ROOT/'assets'/'base'/f'act-{name}.png')
        new=cels(new_path)
        frames=[(old if index<6 else new)[index%6] for index in ordering]
        frames,checks=locked_set(frames[0],frames,CAMERAS[name])
        first=DEST/f'compound-{name}.png'
        w,h=TARGET
        sheet=Image.new('RGB',(w*2,h*((len(frames)+1)//2)))
        for i,pose in enumerate(frames):
            sheet.paste(Image.fromarray(pose),(i%2*w,i//2*h))
        sheet.save(first,optimize=False)
        manifest[first.stem]={'file':first.name,'grid':[2,(len(frames)+1)//2],
                              'inset':0,'source_size':list(TARGET),'action_order':ordering}
        stats[name]={'reg_static_correlation_then_x_y':checks,'protected_full_motion_rect':CAMERAS[name]}
        print(name,len(frames),checks,flush=True)
    (ROOT/'extra-sheets.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (ROOT/'reviews'/'registered-action-stats.json').write_text(json.dumps(stats,indent=2)+'\n')

if __name__=='__main__':
    main()
