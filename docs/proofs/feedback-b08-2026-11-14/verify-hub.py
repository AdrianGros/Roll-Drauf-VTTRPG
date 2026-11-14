"""After the hub import: one campaign map, no new session and no table context."""
import json,warnings
warnings.filterwarnings('ignore')
from sqlalchemy import text
from vtt import create_app
from vtt.extensions import db
from vtt.models import Asset,CampaignMap,GameSession
from vtt.models.mapmaker_project import MapmakerProject
app=create_app('production')
with app.app_context():
    f=json.load(open('/tmp/feedback-b08-live-credentials.json'));cid=f['campaign_id']
    maps=CampaignMap.query.filter_by(campaign_id=cid,name='Hubkarte B08').all();assert len(maps)==1
    assets=Asset.query.filter_by(campaign_id=cid).all();assert len(assets)==1,len(assets);asset=assets[0]
    contexts=db.session.execute(text('SELECT COUNT(*) FROM play_table_contexts WHERE campaign_id=:c'),{'c':cid}).scalar()
    sessions=GameSession.query.filter_by(campaign_id=cid).count()
    project=db.session.get(MapmakerProject,f['projects'][0]['id'])
    result={'campaign_maps_named':len(maps),'map_size':[maps[0].width,maps[0].height],'asset_mime':asset.mime_type,'asset_type':asset.asset_type,
            'asset_session_id':asset.session_id,'background_references_asset':str(asset.id) in (maps[0].background_url or ''),'game_sessions':sessions,'table_contexts':contexts,'source_project_revision':project.revision}
    assert sessions==2 and contexts==0 and project.revision==1,result
    print(json.dumps({'status':'pass',**result}))
