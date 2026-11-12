"""Private world authoring, explicit grants, bounded leases and reader-only snapshots."""
import base64
from copy import deepcopy
from datetime import timedelta
import io
import json
from uuid import uuid4
import zipfile
from flask import Blueprint,current_app,g,jsonify,request,send_file
from flask_jwt_extended import jwt_required
from sqlalchemy import or_,select
from vtt import atlas_domain as domain
from vtt.atlas_domain import AtlasError,need
from vtt.extensions import db,limiter
from vtt.models import User
from vtt.models.atlas import AtlasWorld,AtlasMember,AtlasMap,AtlasPublication
from vtt.models.mapmaker_project import MapmakerProject
from vtt.endpoints.mapmaker import adjust_quota,LibraryError
from vtt.security import current_user
from vtt.storage import get_storage_adapter
from vtt.utils.time import utcnow

atlas_bp=Blueprint('atlas',__name__,url_prefix='/api/atlas')

@atlas_bp.before_request
@jwt_required()
def authenticated():
    need(bool(current_user),'Bitte erneut anmelden.',401,'authentication_required')
    g.atlas_actor=current_user.id;g.atlas_new=[];g.atlas_old=[];g.atlas_committed=False

@atlas_bp.after_request
def private(response):
    response.headers['Cache-Control']='private, no-store';response.headers['X-Content-Type-Options']='nosniff'
    return response

@atlas_bp.teardown_request
def compensate(_error):
    keys=g.get('atlas_old',[]) if g.get('atlas_committed') else g.get('atlas_new',[])
    for key,provider in keys:
        try:adapter(provider).delete(key)
        except Exception:current_app.logger.warning('Atlas scoped object cleanup pending',extra={'key':key})

@atlas_bp.errorhandler(AtlasError)
@atlas_bp.errorhandler(LibraryError)
def error_response(error):
    db.session.rollback();return jsonify(error=str(error),code=error.code),error.status

def body():
    need(request.content_length is None or request.content_length<=domain.MAX_BACKUP,'Die Anfrage ist zu groß.',413)
    data=request.get_json(silent=True);need(isinstance(data,dict),'JSON-Objekt erwartet.');return data

def adapter(provider=None):
    need(not provider or provider==current_app.config.get('STORAGE_PROVIDER','local'),'Der Speicheranbieter ist nicht verfügbar.',503,'storage_unavailable')
    return get_storage_adapter()

def read_object(row):
    try:return json.loads(adapter(row.storage_provider).download(row.storage_key))
    except AtlasError:raise
    except Exception:raise AtlasError('Die gespeicherte Karte ist momentan nicht erreichbar.',503,'storage_unavailable')

def upload(world,data):
    payload=domain.encoded(data);provider=current_app.config.get('STORAGE_PROVIDER','local')
    key=f'users/{world.owner_id}/atlas/{world.id}/{uuid4()}.json'
    g.atlas_new.append((key,provider))
    try:adapter(provider).upload(key,payload)
    except Exception:raise AtlasError('Der Atlas konnte nicht gespeichert werden.',503,'storage_unavailable')
    return key,provider,len(payload)

def old_object(row):g.atlas_old.append((row.storage_key,row.storage_provider))

def role(world):
    actor=db.session.get(User,g.atlas_actor,populate_existing=True)
    owner=db.session.get(User,world.owner_id,populate_existing=True)
    if actor is None or not actor.is_usable() or owner is None or not owner.is_usable():return None
    if world.owner_id==actor.id:return 'owner'
    member=db.session.get(AtlasMember,(world.id,actor.id),populate_existing=True)
    return member.role if member and member.role in ('editor','reader') else None

def access(identity,write=False,owner=False):
    world=db.session.get(AtlasWorld,str(identity),populate_existing=True)
    permission=role(world) if world else None
    need(permission is not None,'Welt nicht gefunden.',404,'not_found')
    need(not write or permission in ('owner','editor'),'Welt nicht gefunden.',404,'not_found')
    need(not owner or permission=='owner','Welt nicht gefunden.',404,'not_found')
    return world,permission

def lock_users(ids):
    for identity in sorted(set(ids)):
        db.session.execute(db.update(User).where(User.id==identity).values(storage_used_gb=db.func.coalesce(User.storage_used_gb,0.0)))
    actor=db.session.get(User,g.atlas_actor,populate_existing=True)
    need(actor is not None and actor.is_usable(),'Bitte erneut anmelden.',401,'authentication_required')

def writing(identity,owner=False):
    initial,_=access(identity,write=True,owner=owner)
    lock_users([initial.owner_id,g.atlas_actor])
    world=db.session.get(AtlasWorld,initial.id,with_for_update=True,populate_existing=True)
    need(world is not None,'Welt nicht gefunden.',404,'not_found')
    permission=role(world)
    need(permission in (('owner',) if owner else ('owner','editor')),'Welt nicht gefunden.',404,'not_found')
    return world

def cas(world,data):need(type(data.get('revision'))is int and data['revision']==world.revision,'Der Atlas wurde inzwischen geändert. Sichere deine Eingaben und lade den aktuellen Stand.',409,'revision_conflict')

def maps_for(world):return AtlasMap.query.filter_by(world_id=world.id).order_by(AtlasMap.id).all()
def dimensions(rows):return {row.id:{'width':row.width,'height':row.height} for row in rows}
def publication(world):return AtlasPublication.query.filter_by(world_id=world.id).first()
def total(world):return world.graph_bytes+sum(row.size_bytes for row in maps_for(world))+(publication(world).size_bytes if publication(world) else 0)
def reserve(world,delta):
    need(total(world)+delta<=domain.MAX_BACKUP-65536,'Der Atlas überschreitet 64 MiB. Sichere oder verkleinere ihn.',413,'world_too_large')
    adjust_quota(db.session.get(User,world.owner_id,populate_existing=True),delta)
def changed(world):world.revision+=1;world.updated_at=utcnow()
def commit():db.session.commit();g.atlas_committed=True

def map_row(world,identity):
    row=db.session.get(AtlasMap,str(identity),populate_existing=True)
    need(row is not None and row.world_id==world.id,'Karte nicht gefunden.',404,'not_found');return row

def map_info(row):return dict(id=row.id,revision=row.revision,width=row.width,height=row.height)

def draft_response(world):
    permission=role(world);rows=maps_for(world)
    members=[]
    if permission=='owner':
        members=[dict(user_id=m.user_id,username=u.username,role=m.role) for m,u in db.session.query(AtlasMember,User).join(User,User.id==AtlasMember.user_id).filter(AtlasMember.world_id==world.id).order_by(User.username)]
    return dict(id=world.id,revision=world.revision,role=permission,graph=world.graph,maps=[map_info(row) for row in rows],members=members)

def make_projection(world):
    rows=maps_for(world);info=dimensions(rows)
    for row in rows:info[row.id]['credits']=read_object(row)['credits']
    return domain.projection(world.graph,info)

@atlas_bp.get('/worlds')
def worlds():
    after=request.args.get('after')
    if after:after=domain.uid(after)
    query=AtlasWorld.query.filter(or_(AtlasWorld.owner_id==g.atlas_actor,AtlasWorld.id.in_(select(AtlasMember.world_id).where(AtlasMember.user_id==g.atlas_actor))))
    if after:query=query.filter(AtlasWorld.id>after)
    rows=query.order_by(AtlasWorld.id).limit(51).all();result=[]
    for world in rows[:50]:
        permission=role(world)
        if not permission:continue
        pub=publication(world)
        result.append(dict(id=world.id,role=permission,title=world.graph['title'] if permission!='reader' else pub.projection['title'] if pub else None,published=pub is not None))
    return jsonify(worlds=result,next_cursor=rows[49].id if len(rows)>50 else None)

@atlas_bp.post('/worlds')
@limiter.limit('30 per hour')
def create_world():
    data=body();lock_users([g.atlas_actor]);need(AtlasWorld.query.filter_by(owner_id=g.atlas_actor).count()<20,'Höchstens 20 eigene Welten erlaubt.',409)
    graph=domain.graph(dict(title=data.get('title'),summary='',private_lore='',places=[],maps=[]),{})
    size=len(domain.encoded(graph));world=AtlasWorld(id=str(uuid4()),owner_id=g.atlas_actor,graph=graph,graph_bytes=0,revision=1)
    db.session.add(world);db.session.flush();reserve(world,size);world.graph_bytes=size;commit();return jsonify(draft_response(world)),201

@atlas_bp.get('/worlds/<uuid:identity>/context')
def world_context(identity):
    world,permission=access(identity);return jsonify(id=world.id,role=permission)

@atlas_bp.get('/worlds/<uuid:identity>')
def draft(identity):
    world,_=access(identity,write=True);return jsonify(draft_response(world))

@atlas_bp.put('/worlds/<uuid:identity>')
def save_graph(identity):
    data=body();world=writing(identity);cas(world,data);graph=domain.graph(data.get('graph'),dimensions(maps_for(world)));size=len(domain.encoded(graph))
    reserve(world,size-world.graph_bytes);world.graph=graph;world.graph_bytes=size;changed(world);commit();return jsonify(draft_response(world))

@atlas_bp.put('/worlds/<uuid:identity>/members')
def grant(identity):
    data=body();world=writing(identity,owner=True);cas(world,data)
    username=domain.text(data.get('username'),80,True);permission=data.get('role');need(permission in ('editor','reader',None))
    target=User.query.filter_by(username=username).first();need(target is not None and target.is_usable(),'Konto nicht gefunden.',404)
    need(target.id!=world.owner_id,'Der Weltbesitzer bleibt Besitzer.',409)
    member=db.session.get(AtlasMember,(world.id,target.id),populate_existing=True)
    if permission is None:
        if member:db.session.delete(member)
        for row in maps_for(world):
            if row.lease_user_id==target.id:row.lease_user_id=None;row.lease_tab=None;row.lease_expires=None
    else:
        need(member is not None or AtlasMember.query.filter_by(world_id=world.id).count()<32,'Höchstens 32 Freigaben erlaubt.',409)
        if member:member.role=permission
        else:db.session.add(AtlasMember(world_id=world.id,user_id=target.id,role=permission))
        if permission=='reader':
            for row in maps_for(world):
                if row.lease_user_id==target.id:row.lease_user_id=None;row.lease_tab=None;row.lease_expires=None
    changed(world);commit();return jsonify(draft_response(world))

@atlas_bp.post('/worlds/<uuid:identity>/maps')
def attach(identity):
    data=body();world=writing(identity);cas(world,data);rows=maps_for(world);need(len(rows)<12,'Höchstens zwölf Karten pro Welt erlaubt.',409)
    source=db.session.get(MapmakerProject,domain.uid(data.get('project_id')),with_for_update=True,populate_existing=True)
    need(source is not None and source.owner_id==g.atlas_actor,'Eigene Bibliothekskarte nicht gefunden.',404)
    need(type(data.get('project_revision'))is int and source.revision==data['project_revision'],'Die Bibliothekskarte hat sich geändert. Vorschau neu öffnen.',409,'revision_conflict')
    raw=read_object(source);bundle=domain.bundle(dict(document=raw,png=data.get('png'),credits=data.get('credits')))
    size=len(domain.encoded(bundle));new_id=str(uuid4());graph=deepcopy(world.graph);graph['maps'].append(dict(id=new_id,title=source.title,reader_visible=False,km_per_pixel=None))
    graph_size=len(domain.encoded(graph));reserve(world,size+graph_size-world.graph_bytes)
    key,provider,size=upload(world,bundle);row=AtlasMap(id=new_id,world_id=world.id,revision=1,width=source.width,height=source.height,storage_key=key,storage_provider=provider,size_bytes=size)
    db.session.add(row);world.graph=graph;world.graph_bytes=graph_size;changed(world);commit();return jsonify(world=draft_response(world),map_id=row.id),201

@atlas_bp.get('/worlds/<uuid:identity>/maps/<uuid:map_id>')
def get_map(identity,map_id):
    world,_=access(identity,write=True);row=map_row(world,map_id);return jsonify(map=map_info(row),bundle=read_object(row))

@atlas_bp.get('/worlds/<uuid:identity>/maps/<uuid:map_id>.png')
def draft_image(identity,map_id):
    world,_=access(identity,write=True);row=map_row(world,map_id);return image_response(read_object(row)['png'])

def image_response(value):return send_file(io.BytesIO(base64.b64decode(value.split(',',1)[1])),mimetype='image/png',max_age=0)

def lease_ok(row,tab):return row.lease_user_id==g.atlas_actor and row.lease_tab==tab and row.lease_expires and row.lease_expires>utcnow()

@atlas_bp.post('/worlds/<uuid:identity>/maps/<uuid:map_id>/lease')
def lease(identity,map_id):
    data=body();tab=domain.uid(data.get('tab'));world=writing(identity);row=map_row(world,map_id)
    need(not row.lease_expires or row.lease_expires<=utcnow() or lease_ok(row,tab),'Diese Karte wird bereits in einem anderen Fenster bearbeitet. Später erneut öffnen.',409,'lease_conflict')
    row.lease_user_id=g.atlas_actor;row.lease_tab=tab;row.lease_expires=utcnow()+timedelta(seconds=120);commit();return jsonify(expires_at=row.lease_expires.isoformat()+'Z',map=map_info(row))

@atlas_bp.delete('/worlds/<uuid:identity>/maps/<uuid:map_id>/lease')
def release_lease(identity,map_id):
    data=body();world=writing(identity);row=map_row(world,map_id);tab=domain.uid(data.get('tab'))
    if row.lease_user_id==g.atlas_actor and row.lease_tab==tab:row.lease_user_id=None;row.lease_tab=None;row.lease_expires=None
    commit();return jsonify(released=True)

@atlas_bp.put('/worlds/<uuid:identity>/maps/<uuid:map_id>')
def save_map(identity,map_id):
    data=body();world=writing(identity);row=map_row(world,map_id)
    need(lease_ok(row,domain.uid(data.get('tab'))),'Die Bearbeitungsfreigabe ist abgelaufen. Sichere die Datei und öffne die Karte neu.',409,'lease_lost')
    need(type(data.get('revision'))is int and data['revision']==row.revision,'Die Karte wurde inzwischen geändert.',409,'revision_conflict')
    bundle=domain.bundle(data.get('bundle'));need(bundle['document']['size']=={'w':row.width,'h':row.height},'Atlas-Kartengröße beim Bearbeiten beibehalten.',409)
    size=len(domain.encoded(bundle));reserve(world,size-row.size_bytes);key,provider,size=upload(world,bundle);old_object(row)
    row.storage_key,row.storage_provider,row.size_bytes=key,provider,size;row.revision+=1;changed(world);commit();return jsonify(map=map_info(row),world_revision=world.revision)

@atlas_bp.delete('/worlds/<uuid:identity>/maps/<uuid:map_id>')
def delete_map(identity,map_id):
    data=body();world=writing(identity);cas(world,data);row=map_row(world,map_id)
    need(not any(place['map_id']==row.id for place in world.graph['places']),'Löse zuerst die Ortsverweise auf diese Karte.',409)
    need(not row.lease_expires or row.lease_expires<=utcnow(),'Die Karte wird gerade bearbeitet.',409,'lease_conflict')
    graph=deepcopy(world.graph);graph['maps']=[item for item in graph['maps'] if item['id']!=row.id];size=len(domain.encoded(graph))
    reserve(world,size-world.graph_bytes-row.size_bytes);old_object(row);db.session.delete(row);world.graph=graph;world.graph_bytes=size;changed(world);commit();return jsonify(draft_response(world))

@atlas_bp.get('/worlds/<uuid:identity>/preview')
def preview(identity):
    world,_=access(identity,write=True);return jsonify(id=world.id,revision=world.revision,projection=make_projection(world))

@atlas_bp.post('/worlds/<uuid:identity>/publish')
def publish(identity):
    data=body();world=writing(identity,owner=True);cas(world,data);need(data.get('confirm_visible_pixels')is True,'Bitte die sichtbaren Kartenbilder ausdrücklich freigeben.',409)
    projection=make_projection(world);images={row.id:read_object(row)['png'] for row in maps_for(world) if any(item['id']==row.id for item in projection['maps'])}
    payload=dict(projection=projection,images=images);size=len(domain.encoded(payload));previous=publication(world);reserve(world,size-(previous.size_bytes if previous else 0))
    key,provider,size=upload(world,payload)
    if previous:old_object(previous);db.session.delete(previous);db.session.flush()
    pub=AtlasPublication(id=str(uuid4()),world_id=world.id,projection=projection,storage_key=key,storage_provider=provider,size_bytes=size);db.session.add(pub);changed(world);commit();return jsonify(id=pub.id,world_revision=world.revision,projection=pub.projection),201

@atlas_bp.get('/worlds/<uuid:identity>/published')
def published(identity):
    world,_=access(identity);pub=publication(world);need(pub is not None,'Diese Welt wurde noch nicht veröffentlicht.',409,'unpublished')
    return jsonify(id=world.id,publication_id=pub.id,projection=pub.projection)

@atlas_bp.get('/worlds/<uuid:identity>/published/maps/<uuid:map_id>.png')
def public_image(identity,map_id):
    world,_=access(identity);pub=publication(world)
    need(pub is not None and request.args.get('version')==pub.id and any(row['id']==str(map_id) for row in pub.projection['maps']),'Karte nicht gefunden.',404,'not_found')
    return image_response(read_object(pub)['images'][str(map_id)])

@atlas_bp.get('/worlds/<uuid:identity>/backup')
def backup(identity):
    world,_=access(identity,write=True);pub=publication(world)
    value=dict(format='rd-atlas',version=1,world_id=world.id,graph=world.graph,maps=[dict(id=row.id,bundle=read_object(row)) for row in maps_for(world)],publication=dict(id=pub.id,projection=pub.projection,images=read_object(pub)['images']) if pub else None)
    payload=domain.encoded(value);need(len(payload)<=domain.MAX_BACKUP,'Die Sicherung ist größer als 64 MiB.',413)
    if request.args.get('format')=='zip':
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED) as archive:archive.writestr('atlas.json',payload)
        payload=stream.getvalue();mime='application/zip';suffix='zip'
    else:mime='application/json';suffix='json'
    return send_file(io.BytesIO(payload),mimetype=mime,as_attachment=True,download_name=f'atlas-{world.id}.{suffix}',max_age=0)

@atlas_bp.delete('/worlds/<uuid:identity>')
def delete_world(identity):
    data=body();world=writing(identity,owner=True);cas(world,data);reserve(world,-total(world))
    for row in maps_for(world):old_object(row);db.session.delete(row)
    pub=publication(world)
    if pub:old_object(pub);db.session.delete(pub)
    AtlasMember.query.filter_by(world_id=world.id).delete(synchronize_session=False);db.session.flush();db.session.delete(world);commit();return jsonify(deleted=True)

def validated_publication(raw):
    if raw is None:return None
    need(isinstance(raw,dict) and set(raw)=={'id','projection','images'})
    identity=domain.uid(raw['id']);projection=raw['projection'];images=raw['images']
    need(isinstance(projection,dict) and set(projection)=={'title','summary','places','maps'} and isinstance(images,dict))
    need(isinstance(projection['maps'],list) and len(projection['maps'])<=12 and isinstance(projection['places'],list))
    info={};metadata=[];clean_images={}
    for row in projection['maps']:
        need(isinstance(row,dict) and set(row)=={'id','title','km_per_pixel','width','height','credits'})
        map_id=domain.uid(row['id']);need(map_id not in info and map_id in images)
        width=domain.integer(row['width'],256,4096);height=domain.integer(row['height'],256,4096);credits=domain.text(row['credits'],20000)
        info[map_id]=dict(width=width,height=height,credits=credits)
        metadata.append(dict(id=map_id,title=row['title'],reader_visible=True,km_per_pixel=row['km_per_pixel']))
        clean_images[map_id]=domain.png(images[map_id],width,height,credits)
    need(set(images)==set(info));places=[]
    for row in projection['places']:
        need(isinstance(row,dict) and set(row)=={'id','name','parent_id','map_id','x','y','lore','links'})
        places.append(row|dict(private_lore='',reader_visible=True))
    draft=domain.graph(dict(title=projection['title'],summary=projection['summary'],private_lore='',maps=metadata,places=places),info)
    return dict(id=identity,projection=domain.projection(draft,info),images=clean_images)

@atlas_bp.post('/restore')
@limiter.limit('20 per hour')
def restore():
    raw=domain.archive_read(request.stream.read(domain.MAX_BACKUP+1),request.mimetype=='application/zip')
    need(set(raw)=={'format','version','world_id','graph','maps','publication'})
    world_id=domain.uid(raw['world_id']);need(isinstance(raw['maps'],list) and len(raw['maps'])<=12)
    bundles={};info={}
    for item in raw['maps']:
        need(isinstance(item,dict) and set(item)=={'id','bundle'});map_id=domain.uid(item['id']);need(map_id not in bundles)
        bundles[map_id]=domain.bundle(item['bundle']);size=bundles[map_id]['document']['size'];info[map_id]=dict(width=size['w'],height=size['h'])
    graph=domain.graph(raw['graph'],info);pubdata=validated_publication(raw['publication'])
    existing=db.session.get(AtlasWorld,world_id)
    if existing:
        world=writing(world_id,owner=True)
        expected=request.headers.get('X-Atlas-Revision','')
        need(expected.isascii() and expected.isdigit() and len(expected)<12 and int(expected)==world.revision,'Für das Überschreiben ist die aktuelle Atlasrevision erforderlich.',409,'revision_conflict')
        previous_total=total(world);next_revision=world.revision+1
    else:
        lock_users([g.atlas_actor]);need(AtlasWorld.query.filter_by(owner_id=g.atlas_actor).count()<20,'Höchstens 20 eigene Welten erlaubt.',409)
        world=AtlasWorld(id=world_id,owner_id=g.atlas_actor,graph=graph,graph_bytes=0,revision=1);db.session.add(world);db.session.flush();previous_total=0;next_revision=1
    for map_id in bundles:
        collision=db.session.get(AtlasMap,map_id);need(collision is None or collision.world_id==world.id,'Eine Kartenkennung gehört bereits zu einer anderen Welt.',409)
    graph_size=len(domain.encoded(graph));pubpayload=dict(projection=pubdata['projection'],images=pubdata['images']) if pubdata else None
    target_size=graph_size+sum(len(domain.encoded(value)) for value in bundles.values())+(len(domain.encoded(pubpayload)) if pubpayload else 0)
    need(target_size<=domain.MAX_BACKUP-65536,'Der Atlas überschreitet 64 MiB.',413)
    reserve(world,target_size-previous_total)
    revisions={row.id:row.revision for row in maps_for(world)}
    for row in maps_for(world):old_object(row);db.session.delete(row)
    previous=publication(world)
    if previous:old_object(previous);db.session.delete(previous)
    db.session.flush()
    for map_id,value in bundles.items():
        key,provider,size=upload(world,value);dims=info[map_id]
        db.session.add(AtlasMap(id=map_id,world_id=world.id,revision=revisions.get(map_id,0)+1,width=dims['width'],height=dims['height'],storage_key=key,storage_provider=provider,size_bytes=size))
    if pubdata:
        key,provider,size=upload(world,pubpayload)
        db.session.add(AtlasPublication(id=str(uuid4()),world_id=world.id,projection=pubdata['projection'],storage_key=key,storage_provider=provider,size_bytes=size))
    world.graph=graph;world.graph_bytes=graph_size;world.revision=next_revision;world.updated_at=utcnow();commit();return jsonify(draft_response(world)),200 if existing else 201
