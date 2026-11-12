"""Own SRD targets and atomic typed-catalog additions with bounded replay receipts."""
from copy import deepcopy
from datetime import timedelta
import hashlib
import json
from uuid import UUID

from flask import current_app, jsonify, request
from flask_jwt_extended import jwt_required
from sqlalchemy import delete

from vtt.characters import sheet_link,srd_inventory,srd_manage,srd_progression
from vtt.characters.routes import _get_current_user,_is_active_campaign_member
from vtt.characters.srd_creator import _bad,_inventory_character,srd_creator_bp
from vtt.extensions import db,limiter
from vtt.models import Campaign,Character,CharacterCatalogReceipt
from vtt.utils.time import utcnow


@srd_creator_bp.after_request
def catalog_private_response(response):
    if request.endpoint in ('srd_creator.catalog_targets','srd_creator.catalog_add'):
        response.headers['Cache-Control']='private, no-store'
    return response


def _positive(raw):
    if not raw or not raw.isascii() or not raw.isdigit() or len(raw)>10 or not 0<int(raw)<2**31:
        raise ValueError()
    return int(raw)


def _campaign_name(user_id,campaign):
    return campaign.name if campaign and _is_active_campaign_member(user_id,campaign.id) else None


@srd_creator_bp.get('/catalog-targets')
@limiter.limit('600 per hour')
@jwt_required()
def catalog_targets():
    user,error=_get_current_user()
    if error:return error
    q=request.args.get('q','').strip();entity_id=request.args.get('entity_id','')
    try:
        if len(q)>100 or len(entity_id)>200:raise ValueError()
        after=_positive(request.args['after']) if 'after' in request.args else None
        campaign_id=_positive(request.args['campaign_id']) if request.args.get('campaign_id') else None
    except ValueError:
        return _bad('invalid_filter','Ungültiger Charakterfilter.',400)
    query=Character.query.filter_by(user_id=user.id,deleted_at=None)
    if q:query=query.filter(Character.name.ilike('%'+q+'%'))
    if campaign_id:query=query.filter(Character.campaign_id==campaign_id)
    if after:query=query.filter(Character.id>after)
    rows=query.order_by(Character.id).limit(25).all();page=rows[:24];targets=[]
    for char in page:
        if srd_manage.is_archived(char) or sheet_link.srd_evaluation(char) is None:continue
        campaign=db.session.get(Campaign,char.campaign_id) if char.campaign_id else None
        targets.append(dict(id=char.id,name=char.name,campaign_id=char.campaign_id,
                            campaign_name=_campaign_name(user.id,campaign),level=char.level,
                            progression=srd_progression.status(char,sheet_link.rules_data(char))))
    campaigns=(db.session.query(Campaign).join(Character,Character.campaign_id==Campaign.id)
               .filter(Character.user_id==user.id,Character.deleted_at.is_(None),Campaign.deleted_at.is_(None))
               .distinct().order_by(Campaign.name,Campaign.id).all())
    entry=srd_inventory.catalog().get(entity_id)
    return jsonify(quantity_limit=srd_inventory.MAX_QUANTITY,characters=targets,next_cursor=page[-1].id if len(rows)>24 else None,
                   campaigns=[dict(id=c.id,name=_campaign_name(user.id,c)) for c in campaigns],
                   item=dict(id=entry['id'],name=entry['name'],kind=entry['kind']) if entry else None)


@srd_creator_bp.post('/characters/<int:char_id>/catalog-add')
@limiter.limit('120 per hour')
@jwt_required()
def catalog_add(char_id):
    # This helper locks/reloads Character before ownership/SRD checks and all
    # dependent inventory reads; it is also used by the old SRD inventory paths.
    user,char,error=_inventory_character(char_id,write=True)
    if error:return error
    if srd_manage.is_archived(char):return _bad('archived','Archivierte Charaktere sind kein Übernahmeziel.',409)
    body=request.get_json(silent=True)
    if not isinstance(body,dict) or set(body)!= {'entity_id','quantity','request_id'}:
        return _bad('invalid_body','JSON-Objekt mit Gegenstand, Menge und Anfrage-ID erwartet.',400)
    entity_id=body['entity_id']
    if not isinstance(entity_id,str) or len(entity_id)>200 or entity_id not in srd_inventory.catalog():
        return _bad('unsupported_catalog_entry','Dieser Eintrag ist kein unterstützter Inventargegenstand. Nutze für Regelentscheidungen den Fortschrittsbereich.',422)
    try:
        request_id=str(UUID(body['request_id']))
        quantity=srd_inventory._clean_quantity(body['quantity'])
    except (ValueError,TypeError,AttributeError):
        return _bad('invalid_request_id','Ungültige Anfrage-ID.',400)
    except srd_inventory.InventoryError as exc:
        return _bad(exc.code,exc.message,exc.status)
    digest=hashlib.sha256(json.dumps({'entity_id':entity_id,'quantity':quantity},sort_keys=True,separators=(',',':')).encode()).hexdigest()
    now=utcnow()
    old=CharacterCatalogReceipt.query.filter_by(character_id=char.id,actor_user_id=user.id,request_id=request_id).first()
    if old:
        if old.expires_at<=now:return _bad('request_expired','Die Bestätigung ist abgelaufen. Prüfe das Inventar vor einer neuen Übernahme.',409)
        if old.request_digest!=digest:return _bad('request_conflict','Diese Anfrage-ID wurde bereits für eine andere Übernahme verwendet.',409)
        confirmation=deepcopy(old.response);db.session.commit()
        return jsonify(receipt=confirmation,replayed=True,table_refresh='replay'),200
    try:
        db.session.execute(delete(CharacterCatalogReceipt).where(CharacterCatalogReceipt.character_id==char.id,
            CharacterCatalogReceipt.actor_user_id==user.id,CharacterCatalogReceipt.expires_at<=now))
        rows=srd_inventory.add_catalog_item(char,entity_id,quantity);db.session.flush()
        entry=srd_inventory.catalog()[entity_id]
        confirmation=dict(id=request_id,character_id=char.id,character_name=char.name,entity_id=entity_id,
            entity_name=entry['name'],quantity=quantity,
            items=[dict(id=row.id,name=row.name,quantity=row.quantity) for row in {row.id:row for row in rows}.values()],
            created_at=now.isoformat()+'Z',expires_at=(now+timedelta(hours=24)).isoformat()+'Z',
            sheet_href=f'/character-sheet?id={char.id}&section=inventory')
        db.session.add(CharacterCatalogReceipt(character_id=char.id,actor_user_id=user.id,request_id=request_id,
            request_digest=digest,response=confirmation,created_at=now,expires_at=now+timedelta(hours=24)))
        db.session.commit()
    except srd_inventory.InventoryError as exc:
        db.session.rollback();return _bad(exc.code,exc.message,exc.status)
    except Exception:
        db.session.rollback();raise
    refresh='sent'
    try:sheet_link.push_character_to_tokens(char)
    except Exception:
        db.session.rollback();refresh='pending'
        current_app.logger.warning('Catalog action committed; table refresh pending',extra={'character_id':confirmation['character_id']})
    return jsonify(receipt=confirmation,replayed=False,table_refresh=refresh),201
