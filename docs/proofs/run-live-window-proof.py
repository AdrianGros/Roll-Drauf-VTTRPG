"""Create and remove only isolated QA data around the normal-role UI proof."""
import json
import os
from pathlib import Path
import subprocess

repo=Path(__file__).resolve().parents[2]
release=Path(os.environ.get('RELEASE_DIR','/srv/migration/2026-11-11/feedback-playtable-windows-20261122/07f4bf075'))
record=json.loads((release/'release.json').read_text())
actual=subprocess.check_output(['docker','inspect','roll-drauf-vtt-app-1','--format','{{.Image}}'],text=True).strip()
assert actual==record['image_id'],'Verify the intended image before live acceptance'
proof=release/'live';proof.mkdir(mode=0o700,exist_ok=True)
credential=proof/'private-live-credentials.json'
container_path='/tmp/window-fix-live-credentials-20261122.json'
fixture=(repo/'docs/proofs/ui-playtable-2026-11-17/create-live-fixture.py').read_text().replace('/tmp/ui-playtable-live-credentials.json',container_path)
cleanup=(repo/'docs/proofs/review-web-2026-11-18/cleanup-review-fixture.py').read_text().replace('/tmp/review-web-live-credentials-20261122.json',container_path)
subprocess.run(['docker','exec','-i','roll-drauf-vtt-app-1','python','-'],input=fixture,text=True,check=True)
try:
    data=subprocess.check_output(['docker','exec','roll-drauf-vtt-app-1','cat',container_path])
    fd=os.open(credential,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as out:out.write(data)
    subprocess.run(['docker','run','--rm','--network','host','-e','PROOF_ROOT=/proof',
                    '-v',str(repo)+':/app:ro','-v',str(proof)+':/proof',
                    '-v','/root/.cache/ms-playwright:/root/.cache/ms-playwright:ro',
                    '--entrypoint','python','roll-drauf-vtt-mobile-tests:20261115',
                    '/app/docs/proofs/live-window-journey.py'],check=True)
finally:
    result=subprocess.run(['docker','exec','-i','roll-drauf-vtt-app-1','python','-'],input=cleanup,text=True,capture_output=True)
    if result.returncode:
        raise RuntimeError('Synthetic cleanup failed; reconcile scoped QA fixture before continuing. '+result.stderr[-1200:])
    (proof/'cleanup.json').write_text(result.stdout.strip()+'\n')
    credential.unlink(missing_ok=True)
    print('Synthetic fixture and temporary credentials removed')
