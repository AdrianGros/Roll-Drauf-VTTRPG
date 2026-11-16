import json,os,secrets,warnings
warnings.filterwarnings("ignore")
from datetime import timedelta
from flask_jwt_extended import create_access_token,get_csrf_token,decode_token
from vtt import create_app
from vtt.extensions import db
from vtt.models import User,Role,Campaign,CampaignMember,CampaignMap,GameSession,TokenState,Session,Character
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_rules import load_creator_data,evaluate
from vtt.rules_content.creator_drafts import character_values
from vtt.utils.time import utcnow
def wizard_state(data, name="Mira Eulenfeder"):
    cantrips = [sid for sid in data["spellLists"]["wizard"] if data["spells"][sid]["level"] == 0][:4]
    book = [sid for sid in data["spellLists"]["wizard"] if 1 <= data["spells"][sid]["level"] <= 3][:14]
    return {
        "abilityMethod": "manual",
        "abilityBase": {"str": 8, "dex": 12, "con": 13, "int": 15, "wis": 14, "cha": 10},
        "levels": [{"classKey": "wizard"}] * 5,
        "background": {"id": "character-origins.backgrounds.sage", "abilityBonus": {"int": 2, "con": 1}},
        "species": {"id": "character-origins.species.halfling", "choices": {}},
        "subclasses": {"wizard": "classes.wizard.subclass-evoker"},
        "skills": {"class": ["heilkunde", "nachforschungen"], "expertise": ["arkane-kunde"]},
        "advancements": [{"classKey": "wizard", "classLevel": 4, "kind": "asi", "increases": {"int": 2}}],
        "spells": {"wizard": {"cantrips": cantrips, "spellbook": book, "prepared": book[:9]}},
        "identity": {"name": name, "alignment": "neutral-gut", "backstory": "Fand eine Eule."},
    }
app=create_app("production")
with app.app_context():
    suffix=secrets.token_hex(4);users=[]
    for kind,role_name in [("dm","DM"),("player","Player")]:
        role=Role.query.filter_by(name=role_name).first();assert role
        user=User(username="qa_sf_"+kind+"_"+suffix,email="qa_sf_"+kind+"_"+suffix+"@example.invalid",role_id=role.id,is_active=True,email_verified=True,profile_tier=kind,active_campaigns_quota=3,storage_quota_gb=1)
        user.set_password(secrets.token_urlsafe(32));db.session.add(user);db.session.flush();users.append(user)
    owner,player=users
    campaign=Campaign(name="QA Session Feedback "+suffix,description="Eigene temporäre technische Live-Abnahme",owner_id=owner.id,status="active",max_players=6)
    db.session.add(campaign);db.session.flush()
    for user,role in [(owner,"DM"),(player,"Player")]:
        db.session.add(CampaignMember(campaign_id=campaign.id,user_id=user.id,campaign_role=role,status="active",joined_at=utcnow(),invited_at=utcnow(),accepted_at=utcnow(),invited_by=owner.id))
    map_=CampaignMap(campaign_id=campaign.id,name="Aktionsprüfung",width=1200,height=900,created_by=owner.id)
    db.session.add(map_);db.session.flush()
    second_map=CampaignMap(campaign_id=campaign.id,name="Zweite Abnahmekarte",width=1200,height=900,created_by=owner.id)
    db.session.add(second_map);db.session.flush()
    other=GameSession(campaign_id=campaign.id,name="Isolierte Aktionssitzung",status="in_progress",map_id=map_.id)
    main=GameSession(campaign_id=campaign.id,name="Live-Aktionsprüfung",status="in_progress",map_id=map_.id)
    db.session.add(other);db.session.flush();db.session.add(main);db.session.commit()
    data=load_creator_data();state=wizard_state(data,"Live-Aktionsmagier")
    char=Character(user_id=player.id,**character_values(data,state,evaluate(data,state),draft_id=1,finalized_at=utcnow().isoformat()+"Z"));char.campaign_id=campaign.id
    db.session.add(char);db.session.commit()
    from vtt.play.service import init_scene_stack
    init_scene_stack(campaign,main,owner,[map_.id,second_map.id])
    runtime=ensure_session_state(campaign,main)
    token=TokenState(session_state_id=runtime.id,campaign_id=campaign.id,game_session_id=main.id,map_id=map_.id,character_id=char.id,owner_user_id=player.id,name=char.name,token_type="player",x=1,y=1,size=1,rotation=0,visibility="public",metadata_json={},updated_by=player.id,version=1)
    db.session.add(token);db.session.flush()
    hidden=TokenState(session_state_id=runtime.id,campaign_id=campaign.id,game_session_id=main.id,map_id=map_.id,owner_user_id=owner.id,name="QA_PRIVATE_SENTINEL",token_type="monster",x=350,y=210,size=1,rotation=0,visibility="dm_only",metadata_json={"position_mode":"pixel"},updated_by=owner.id,version=1,hp_current=12,hp_max=12)
    npc=TokenState(session_state_id=runtime.id,campaign_id=campaign.id,game_session_id=main.id,map_id=map_.id,owner_user_id=owner.id,name="QA Goblin",token_type="monster",x=490,y=210,size=1,rotation=0,visibility="public",metadata_json={"position_mode":"pixel"},updated_by=owner.id,version=1,hp_current=12,hp_max=12)
    db.session.add_all([hidden,npc]);db.session.flush()
    result={"campaign_id":campaign.id,"session_id":main.id,"other_session_id":other.id,"session_ids":[main.id,other.id],"character_id":char.id,"character_name":char.name,"token_id":token.id,"map_id":map_.id,"second_map_id":second_map.id,"secret_token_id":hidden.id,"npc_id":npc.id,"user_ids":[u.id for u in users],"users":{}}
    for kind,user in zip(["dm","player"],users):
        access=create_access_token(identity=str(user.id));decoded=decode_token(access)
        db.session.add(Session(user_id=user.id,token_jti=decoded["jti"],expires_at=utcnow()+timedelta(hours=1)))
        result["users"][kind]={"id":user.id,"username":user.username,"token":access,"csrf":get_csrf_token(access)}
    db.session.commit()
    target="/tmp/session-feedback-live-credentials.json"
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as out:json.dump(result,out)
    print("Synthetic personal-action fixture created")
