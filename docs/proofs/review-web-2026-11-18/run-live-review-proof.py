"""Bounded production acceptance; all created data belongs to synthetic QA users."""
import json,os,subprocess
from pathlib import Path

repo=Path(__file__).resolve().parents[3]
release=Path(os.environ['RELEASE_DIR']).resolve();record=json.loads((release/'release.json').read_text())
actual=subprocess.check_output(['docker','inspect','roll-drauf-vtt-app-1','--format','{{.Image}}'],text=True).strip()
assert actual==record['image_id'],'Verify the intended image before live acceptance'
proof=release/'live';proof.mkdir(mode=0o700,exist_ok=True)
credentials=proof/'private-live-credentials.json';target='/tmp/review-web-live-credentials-20261122.json'
source=(repo/'docs/proofs/ui-playtable-2026-11-17/create-live-fixture.py').read_text().replace('/tmp/ui-playtable-live-credentials.json',target)
addon='''    from uuid import uuid4
    from sqlalchemy.orm.attributes import flag_modified
    from vtt.models.calendar_note import CalendarNote
    char.character_data['srdCompanions']=[dict(id='c12345678',name='QA Companion',kind='Wolf',speed='12 m',hpMax=20,hpCurrent=13,ac=13,attacks='',notes='')]
    flag_modified(char,'character_data')
    db.session.add(CalendarNote(user_id=owner.id,request_key=str(uuid4()),input_digest='f'*64,local_date=utcnow().date(),title='QA Due preparation',body='Server worker proof',color='purple',reminder_at=utcnow()-timedelta(minutes=1),reminder_state='pending',timezone='UTC'))
    db.session.flush()
'''
needle='    result={"campaign_id":';assert source.count(needle)==1;source=source.replace(needle,addon+needle)
subprocess.run(['docker','exec','-i','roll-drauf-vtt-app-1','python','-'],input=source,text=True,check=True)
try:
    data=subprocess.check_output(['docker','exec','roll-drauf-vtt-app-1','cat',target])
    fd=os.open(credentials,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(data)
    worker=subprocess.run(['docker','exec','roll-drauf-vtt-app-1','python','-m','vtt.calendar_reminder_worker'],text=True,capture_output=True,check=True)
    (proof/'worker.json').write_text(worker.stdout.strip()+'\n')
    scripts=os.environ.get('PROOF_SCRIPTS','live-review-journey.py,live-table-maps.py').split(',')
    assert scripts and all(script in {'live-review-journey.py','live-table-maps.py'} for script in scripts)
    for script in scripts:
        subprocess.run(['docker','run','--rm','--network','host','-e','PROOF_ROOT=/proof',
                        '-v',str(repo)+':/app:ro','-v',str(proof)+':/proof',
                        '-v','/root/.cache/ms-playwright:/root/.cache/ms-playwright:ro',
                        '--entrypoint','python','roll-drauf-vtt-mobile-tests:20261115',
                        '/app/docs/proofs/review-web-2026-11-18/'+script],check=True)
finally:
    cleanup=(repo/'docs/proofs/review-web-2026-11-18/cleanup-review-fixture.py').read_text()
    result=subprocess.run(['docker','exec','-i','roll-drauf-vtt-app-1','python','-'],input=cleanup,text=True,capture_output=True)
    if result.returncode:raise RuntimeError('Scoped QA cleanup needs reconciliation: '+result.stderr[-1500:])
    (proof/'cleanup.json').write_text(result.stdout.strip()+'\n');credentials.unlink(missing_ok=True)
    print('Synthetic review fixture, private objects and credentials removed')
