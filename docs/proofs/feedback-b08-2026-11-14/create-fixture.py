"""Synthetic B08 live fixture: DM + Player, own campaign/session, two private editor maps."""
import json,os,secrets,warnings
warnings.filterwarnings("ignore")
from uuid import uuid4
from vtt import create_app
from vtt.extensions import db
from vtt.models import User,Role,Campaign,CampaignMember,CampaignMap,GameSession,TokenState,Character
from vtt.models.mapmaker_project import MapmakerProject
from vtt.mapmaker_document import normalize_document
from vtt.play.service import ensure_session_state
from vtt.rules_content.creator_rules import load_creator_data,evaluate
from vtt.rules_content.creator_drafts import character_values
from vtt.storage import get_storage_adapter
from vtt.utils.time import utcnow
TARGET="/tmp/feedback-b08-live-credentials.json"
assert not os.path.exists(TARGET)
app=create_app("production")
with app.app_context():
    suffix=secrets.token_hex(4);users=[];passwords={}
    for kind,role_name in [("dm","DM"),("player","Player")]:
        role=Role.query.filter_by(name=role_name).first();assert role
        user=User(username="feedback_b08_"+kind+"_"+suffix,email="feedback_b08_"+kind+"_"+suffix+"@example.invalid",role_id=role.id,is_active=True,email_verified=True,profile_tier=kind,active_campaigns_quota=3,storage_quota_gb=1)
        password=secrets.token_urlsafe(32);passwords[kind]=password;user.set_password(password);db.session.add(user);db.session.flush();users.append(user)
    owner,player=users
    campaign=Campaign(name="Feedback-B08 "+suffix,description="Eigene temporäre technische Live-Abnahme",owner_id=owner.id,status="active",max_players=6)
    db.session.add(campaign);db.session.flush()
    for user,role in [(owner,"DM"),(player,"Player")]:
        db.session.add(CampaignMember(campaign_id=campaign.id,user_id=user.id,campaign_role=role,status="active",joined_at=utcnow(),invited_at=utcnow(),accepted_at=utcnow(),invited_by=owner.id))
    map_=CampaignMap(campaign_id=campaign.id,name="Journalprüfung",width=1200,height=900,grid_size=50,fog_enabled=False,created_by=owner.id)
    db.session.add(map_);db.session.flush()
    other=GameSession(campaign_id=campaign.id,name="Andere Sitzung",status="in_progress",map_id=map_.id)
    main=GameSession(campaign_id=campaign.id,name="Live-Journalprüfung",status="in_progress",map_id=map_.id)
    db.session.add(other);db.session.flush();db.session.add(main);db.session.commit()
    data=load_creator_data()
    cantrips=[sid for sid in data["spellLists"]["wizard"] if data["spells"][sid]["level"]==0][:4]
    book=[sid for sid in data["spellLists"]["wizard"] if 1<=data["spells"][sid]["level"]<=3][:14]
    state={"abilityMethod":"manual","abilityBase":{"str":8,"dex":12,"con":13,"int":15,"wis":14,"cha":10},"levels":[{"classKey":"wizard"}]*5,
           "background":{"id":"character-origins.backgrounds.sage","abilityBonus":{"int":2,"con":1}},"species":{"id":"character-origins.species.halfling","choices":{}},
           "subclasses":{"wizard":"classes.wizard.subclass-evoker"},"skills":{"class":["heilkunde","nachforschungen"],"expertise":["arkane-kunde"]},
           "advancements":[{"classKey":"wizard","classLevel":4,"kind":"asi","increases":{"int":2}}],
           "spells":{"wizard":{"cantrips":cantrips,"spellbook":book,"prepared":book[:9]}},"identity":{"name":"Journal","alignment":"neutral-gut","backstory":"Test."}}
    char=Character(user_id=player.id,**character_values(data,state,evaluate(data,state),draft_id=1,finalized_at=utcnow().isoformat()+"Z"));char.campaign_id=campaign.id;char.xp=14000
    db.session.add(char);db.session.commit()
    runtime=ensure_session_state(campaign,main)
    token=TokenState(session_state_id=runtime.id,campaign_id=campaign.id,game_session_id=main.id,map_id=map_.id,character_id=char.id,owner_user_id=player.id,name=char.name,token_type="player",x=200,y=200,sight_range=100,size=1,rotation=0,visibility="public",metadata_json={"position_mode":"pixels"},updated_by=player.id,version=1)
    db.session.add(token);db.session.commit()
    projects=[]
    for title,top,bottom in [("Küstenwelt B08","#1d4e6b","#8cc0c9"),("Bergwelt B08","#5b3a1e","#d8b27a")]:
        identity=str(uuid4())
        document,encoded=normalize_document({"format":"rd-mapmaker","version":1,"size":{"w":1024,"h":768},"meta":{"title":title},"sea":{"top":top,"bottom":bottom},
            "layers":[{"id":"roads","kind":"paths","name":"Wege","visible":True,"opacity":1,"items":[{"id":"r1","x":200,"y":300,"material":"river","width":12,"points":[{"x":0,"y":0},{"x":400,"y":120},{"x":600,"y":-80}]}]}]})
        key=f"users/{owner.id}/mapmaker/{identity}/{uuid4()}.json";get_storage_adapter().upload(key,encoded)
        db.session.add(MapmakerProject(id=identity,owner_id=owner.id,title=document["meta"]["title"],width=1024,height=768,revision=1,size_bytes=len(encoded),storage_key=key,storage_provider=app.config.get("STORAGE_PROVIDER","local")))
        owner.storage_used_gb=(owner.storage_used_gb or 0)+len(encoded)/(1024**3);projects.append({"id":identity,"title":title})
    db.session.commit()
    result={"campaign_id":campaign.id,"session_id":main.id,"other_session_id":other.id,"session_ids":[main.id,other.id],"character_id":char.id,"token_id":token.id,
            "user_ids":[u.id for u in users],"projects":projects,"users":{k:{"id":u.id,"username":u.username,"password":passwords[k]} for k,u in zip(["dm","player"],users)}}
    fd=os.open(TARGET,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"w") as out:json.dump(result,out)
    print("Synthetic B08 fixture created")
