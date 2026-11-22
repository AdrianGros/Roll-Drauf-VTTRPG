"""Production-proof cleanup preserves unrelated people, memberships and files."""
import json
from pathlib import Path
import uuid
import vtt
from vtt.extensions import db
from vtt.models import User,Role,Campaign,CampaignMember
from vtt.models.mapmaker_project import MapmakerProject
from vtt.storage import get_storage_adapter


def test_cleanup_follows_children_without_deleting_existing_parents(tmp_path,monkeypatch):
    app=vtt.create_app('testing')
    app.config.update(STORAGE_PROVIDER='local',LOCAL_STORAGE_PATH=str(tmp_path/'storage'))
    with app.app_context():
        db.create_all();role=Role(name='Cleanup role');db.session.add(role);db.session.flush();role_id=role.id
        users=[User(username=name,email=name+'@example.invalid',password_hash='x',role_id=role.id,is_active=True)
               for name in ['qa_ui_first','qa_ui_second','human_kept']]
        db.session.add_all(users);db.session.flush();qids=[u.id for u in users[:2]];human_id=users[2].id
        campaigns=[Campaign(name='QA review',owner_id=qids[0]),Campaign(name='QA One-Shot',owner_id=qids[0]),Campaign(name='Existing human campaign',owner_id=human_id)]
        db.session.add_all(campaigns);db.session.flush();human_campaign=campaigns[2].id
        db.session.add_all([CampaignMember(campaign_id=human_campaign,user_id=qids[1],campaign_role='PLAYER',status='active'),CampaignMember(campaign_id=human_campaign,user_id=human_id,campaign_role='DM',status='active')])
        storage=get_storage_adapter()
        for uid,key in [(qids[0],'qa.json'),(human_id,'keep.json')]:
            storage.upload(key,b'test')
            db.session.add(MapmakerProject(id=str(uuid.uuid4()),owner_id=uid,title='Scoped project',width=256,height=256,size_bytes=4,storage_key=key,storage_provider='local'))
        db.session.commit()
    path=Path('/tmp/review-web-live-credentials-20261122.json')
    path.write_text(json.dumps({'user_ids':qids}))
    monkeypatch.setattr(vtt,'create_app',lambda _:app)
    source=Path('docs/proofs/review-web-2026-11-18/cleanup-review-fixture.py').read_text()
    exec(compile(source,'cleanup-review-fixture.py','exec'),{'__name__':'review_cleanup_test'})
    with app.app_context():
        assert User.query.count()==1 and User.query.one().id==human_id
        assert Campaign.query.count()==1 and Campaign.query.one().id==human_campaign
        assert CampaignMember.query.count()==1 and CampaignMember.query.one().user_id==human_id
        assert MapmakerProject.query.count()==1 and MapmakerProject.query.one().owner_id==human_id
        assert storage.exists('keep.json') and not storage.exists('qa.json')
        assert db.session.get(Role,role_id) is not None
        db.session.remove();db.engine.dispose()
    assert not path.exists()
