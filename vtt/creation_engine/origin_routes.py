"""Playable Background/Feat check and immutable publication beside Eagle authoring."""
import copy
from flask import current_app,jsonify,request
from sqlalchemy.exc import IntegrityError
from vtt.extensions import db,limiter
from vtt.models import CeRuleRevision
from vtt.characters import origin_catalog
from vtt.rules_content.creator_rules import load_creator_data
from vtt.rules_content.origin_profiles import parse_id
from . import origins
from .canonical import content_digest
from .documents import RequestFailure
from .routes import blueprint,current_user,resolve_world,scope_of,find,read_failure
from .species_routes import _digest,_lineage


def error(code,detail,status=422,**extra):return jsonify(error=code,detail=detail,**extra),status


def inspect_request(user):
    if not current_app.config.get('CE_PLAYABLE_ORIGINS'):return None,error('not-found','Hintergründe/Merkmale sind nicht eingeschaltet.',404)
    if (request.content_length or 0)>70000:return None,error('too-large','Anfrage zu groß.',413)
    body=request.get_json(silent=True)
    if not isinstance(body,dict):return None,error('invalid-request','JSON-Objekt erwartet.',400)
    try:
        world=resolve_world(user,body.get('world'))
        scope,document_name,document_id=scope_of(user,world,body.get('uuid'))
        row=find(scope,document_name,document_id)
        if row is None:return None,error('not-found','Eagle-Dokument nicht gefunden.',404)
        if row.doc_type not in ('background','feat'):return None,error('not-origin','Hintergrund oder Merkmal wählen.')
        digest=_digest(row)
    except RequestFailure as failure:return None,read_failure(failure)
    supplement=body.get('supplement')
    fid=supplement.get('featId') if isinstance(supplement,dict) else None
    data,linked,problems=origin_catalog.resolve(user.id,{'advancements':[{'kind':'feat','featId':fid}]},load_creator_data())
    if problems:return None,error('origin-unavailable','Das verknüpfte Talent ist nicht freigegeben.')
    result=origins.inspect(row.source,supplement,data=data,pack=row.pack)
    report={k:result[k] for k in ('playable','edition','entries')}
    return {'body':body,'row':row,'digest':digest,'result':result,'report':report,'linked':linked},None


@blueprint.post('/authoring/origins/check')
@limiter.limit('240 per hour')
def origin_check():
    user=current_user();checked,failure=inspect_request(user)
    if failure:return failure
    row=checked['row'];profile=checked['result']['profile']
    return jsonify(source={'uuid':row.uuid,'name':row.name,'revision':row.revision,'digest':checked['digest']},
        report=checked['report'],profile=profile,profileDigest=content_digest(profile) if profile else None)


@blueprint.post('/authoring/origins/publish')
@limiter.limit('60 per hour')
def origin_publish():
    user=current_user();checked,failure=inspect_request(user)
    if failure:return failure
    body=checked['body'];row=checked['row'];profile=checked['result']['profile']
    if not profile:return error('not-playable','Die blockierenden Punkte zuerst beheben.',report=checked['report'])
    digest=content_digest(profile)
    if body.get('expectedDigest')!=checked['digest'] or body.get('expectedProfileDigest')!=digest:
        return error('source-changed','Quelle oder Zusatz geändert. Bitte erneut prüfen.',409)
    try:
        target=body.get('scope') or body.get('world')
        kind,scope_id=('global',0) if target=='global' else resolve_world(user,target)
    except RequestFailure as failure:return read_failure(failure)
    for linked in checked['linked']:
        if kind=='global' and linked.scope_kind!='global' or kind=='campaign' and (linked.scope_kind,linked.scope_id) not in [('global',0),('campaign',scope_id)]:
            return error('linked-scope','Das Herkunftstalent muss für denselben Nutzerkreis veröffentlicht sein.')
    lineage=_lineage(row,user if kind=='global' else None)
    latest=CeRuleRevision.query.filter_by(scope_kind=kind,scope_id=scope_id,lineage=lineage).order_by(CeRuleRevision.revision_number.desc()).first()
    if latest and latest.profile_digest==digest and latest.source_digest==checked['digest']:
        return jsonify(created=False,revision=latest.summary(),report=checked['report'])
    revision=CeRuleRevision(scope_kind=kind,scope_id=scope_id,lineage=lineage,revision_number=(latest.revision_number if latest else 0)+1,
        kind=profile['kind'],name=profile['entry']['name'],source_uuid=row.uuid,source_revision=row.revision,source_digest=checked['digest'],
        source=copy.deepcopy(row.source),supplement=copy.deepcopy(body['supplement']),profile=profile,profile_digest=digest,published_by=user.id)
    db.session.add(revision)
    try:db.session.commit()
    except IntegrityError:
        db.session.rollback();return error('publish-conflict','Gleichzeitig veröffentlicht. Bitte erneut prüfen.',409)
    return jsonify(created=True,revision=revision.summary(),report=checked['report']),201
