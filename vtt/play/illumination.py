"""Wall-clipped 2D illumination. Only final RGBA projections leave the server."""
import base64
import io
import math
from functools import lru_cache
from vtt.play.vision import token_world_xy
from PIL import Image, ImageDraw, ImageChops, ImageOps


def wall_key(walls, kind):
    return tuple((float(w.x0),float(w.y0),float(w.x1),float(w.y1)) for w in walls
                 if getattr(w, kind, 'normal') != 'none')


@lru_cache(maxsize=128)
def polygon(x, y, radius, walls):
    radius = max(0.0, min(float(radius), 12000.0))
    if not radius:
        return ((x,y),)
    angles = {i*math.tau/128 for i in range(128)}
    for x0,y0,x1,y1 in walls:
        for wx,wy in [(x0,y0),(x1,y1)]:
            angle=math.atan2(wy-y,wx-x)
            angles.update([(angle-1e-6)%math.tau,angle%math.tau,(angle+1e-6)%math.tau])
    points=[]
    for angle in sorted(angles):
        dx,dy=math.cos(angle),math.sin(angle);distance=radius
        for x0,y0,x1,y1 in walls:
            ex,ey=x1-x0,y1-y0;denom=dx*ey-dy*ex
            if abs(denom)<1e-10:continue
            qx,qy=x0-x,y0-y
            t=(qx*ey-qy*ex)/denom;u=(qx*dy-qy*dx)/denom
            if 0<=t<distance and 0<=u<=1:distance=t
        points.append((x+dx*distance,y+dy*distance))
    return tuple(points)


def light_reaches(light, x, y, walls):
    """Independent light-to-point segment, including sight-transparent light barriers."""
    ox,oy=float(light.x),float(light.y);dx,dy=x-ox,y-oy
    for x0,y0,x1,y1 in wall_key(walls, 'light'):
        ex,ey=x1-x0,y1-y0;denom=dx*ey-dy*ex
        if abs(denom)<1e-10:continue
        qx,qy=x0-ox,y0-oy
        t=(qx*ey-qy*ex)/denom;u=(qx*dy-qy*dx)/denom
        if 1e-7<t<1-1e-7 and 0<=u<=1:return False
    return True


def _mask(size, points, scale):
    mask=Image.new('L',size,0)
    if len(points)>=3:ImageDraw.Draw(mask).polygon([(round(x*scale),round(y*scale)) for x,y in points],fill=255)
    return mask


def _radial(size, x, y, bright, dim, scale):
    # Affine sampling keeps memory bounded by the projection, even for a light
    # whose radius is many times larger than the map.
    radius=max(bright,dim,1)
    gradient=ImageOps.invert(Image.radial_gradient('L'))
    inner=min(1.0,bright/radius)
    gradient=gradient.point([255 if (1-v/255)<=inner else round(max(0,(v/255)/(max(1e-6,1-inner)))*255) for v in range(256)])
    factor=127.5/(radius*scale)
    return gradient.transform(size,Image.Transform.AFFINE,
        (factor,0,127.5-x*scale*factor,0,factor,127.5-y*scale*factor),
        Image.Resampling.BILINEAR,fillcolor=0)


def render_overlay(width, height, walls, lights, tokens, *, ambient=25, explored=(), grid_size=32, fog_enabled=False):
    scale=min(1.0,1024/max(width,height,1));size=(max(1,round(width*scale)),max(1,round(height*scale)))
    sight_walls=wall_key(walls,'sight');light_walls=wall_key(walls,'light')
    light_field=Image.new('L',size,0);vision_light_field=Image.new('L',size,0);darkness=Image.new('L',size,0)
    for light in lights:
        radius=max(light.bright_radius or 0,light.dim_radius or 0)
        if radius<=0:continue
        clip=_mask(size,polygon(light.x,light.y,radius,() if light.light_type=='darkness' else light_walls),scale)
        if light.light_type=='darkness':darkness=ImageChops.lighter(darkness,clip);continue
        field=ImageChops.multiply(_radial(size,light.x,light.y,light.bright_radius or 0,light.dim_radius or 0,scale),clip)
        light_field=ImageChops.lighter(light_field,field)
        if light.provides_vision:vision_light_field=ImageChops.lighter(vision_light_field,field)
    view=Image.new('L',size,0);natural=Image.new('L',size,0)
    for token in tokens:
        tx,ty=token_world_xy(token,grid_size)
        sight=token.sight_range if token.sight_range is not None else 4000
        effective=max([sight]+[math.hypot(light.x-tx,light.y-ty)+max(light.bright_radius or 0,light.dim_radius or 0) for light in lights if light.provides_vision and light.light_type=='light'])
        view=ImageChops.lighter(view,_mask(size,polygon(tx,ty,min(effective,12000),sight_walls),scale))
        natural=ImageChops.lighter(natural,_mask(size,polygon(tx,ty,sight,sight_walls),scale))
    allowed=ImageChops.lighter(natural,ImageChops.multiply(view,vision_light_field.point(lambda v:255 if v else 0)))
    allowed=ImageChops.subtract(allowed,darkness)
    brightness=ImageChops.lighter(light_field,Image.new('L',size,round(255*max(0,min(100,ambient))/100)))
    brightness=ImageChops.multiply(brightness,allowed)
    if fog_enabled and explored:
        old=Image.new('L',size,0);draw=ImageDraw.Draw(old)
        for col,row in explored:
            draw.rectangle((round(col*grid_size*scale),round(row*grid_size*scale),round((col+1)*grid_size*scale),round((row+1)*grid_size*scale)),fill=24)
        brightness=ImageChops.lighter(brightness,old)
    overlay=Image.new('RGBA',size,(0,0,0,255));overlay.putalpha(ImageOps.invert(brightness))
    stream=io.BytesIO();overlay.save(stream,format='PNG',optimize=True)
    return 'data:image/png;base64,'+base64.b64encode(stream.getvalue()).decode()
