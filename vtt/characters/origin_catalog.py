"""Authorized selection of immutable Background/Feat revisions; finished sheets use pins."""
import copy
from flask import current_app
from sqlalchemy import and_,or_
from vtt.extensions import db
from vtt.models import CeRuleRevision,User
from vtt.rules_content import origin_profiles as profiles
from vtt.rules_content.creator_rules import load_creator_data
from .species_catalog import can_select,_campaign_ids,_scope


def enabled():
    return bool(current_app.config.get('CE_PLAYABLE_ORIGINS'))


def pin_for(row):
    author=db.session.get(User,row.published_by)
    return {'schema':profiles.PIN_SCHEMA,'revisionId':row.id,'revision':row.revision_number,
        'digest':row.profile_digest,'sourceUuid':row.source_uuid,'sourceDigest':row.source_digest,
        'scope':_scope(row),'author':author.username if author else None,
        'publishedAt':row.published_at.isoformat()+'Z' if row.published_at else None,
        'profile':copy.deepcopy(row.profile)}


def resolve(user_id,state,data=None):
    data=data or load_creator_data();rows={};problems=[]
    pending=profiles.selected_ids(state)
    while pending:
        key=pending.pop(0)
        if key in rows:continue
        parsed=profiles.parse_id(key)
        row=db.session.get(CeRuleRevision,parsed[1]) if parsed and enabled() else None
        if row is None or row.kind!=parsed[0] or not can_select(user_id,row):
            problems.append({'path':'background.id' if key.startswith('homebrew.background.') else 'advancements',
                'message':'Diese Homebrew-Fassung ist für dich nicht (mehr) freigegeben.'})
            continue
        rows[key]=row
        if row.kind=='background':
            fid=row.profile['entry']['featId']
            if profiles.parse_id(fid):pending.append(fid)
    return profiles.with_pins(data,[pin_for(row) for row in rows.values()]),list(rows.values()),problems


def catalog(user_id):
    result={'backgrounds':[],'feats':[]}
    if not enabled():return result
    campaigns=_campaign_ids(user_id)
    rows=CeRuleRevision.query.filter(or_(
        and_(CeRuleRevision.scope_kind=='global',CeRuleRevision.scope_id==0),
        and_(CeRuleRevision.scope_kind=='personal',CeRuleRevision.scope_id==user_id),
        and_(CeRuleRevision.scope_kind=='campaign',CeRuleRevision.scope_id.in_(campaigns or [-1])),
    )).order_by(CeRuleRevision.revision_number,CeRuleRevision.id).all()
    latest={}
    for row in rows:latest[(row.scope_kind,row.scope_id,row.lineage)]=row
    for row in sorted(latest.values(),key=lambda r:(r.name.casefold(),r.id)):
        if row.kind=='background':
            parsed=profiles.parse_id(row.profile['entry']['featId'])
            if parsed:
                feat=db.session.get(CeRuleRevision,parsed[1])
                if feat is None or feat.kind!='feat' or not can_select(user_id,feat):continue
        result['backgrounds' if row.kind=='background' else 'feats'].append(profiles.entry_for(pin_for(row)))
    return result


def campaign_problem(pins,campaign_id):
    for pin in pins:
        scope=pin.get('scope') or {}
        if scope.get('kind')=='campaign' and scope.get('id')!=campaign_id:
            return f"„{pin['profile']['entry']['name']}“ ist an die Kampagne „{scope.get('label','Kampagne')}“ gebunden."
    return None
