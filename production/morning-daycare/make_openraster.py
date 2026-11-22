"""Provide three layered, editable contact-stage files for Krita/GIMP."""
from pathlib import Path
from io import BytesIO
from xml.etree.ElementTree import Element,SubElement,tostring
from zipfile import ZipFile,ZIP_STORED,ZIP_DEFLATED
from PIL import Image
from exposures import action,ROOT

def png(im):
    data=BytesIO()
    im.save(data,'PNG')
    return data.getvalue()

def stage(key,n,label):
    c=action(key)
    with Image.open(c.plate_at(n)) as bg:
        plate=bg.convert('RGBA').resize((1280,720),Image.Resampling.LANCZOS)
    with Image.open(c.path_at(n)) as src:
        im=src.convert('RGBA')
    x,y,w,h=c.dest
    x,y,w,h=round(x*1280),round(y*720),round(w*1280),round(h*720)
    actor=im.resize((w,h),Image.Resampling.LANCZOS)
    merged=plate.copy()
    merged.alpha_composite(actor,(x,y))
    info=Element('image',dict(w='1280',h='720',name=label,version='0.0.3'))
    layers=SubElement(info,'stack')
    positions=[('Action · '+label,'data/action.png',actor,x,y),
               ('Photographic set','data/plate.png',plate,0,0)]
    d=ROOT/'editor';d.mkdir(exist_ok=True)
    out=d/f'{key}.ora'
    with ZipFile(out,'w') as z:
        z.writestr('mimetype','image/openraster',compress_type=ZIP_STORED)
        for name,path,image,x,y in positions:
            SubElement(layers,'layer',dict(name=name,src=path,x=str(x),y=str(y),opacity='1.0',
                                           visibility='visible',**{'composite-op':'svg:src-over'}))
            z.writestr(path,png(image),compress_type=ZIP_STORED)
        z.writestr('stack.xml',tostring(info,encoding='utf-8'),compress_type=ZIP_DEFLATED)
        z.writestr('mergedimage.png',png(merged),compress_type=ZIP_STORED)
        merged.thumbnail((256,256))
        z.writestr('Thumbnails/thumbnail.png',png(merged),compress_type=ZIP_STORED)
    with ZipFile(out) as z:
        assert z.testzip() is None
    print(out.relative_to(ROOT))
if __name__=='__main__':
    for key,n,label in [('wake',101,'Both feet touch'),('shoes',51,'Heel seats'),('depart',136,'Second loop takes the arm')]:
        stage(key,n,label)
