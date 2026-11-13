"""Pure bounded Atlas graph, image and archive validation; no access decisions here."""
import base64
import binascii
from copy import deepcopy
import io
import json
import math
from uuid import UUID
import zipfile
from PIL import Image,PngImagePlugin
from vtt.mapmaker_document import normalize_document,InvalidDocument

MIB=1024*1024
MAX_BACKUP=64*MIB
MAX_MAP=16*MIB
MAX_CREDITS=200000

class AtlasError(ValueError):
    def __init__(self,message,status=400,code='invalid_atlas'):
        super().__init__(message);self.status=status;self.code=code

def need(condition,message='Ungültige Atlas-Daten.',status=400,code='invalid_atlas'):
    if not condition:raise AtlasError(message,status,code)

def uid(value):
    try:
        need(isinstance(value,str) and len(value)==36);return str(UUID(value))
    except (ValueError,AttributeError):raise AtlasError('Ungültige Atlas-Kennung.')

def text(value,limit,required=False):
    need(isinstance(value,str) and len(value)<=limit and '\x00' not in value)
    try:value.encode('utf-8')
    except UnicodeError:raise AtlasError('Ungültiger Text.')
    need(not required or bool(value.strip()));return value

def integer(value,low=1,high=2**31-1):
    need(type(value)is int and low<=value<=high);return value

def number(value,low,high):
    need(type(value)in(int,float) and math.isfinite(value) and low<=value<=high);return value

def boolean(value):need(type(value)is bool);return value

def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8')

def graph(raw,maps):
    need(isinstance(raw,dict) and set(raw)=={'title','summary','private_lore','places','maps'})
    result={key:text(raw.get(key),limit,key=='title') for key,limit in [('title',80),('summary',2000),('private_lore',10000)]}
    need(isinstance(raw['maps'],list) and len(raw['maps'])<=12)
    result['maps']=[];seen=set()
    for row in raw['maps']:
        need(isinstance(row,dict) and set(row)=={'id','title','reader_visible','km_per_pixel'})
        identity=uid(row['id']);need(identity in maps and identity not in seen);seen.add(identity)
        scale=row['km_per_pixel']
        if scale is not None:number(scale,0.000000001,1000000)
        result['maps'].append(dict(id=identity,title=text(row['title'],80,True),reader_visible=boolean(row['reader_visible']),km_per_pixel=scale))
    need(seen==set(maps),'Die Kartenliste hat sich geändert. Bitte den Atlas neu laden.',409,'revision_conflict')
    need(isinstance(raw['places'],list) and len(raw['places'])<=256)
    places={};result['places']=[]
    for row in raw['places']:
        need(isinstance(row,dict) and set(row)=={'id','name','parent_id','map_id','x','y','lore','private_lore','reader_visible','links'})
        identity=uid(row['id']);need(identity not in places)
        parent=uid(row['parent_id']) if row['parent_id'] is not None else None
        map_id=uid(row['map_id']) if row['map_id'] is not None else None
        need(map_id is None or map_id in maps)
        x,y=row['x'],row['y']
        if map_id is None:need(x is None and y is None)
        elif x is not None or y is not None:
            dims=maps[map_id];number(x,0,dims['width']);number(y,0,dims['height'])
        need(isinstance(row['links'],list) and len(row['links'])<=32)
        links=[uid(link) for link in row['links']];need(len(links)==len(set(links)))
        clean=dict(id=identity,name=text(row['name'],120,True),parent_id=parent,map_id=map_id,x=x,y=y,
                   lore=text(row['lore'],10000),private_lore=text(row['private_lore'],10000),reader_visible=boolean(row['reader_visible']),links=links)
        places[identity]=clean;result['places'].append(clean)
    for row in places.values():
        need(row['parent_id'] is None or row['parent_id'] in places)
        need(all(link in places for link in row['links']))
        seen={row['id']};parent=row['parent_id']
        while parent:
            need(parent not in seen,'Orte dürfen keinen Hierarchiekreis bilden.');seen.add(parent);parent=places[parent]['parent_id']
    need(len(encoded(result))<=2*MIB,'Der Atlastext ist zu groß.',413)
    return result

def png(value,width,height,credits):
    need(isinstance(value,str) and value.startswith('data:image/png;base64,') and len(value)<=MAX_MAP*2)
    try:
        data=base64.b64decode(value.split(',',1)[1],validate=True)
        need(len(data)<=MAX_MAP)
        with Image.open(io.BytesIO(data)) as image:
            need(image.format=='PNG' and image.size==(width,height) and getattr(image,'n_frames',1)==1)
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            output=io.BytesIO();info=PngImagePlugin.PngInfo();info.add_text('Credits',credits)
            image.convert('RGBA').save(output,format='PNG',pnginfo=info)
    except (OSError,ValueError,binascii.Error,Image.DecompressionBombError) as error:
        raise AtlasError('Ungültiges Kartenbild.') from error
    return 'data:image/png;base64,'+base64.b64encode(output.getvalue()).decode('ascii')

def bundle(raw):
    need(isinstance(raw,dict) and set(raw)=={'document','png','credits'})
    credits=text(raw['credits'],MAX_CREDITS)
    try:document,_=normalize_document(raw['document'])
    except (InvalidDocument,OverflowError,RecursionError,UnicodeError) as error:raise AtlasError(str(error)) from error
    width,height=document['size']['w'],document['size']['h']
    result=dict(document=document,png=png(raw['png'],width,height,credits),credits=credits)
    need(len(encoded(result))<=MAX_MAP,'Diese Atlaskarte ist größer als 16 MiB.',413)
    return result

def projection(draft,maps):
    visible={row['id'] for row in draft['places'] if row['reader_visible']}
    public_maps={row['id'] for row in draft['maps'] if row['reader_visible']}
    out=dict(title=draft['title'],summary=draft['summary'],places=[],maps=[])
    for row in draft['places']:
        if row['id'] not in visible:continue
        need(row['parent_id'] is None or row['parent_id'] in visible,'Ein sichtbarer Ort hat einen privaten übergeordneten Ort.',409,'private_parent')
        need(row['map_id'] is None or row['map_id'] in public_maps,'Ein sichtbarer Ort verweist auf eine private Karte.',409,'private_map')
        clean={key:deepcopy(row[key]) for key in ['id','name','parent_id','map_id','x','y','lore']}
        clean['links']=[identity for identity in row['links'] if identity in visible];out['places'].append(clean)
    for row in draft['maps']:
        if row['id'] in public_maps:out['maps'].append({key:row[key] for key in ['id','title','km_per_pixel']}|maps[row['id']])
    return out

def archive_read(data,is_zip):
    need(len(data)<=MAX_BACKUP,'Die Sicherung ist größer als 64 MiB.',413)
    try:
        if is_zip:
            with zipfile.ZipFile(io.BytesIO(data)) as archive:
                entries=archive.infolist();need(len(entries)==1 and entries[0].filename=='atlas.json','Die ZIP-Sicherung muss genau atlas.json enthalten.')
                entry=entries[0];need(not entry.flag_bits&1 and entry.compress_type in (zipfile.ZIP_STORED,zipfile.ZIP_DEFLATED) and entry.file_size<=MAX_BACKUP)
                with archive.open(entry) as source:data=source.read(MAX_BACKUP+1)
                need(len(data)<=MAX_BACKUP,'Die entpackte Sicherung ist zu groß.',413)
        result=json.loads(data)
        need(isinstance(result,dict) and result.get('format')=='rd-atlas' and type(result.get('version'))is int and result['version']==1)
        return result
    except (zipfile.BadZipFile,RuntimeError,UnicodeError,ValueError,RecursionError) as error:
        if isinstance(error,AtlasError):raise
        raise AtlasError('Ungültige Atlas-Sicherung.') from error
