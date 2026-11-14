"""Rebuild the cleanup reference after the app container (and its /tmp) was recreated."""
import json,os,warnings
warnings.filterwarnings('ignore')
from vtt import create_app
from vtt.models import User,Campaign,GameSession
app=create_app('production')
with app.app_context():
    users=[u for u in User.query.filter(User.username.like('feedback%b08%')).all() if u.username.startswith('feedback_b08_')]
    campaigns=[c for c in Campaign.query.filter(Campaign.name.like('Feedback-B08%')).all() if c.name.startswith('Feedback-B08 ')]
    assert len(users)==2 and len(campaigns)==1,(len(users),len(campaigns))
    campaign=campaigns[0];uids=sorted(u.id for u in users)
    assert campaign.owner_id in uids and all(u.email.endswith('@example.invalid') for u in users)
    suffix=campaign.name.split()[-1];assert all(u.username.endswith('_'+suffix) for u in users)
    sids=[s.id for s in GameSession.query.filter_by(campaign_id=campaign.id).all()]
    target='/tmp/feedback-b08-live-credentials.json';fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as out:json.dump({'campaign_id':campaign.id,'session_ids':sids,'user_ids':uids},out)
    print(json.dumps({'campaign_id':campaign.id,'session_ids':sids,'user_ids':uids,'usernames':sorted(u.username for u in users)}))
