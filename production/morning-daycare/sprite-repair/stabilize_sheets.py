"""Stabilize stationary room pixels in existing opaque dialogue atlases.

Registration uses one translation for the entire cel, estimated from artwork
outside conservative cast and prop bounds. The unaltered actor group always
comes from the registered source exposure. No motion is inferred or redrawn.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT.parent / 'morning-daycare'
DEFAULT_OUT = ROOT / 'overrides' / 'dialogue'
INITIAL = ('dlg-bedroom-pj', 'dlg-bath-pj', 'dlg-bedroom-socks', 'dlg-entry-day')
MIB = 1024 * 1024
OUTPUT_LIMIT = 40 * MIB
SEARCH_RADIUS = 9
PATCH_RADIUS = 10
FEATHER_PX = 9

# Whole cast bounds in the native opaque tile, before the editorial 16:9 crop.
# These include hand contacts, foreground props being held and visible reflections.
GUARDS = {
    'dlg-bedroom-pj': ((.244,.014,.464,.976),(.541,.219,.766,.980),(.587,.865,.935,.995)),
    'dlg-bath-pj': ((.368,.179,.552,.925),(.484,.465,.597,.592),(.716,.199,.943,.922)),
    'dlg-kitchen-pj': ((.125,.116,.685,.996),),
    'dlg-bedroom-dress': ((.287,.013,.855,.995),),
    'dlg-bedroom-socks': ((.213,.005,.565,.997),(.535,.048,.887,.995)),
    'dlg-bedroom-day-bag': ((.394,.089,.924,.997),),
    'dlg-entry-day': ((.187,.058,.446,.969),(.465,.010,.812,.972),(.326,.805,.566,.997)),
    'dlg-entry-pack': ((.224,.091,.769,.995),),
    'dlg-school-day': ((.119,.074,.883,.996),),
    'dlg-mirror': ((.261,.409,.491,.993),(.464,.260,.733,.999)),
    'dlg-search': ((.156,.166,.742,.997),),
    'dlg-alarm-speech': ((.303,.240,.721,.828),(.809,.467,.998,.998)),
    'dlg-street-speech': ((.218,.449,.386,.994),(.326,.427,.492,.994),(.454,.268,.642,.994),(.353,.567,.570,.815)),
    'dlg-arrive-speech': ((.281,.391,.447,.996),(.394,.151,.654,.995),(.669,.125,.954,.977),(.865,.079,.956,.994)),
}


@dataclass(frozen=True)
class TileGrid:
    columns: int
    rows: int
    inset: int
    width: int
    height: int
    source_boxes: tuple

    @classmethod
    def read(cls, shape, setup):
        grid_x, grid_y = setup['grid']
        size_y, size_x = shape[:2]
        inset = int(setup.get('inset', 1))
        x = setup.get('x', [round(i*size_x/grid_x) for i in range(grid_x+1)])
        y = setup.get('y', [round(i*size_y/grid_y) for i in range(grid_y+1)])
        width = min(b-a for a,b in zip(x,x[1:]))-2*inset
        height = min(b-a for a,b in zip(y,y[1:]))-2*inset
        if (len(x),len(y)) != (grid_x+1,grid_y+1) or min(width,height) < 55:
            raise ValueError(f'Invalid grid and inset: {shape}, {setup}')
        source_boxes = tuple((x[ix]+inset, y[iy]+inset, x[ix]+inset+width, y[iy]+inset+height)
                             for iy in range(grid_y) for ix in range(grid_x))
        return cls(grid_x,grid_y,inset,width,height,source_boxes)

    @property
    def x(self):
        return [i*(self.width+2*self.inset) for i in range(self.columns+1)]

    @property
    def y(self):
        return [i*(self.height+2*self.inset) for i in range(self.rows+1)]

    def output_box(self, i):
        col,row = i % self.columns,i // self.columns
        return self.x[col]+self.inset,self.y[row]+self.inset,self.x[col+1]-self.inset,self.y[row+1]-self.inset

    def frames(self, art):
        return [art[y0:y1,x0:x1].copy() for x0,y0,x1,y1 in self.source_boxes]

    def assemble(self, exposures):
        out = np.zeros((self.y[-1],self.x[-1],3),np.uint8)
        for i,exposure in enumerate(exposures):
            col,row = i % self.columns,i // self.columns
            # Duplicate only the discarded gutter pixels to keep the atlas opaquely padded.
            pad = ((self.inset,self.inset),(self.inset,self.inset),(0,0))
            out[self.y[row]:self.y[row+1],self.x[col]:self.x[col+1]] = np.pad(exposure,pad,mode='edge')
        return out


def guard_mask(shape, rectangles):
    h,w = shape[:2]
    mask = np.zeros((h,w),np.uint8)
    for a,b,c,d in rectangles:
        mask[int(b*h):int(np.ceil(d*h)),int(a*w):int(np.ceil(c*w))] = 1
    return cv2.dilate(mask,np.ones((11,11),np.uint8)) != 0


def gray(image):
    return cv2.cvtColor(image,cv2.COLOR_RGB2GRAY)


def registration_features(reference, distance):
    safe = distance > PATCH_RADIUS + SEARCH_RADIUS + FEATHER_PX + 2
    border = PATCH_RADIUS + SEARCH_RADIUS + 3
    safe[:border] = safe[-border:] = False
    safe[:,:border] = safe[:,-border:] = False
    corners = cv2.goodFeaturesToTrack(reference,100,.007,13,mask=np.uint8(safe),blockSize=5)
    return [] if corners is None else [tuple(p) for p in np.rint(corners[:,0,:]).astype(int)]


def quadratic_peak(before, at, after):
    denominator = before - 2*at + after
    if abs(denominator)<1e-8:
        return 0.
    return float(np.clip(.5*(before-after)/denominator,-.5,.5))


def estimate_shift(reference, moving, points):
    patch,search = PATCH_RADIUS,SEARCH_RADIUS
    outer = patch + search
    matches = []
    for x,y in points:
        tile = reference[y-patch:y+patch+1,x-patch:x+patch+1]
        scan = moving[y-outer:y+outer+1,x-outer:x+outer+1]
        scores = cv2.matchTemplate(scan,tile,cv2.TM_CCOEFF_NORMED)
        _,peak,_,(i,j) = cv2.minMaxLoc(scores)
        if peak < .83 or min(i,j)==0 or max(i,j)==2*search:
            continue
        runner = scores.copy()
        runner[j-1:j+2,i-1:i+2] = -1.
        if peak-float(runner.max())<.021:
            continue
        u = quadratic_peak(scores[j,i-1],scores[j,i],scores[j,i+1])
        v = quadratic_peak(scores[j-1,i],scores[j,i],scores[j+1,i])
        matches.append((i+u-search,j+v-search))
    if len(matches)<7:
        return np.zeros(2),len(matches),0
    observations = np.array(matches)
    distances = np.linalg.norm(observations[:,None]-observations[None,:],axis=2)
    inliers = distances[int(np.argmax((distances < .78).sum(axis=1)))] < .78
    count = int(inliers.sum())
    if count < max(7,len(matches)*.45):
        return np.zeros(2),len(matches),count
    return np.median(observations[inliers],axis=0),len(matches),count


def shift_image(image, shift):
    h,w = image.shape[:2]
    dx,dy = shift
    return cv2.getRectSubPix(image,(w,h),((w-1)*.5+float(dx),(h-1)*.5+float(dy)))


def mean_delta(left, right, region):
    return float(np.abs(left[region].astype(np.int16)-right[region].astype(np.int16)).mean())


def stabilize(reference, exposures, protected, feather_px):
    distance = cv2.distanceTransform(np.uint8(~protected),cv2.DIST_L2,5)
    with_margin = distance > feather_px
    box_alpha = (1.0-np.clip(distance/feather_px,0.,1.)).astype(np.float32)
    feather = (distance>0.) & ~with_margin
    if np.count_nonzero(with_margin)<reference.shape[0]*reference.shape[1]*.15:
        raise ValueError('Less than 15% trustworthy stationary exterior')
    ref_gray = gray(reference)
    ref_structure = cv2.GaussianBlur(reference.astype(np.float32),(7,7),1.4)
    anchors = registration_features(ref_gray,distance)
    outputs, details = [],[]
    for index,original in enumerate(exposures):
        moving_gray = gray(original)
        suggested,samples,inliers = estimate_shift(ref_gray,moving_gray,anchors) if index else (np.zeros(2),0,0)
        aligned = original
        used = np.zeros(2)
        before = mean_delta(reference,original,with_margin)
        if .14 < np.linalg.norm(suggested) <= SEARCH_RADIUS:
            candidate = shift_image(original,suggested)
            after = mean_delta(reference,candidate,with_margin)
            if after + max(.028,before*.012) < before:
                aligned,used = candidate,suggested
        after_registration = mean_delta(reference,aligned,with_margin)
        per_pixel = np.abs(aligned.astype(np.int16)-reference.astype(np.int16)).mean(axis=2)
        structure = cv2.GaussianBlur(aligned.astype(np.float32),(7,7),1.4)
        coarse_error = np.abs(ref_structure-structure).mean(axis=2)
        coherent = cv2.erode(np.uint8(per_pixel>35.),np.ones((3,3),np.uint8))
        belt_error = float(np.percentile(per_pixel[feather],95))
        structure_error = float(np.percentile(coarse_error[feather],95))
        coherent_rate = float(coherent[feather].mean())
        # Subpixel texture differences can be large at a single grout or leaf edge.
        # Reject coherent shifts near the cast, and keep that source cel untouched.
        compatible = index==0 or (structure_error < 18.0 and coherent_rate < .025 and after_registration < 15.0)
        state = 'locked' if compatible else 'retained source at incompatible boundary'
        if compatible:
            result = aligned.copy()
            result[with_margin] = reference[with_margin]
            a = box_alpha[feather,None]
            result[feather] = np.rint(aligned[feather]*a+reference[feather]*(1.-a)).astype(np.uint8)
            if not (np.array_equal(result[protected],aligned[protected]) and np.array_equal(result[with_margin],reference[with_margin])):
                raise RuntimeError('Protected cast or stationary equality failed')
        else:
            result,used = original,np.zeros(2)
        outputs.append(result)
        details.append({'cell':index,'status':state,'source_shift_xy_px':[float(v) for v in used],
                        'candidate_shift_xy_px':[float(v) for v in suggested],
                        'background_features':samples,'consensus_features':inliers,
                        'static_mean_rgb_error_before':round(before,4),
                        'static_mean_rgb_error_aligned':round(after_registration,4),
                        'static_mean_rgb_error_output':round(mean_delta(reference,result,with_margin),4),
                        'boundary_p95_rgb_error':round(belt_error,4),
                        'boundary_structure_p95':round(structure_error,4),'boundary_coherent_rate':round(coherent_rate,5),
                        'protected_pixels_equal':bool(np.array_equal(result[protected],shift_image(original,used)[protected]) if np.linalg.norm(used) else np.array_equal(result[protected],original[protected]))})
    return outputs,details,dict(protected_pixels=int(protected.sum()),locked_pixels=int(with_margin.sum()),
                                feather_pixels=int(feather.sum()),reference_anchors=len(anchors))


def preview(path, key, originals, outputs, record):
    w,h = 309,174
    margin = 12
    row_h = h+26
    board = Image.new('RGB',(2*w+3*margin,(len(outputs)+1)*row_h),'#25313a')
    draw = ImageDraw.Draw(board)
    font = ImageFont.load_default(size=14)
    draw.text((margin,14),f'{key}  ·  Original',fill='white',font=font)
    draw.text((2*margin+w,14),'Stationary plate registered to cell 0',fill='white',font=font)
    for index,(before,after,meta) in enumerate(zip(originals,outputs,record['cells'])):
        y = 42+index*row_h
        for col, pixels in enumerate((before,after)):
            frame = ImageOps.fit(Image.fromarray(pixels),(w,h),Image.Resampling.LANCZOS)
            board.paste(frame,(margin+col*(w+margin),y))
        dx,dy = meta['source_shift_xy_px']
        draw.text((margin,y+h+3),f'Cell {index}  ·  RGB drift {meta["static_mean_rgb_error_before"]:.2f}',fill='white',font=font)
        draw.text((margin*2+w,y+h+3),f'{meta["status"]}  ·  ({dx:+.2f}, {dy:+.2f}) px',fill='white',font=font)
    board.crop((0,0,board.width,58+len(outputs)*row_h)).save(path,quality=88,optimize=True)


def process(key, setup, source, target):
    file = source / setup['file']
    with Image.open(file) as art:
        original = np.asarray(art.convert('RGB'))
    grid = TileGrid.read(original.shape,setup)
    sources = grid.frames(original)
    protected = guard_mask(sources[0].shape,GUARDS[key])
    outputs, details, counts = stabilize(sources[0],sources,protected,FEATHER_PX)
    atlas = grid.assemble(outputs)
    descriptor = dict(setup,file=f'{key}.png',x=grid.x,y=grid.y,inset=grid.inset)
    record = {'descriptor':descriptor,'source_file':str(file),'source_sha256':hashlib.sha256(file.read_bytes()).hexdigest(),
              'reference_cell':0,'source_size':[original.shape[1],original.shape[0]],'output_size':[atlas.shape[1],atlas.shape[0]],
              'working_cell_size':[grid.width,grid.height],'source_boxes':grid.source_boxes,
              'output_boxes':[grid.output_box(i) for i in range(len(sources))],
              'cast_guard_normalized':GUARDS[key],'dilated_guard_px':5,'feather_px':FEATHER_PX,'cells':details,**counts}
    destination = target/descriptor['file']
    temporary = destination.with_suffix('.tmp')
    try:
        Image.fromarray(atlas).save(temporary,format='PNG',optimize=True)
        current_bytes = sum(p.stat().st_size for p in target.rglob('*') if p.is_file() and p not in (temporary,destination))
        if current_bytes+temporary.stat().st_size > OUTPUT_LIMIT:
            raise RuntimeError('40 MiB output capacity would be exceeded')
        with Image.open(temporary) as check:
            if not np.array_equal(np.asarray(check),atlas):
                raise RuntimeError('Saved atlas differs from verified cels')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    preview(target/'review'/f'{key}.jpg',key,sources,outputs,record)
    locked = sum(cell['status']=='locked' for cell in details)
    print(f'{key}: {locked}/{len(outputs)} locked, background {counts["locked_pixels"]/(grid.width*grid.height):.1%}, '
          f'{destination.stat().st_size/MIB:.2f} MiB',flush=True)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('names',nargs='*',help='Dialogue sheet keys. Default is the four requested examples.')
    parser.add_argument('--all',action='store_true',help='Process every dialogue sheet in the supplied manifest.')
    parser.add_argument('--manifest',type=Path,default=SOURCE/'whole-scene.json')
    parser.add_argument('--art',type=Path,help='Original art folder. Defaults to assets/whole-scene next to the manifest.')
    parser.add_argument('--output',type=Path,default=DEFAULT_OUT)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    catalog = manifest['sheets']
    keys = [key for key in catalog if key.startswith('dlg-')] if args.all else list(args.names or INITIAL)
    unknown = [key for key in keys if key not in catalog or key not in GUARDS]
    if unknown:
        parser.error(f'No verified cast bounds for: {", ".join(unknown)}')
    source = (args.art or args.manifest.parent/'assets'/'whole-scene').resolve()
    output = args.output.resolve()
    if source == output or output.is_relative_to(source):
        parser.error('The original art directory must be preserved. Choose a separate output directory.')
    (output/'review').mkdir(parents=True,exist_ok=True)
    index = output/'index.json'
    if index.is_file():
        report = json.loads(index.read_text())
    else:
        report = {'method':'Opaque full-camera cels. Entire tile translation only. Reference cell 0 locks the static room exterior.',
                  'source_manifest':str(args.manifest.resolve()),'sheets':{}}
    cv2.setNumThreads(1)
    for key in keys:
        report['sheets'][key] = process(key,catalog[key],source,output)
        pending = index.with_suffix('.tmp')
        pending.write_text(json.dumps(report,indent=2)+'\n')
        pending.replace(index)
    print(f'Wrote {index}',flush=True)


if __name__=='__main__':
    main()
