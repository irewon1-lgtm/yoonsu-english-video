from PIL import Image
import ctypes as C
import ctypes.util
def _lib(name):
    return C.CDLL(ctypes.util.find_library(name))
def _fn(lib,name,result,*args):
    func=getattr(lib,name);func.argtypes=args;func.restype=result;return func
_c=_lib('cairo');_r=_lib('rsvg-2');_g=_lib('gobject-2.0')
_ptr=C.c_void_p;_i=C.c_int
_surface=_fn(_c,'cairo_image_surface_create',_ptr,_i,_i,_i)
_context=_fn(_c,'cairo_create',_ptr,_ptr)
_read=_fn(_c,'cairo_image_surface_get_data',_ptr,_ptr)
_flush=_fn(_c,'cairo_surface_flush',None,_ptr)
_kill_ctx=_fn(_c,'cairo_destroy',None,_ptr)
_kill_surf=_fn(_c,'cairo_surface_destroy',None,_ptr)
_new_svg=_fn(_r,'rsvg_handle_new_from_data',_ptr,C.c_char_p,C.c_size_t,_ptr)
_svg_render=_fn(_r,'rsvg_handle_render_cairo',_i,_ptr,_ptr)
_unref=_fn(_g,'g_object_unref',None,_ptr)
def raster(svg,width,height=None):
    height=height or width
    data=svg.encode();handle=_new_svg(data,len(data),None)
    if not handle:raise ValueError('invalid SVG')
    surface=_surface(0,width,height);ctx=_context(surface)
    try:
        if not _svg_render(handle,ctx):raise ValueError('SVG render failed')
        _flush(surface)
        pixels=C.string_at(_read(surface),width*height*4)
        return Image.frombytes('RGBa',(width,height),pixels,'raw','BGRa').convert('RGBA')
    finally:
        _unref(handle);_kill_ctx(ctx);_kill_surf(surface)

