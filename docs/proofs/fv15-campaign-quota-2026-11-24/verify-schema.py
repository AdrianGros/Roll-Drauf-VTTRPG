"""Inspect the additive table only; no DDL or account mutation."""
import json
import os
from pathlib import Path
import subprocess
code='''import json,warnings
warnings.filterwarnings('ignore')
from vtt import create_app
from vtt.extensions import db
from sqlalchemy import inspect
app=create_app('production')
with app.app_context():
 i=inspect(db.engine);name='campaign_quota_requests'
 checks={row['name']:row['sqltext'] for row in i.get_check_constraints(name)}
 pending=checks['ck_campaign_quota_request_pending_key'].lower().replace('"','')
 assert 'pending_key is not null' in pending
 assert any(row['column_names']==['pending_key'] for row in i.get_unique_constraints(name))
 refs=i.get_foreign_keys(name)
 assert {tuple(row['constrained_columns']) for row in refs if row['referred_table']=='users'}=={('requester_id',),('reviewer_id',)}
 print(json.dumps({'status':'pass','table':name,'checks':sorted(checks),'unique_pending_key':True,'requester_reviewer_user_foreign_keys':True}))
'''
r=subprocess.run(['docker','exec','-i','roll-drauf-vtt-app-1','python','-'],input=code,text=True,capture_output=True,check=True)
proof=json.loads(r.stdout.strip().splitlines()[-1])
(Path(os.environ['PROOF_ROOT'])/'schema-constraints.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
