"""Commit-only app releases using the actual live image and guarded Compose workflow.

prepare -> schema (backup, optional additive models) -> activate.
Never builds the unrelated original checkout or installs dependencies.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import time
import urllib.request


def run(args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def inspect(target):
    return json.loads(subprocess.check_output(['docker', 'inspect', target]))[0]


def read_record(directory):
    return json.loads((directory / 'release.json').read_text())


def save(directory, record):
    (directory / 'release.json').write_text(json.dumps(record, indent=2) + '\n')


def current(record):
    actual = inspect('roll-drauf-vtt-app-1')
    assert actual['Image'] == record['base_image_id'], 'Production changed; reconcile before delivery'
    return actual


def prepare(args):
    assert re.fullmatch(r'[a-z0-9-]{1,40}', args.package)
    assert not subprocess.check_output(['git','status','--porcelain','--','vtt','app.py','requirements.txt'], text=True), 'Commit app changes first'
    app = inspect('roll-drauf-vtt-app-1')
    assert app['Image'] == args.expected_image
    base_source = subprocess.check_output(['git','rev-parse',args.base_source],text=True).strip()
    expected_revision = subprocess.check_output(['git','rev-parse',args.expected_revision or args.base_source],text=True).strip()
    assert app['Config']['Labels']['org.opencontainers.image.revision'] == expected_revision
    commit = subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    directory = Path('/srv/migration/2026-11-11') / ('feedback-' + args.package) / commit[:9]
    directory.mkdir(parents=True, exist_ok=True);directory.chmod(0o700)
    assert not (directory/'release.json').exists(), 'Use existing record for a prepared release'
    prior = f'roll-drauf-vtt-app:feedback-{args.package}-rollback-20261111-{app["Image"][7:19]}'
    run(['docker','tag',app['Image'],prior])
    image = f'roll-drauf-vtt-app:feedback-{args.package}-20261111-{commit[:9]}'
    paths = subprocess.check_output(['git','diff','--name-only',base_source,commit,'--','vtt','app.py','requirements.txt'],text=True).splitlines()
    hash_code = 'import json,sys,hashlib;from pathlib import Path;print(json.dumps({p:hashlib.sha256(Path("/app",p).read_bytes()).hexdigest() if Path("/app",p).is_file() else None for p in json.load(sys.stdin)}))'
    running_hashes = json.loads(subprocess.check_output(['docker','exec','-i','roll-drauf-vtt-app-1','python','-c',hash_code],input=json.dumps(paths).encode()))
    manifest = {}
    for relative in paths:
        source = Path(relative)
        assert source.is_file(), 'Deletion requires an explicit release design: ' + relative
        if running_hashes.get(relative) == hashlib.sha256(source.read_bytes()).hexdigest():
            continue  # reconciled, already-live work is preserved by the image base
        target = directory/'build/files'/relative;target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
        manifest[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    # Image-only legacy backups were identified in the approved reconciliation.
    removals = ['vtt/templates/creation-engine.html.orig', 'vtt/templates/character-sheet.html.orig']
    for relative in ['requirements.txt']:
        source = Path(relative)
        target = directory/'build/files'/relative; target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
    assert manifest
    (directory/'build/Dockerfile').write_text(f'FROM {prior}\nCOPY files/ /app/\nRUN rm -f /app/vtt/templates/creation-engine.html.orig /app/vtt/templates/character-sheet.html.orig\nLABEL org.opencontainers.image.revision="{commit}"\nLABEL de.roll-drauf.feedback-program.base-image="{app["Image"]}"\n')
    compose_files = app['Config']['Labels']['com.docker.compose.project.config_files'].split(',')
    assert len(compose_files) == 2
    shutil.copy2(compose_files[1],directory/'previous.override.yml')
    before = {}
    for cid in subprocess.check_output(['docker','ps','-q'],text=True).splitlines():
        item = inspect(cid)
        if item['Name'].startswith('/roll-drauf-vtt-') and item['Name'] != '/roll-drauf-vtt-app-1':
            before[item['Name']] = {'id':item['Id'],'started_at':item['State']['StartedAt']}
    record = {'commit':commit,'base_source':base_source,'running_revision_label':expected_revision,'image':image,'base_image_id':app['Image'],
              'prior_image':prior,'overlay_manifest':manifest,'compose_project':app['Config']['Labels']['com.docker.compose.project'],
              'compose_files':compose_files,'other_services_before':before,'prepared_at':datetime.now(timezone.utc).isoformat()}
    tracked = subprocess.check_output(['git','ls-files','--','vtt','app.py','requirements.txt'],text=True).splitlines()
    # The live image deliberately omits the superseded G1 engine. Do not resurrect
    # every repository file: require every SHIPPED file to have committed content.
    listing = 'import json;from pathlib import Path;r=Path("/app");print(json.dumps([str(p.relative_to(r)) for base in [r/"vtt",r/"app.py",r/"requirements.txt"] for p in ([base] if base.is_file() else base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]))'
    shipped = set(json.loads(subprocess.check_output(['docker','exec','roll-drauf-vtt-app-1','python','-c',listing])))
    shipped = (shipped - set(removals)) | set(manifest)
    assert not (shipped - set(tracked)), 'Uncommitted application files in the image: ' + str(sorted(shipped-set(tracked)))
    expected = {p:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in shipped}
    record['tracked_files_intentionally_absent'] = sorted(set(tracked)-shipped)
    record['removed_obsolete_backups'] = removals
    record['expected_runtime_files'] = len(expected)
    (directory/'expected-runtime-sha256.json').write_text(json.dumps(expected))
    save(directory,record)
    run(['docker','build','--network','none','-t',image,str(directory/'build')])
    verify = 'import json,sys,hashlib;from pathlib import Path;e=json.load(sys.stdin);r=Path("/app");actual={str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for base in [r/"vtt",r/"app.py",r/"requirements.txt"] for p in ([base] if base.is_file() else base.rglob("*")) if p.is_file() and "__pycache__" not in p.parts};wrong=[p for p,h in e.items() if actual.get(p)!=h];extra=sorted(set(actual)-set(e));print(json.dumps({"checked":len(e),"actual":len(actual),"mismatches":wrong,"uncommitted_files":extra}));assert not wrong and not extra'
    proof = json.loads(subprocess.check_output(['docker','run','--rm','-i','--network','none','--entrypoint','python',image,'-c',verify],input=json.dumps(expected).encode()))
    with (directory/'factory-check.log').open('w') as out:
        run(['docker','run','--rm','--network','none','--entrypoint','python',image,'-c','import warnings;warnings.filterwarnings("ignore");from vtt import create_app;create_app("testing");print("Factory OK")'],stdout=out,stderr=subprocess.STDOUT)
    record['image_id'] = inspect(image)['Id'];record['built_source_verification'] = proof
    save(directory,record)
    print(json.dumps({'release_directory':str(directory),'image':image,'verified_source_files':proof['checked']}))


def schema(args):
    directory=Path(args.directory);record=read_record(directory);current(record)
    backup=directory/'database-before.dump'
    if not backup.exists():
        with os.fdopen(os.open(backup,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'wb') as out:
            run(['docker','exec','roll-drauf-vtt-db-1','sh','-c','pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc'],stdout=out)
    assert backup.stat().st_size>1000
    run(['docker','exec','-i','roll-drauf-vtt-db-1','pg_restore','--list'],input=backup.read_bytes(),stdout=subprocess.DEVNULL)
    record['database_backup']={'path':str(backup),'bytes':backup.stat().st_size,'archive_readable':True,'restore_exercised':False}
    sources=[Path(p).read_text() for p in args.model]
    code='''import json,warnings
warnings.filterwarnings("ignore")
from vtt import create_app
from vtt.extensions import db
from sqlalchemy import inspect
app=create_app("production")
with app.app_context():
    before=set(db.metadata.tables)
    namespace={"__name__":"feedback_additive_schema"}
    for source in SOURCES:exec(compile(source,"feedback_additive_model.py","exec"),namespace)
    names=set(db.metadata.tables)-before
    existing=[name for name in names if inspect(db.engine).has_table(name)]
    for table in db.metadata.sorted_tables:
        if table.name in names:table.create(bind=db.engine,checkfirst=True)
    for name in names:
        table=db.metadata.tables[name]
        actual={c["name"]:c for c in inspect(db.engine).get_columns(name)}
        for column in table.columns:
            assert column.name in actual,(name,column.name)
            assert str(actual[column.name]["type"].compile(db.engine.dialect))==str(column.type.compile(db.engine.dialect)),(name,column.name,"type")
            assert actual[column.name]["nullable"]==column.nullable,(name,column.name,"nullable")
    print(json.dumps({"status":"pass","tables":sorted(names),"previously_present":existing,"columns_verified":True}))
'''.replace('SOURCES',repr(sources))
    result=run(['docker','exec','-i','roll-drauf-vtt-app-1','python','-'],input=code,text=True,capture_output=True)
    proof=json.loads(result.stdout.strip().splitlines()[-1]);record['schema_migration']=proof;save(directory,record)
    print(json.dumps(proof))


def activate(args):
    directory=Path(args.directory);record=read_record(directory);app=current(record)
    assert record['schema_migration']['status']=='pass' and not record['built_source_verification']['mismatches']
    override=Path(record['compose_files'][1]);old=override.read_text()
    assert old==(directory/'previous.override.yml').read_text(),'Compose changed since discovery'
    assert app['Config']['Image'] in old
    new,count=re.subn(r'(?m)^(\s*image:\s*).*$',lambda m:m[1]+record['image'],old);assert count==1
    compose=['docker','compose','-p',record['compose_project']]
    for file in record['compose_files']:compose+=['-f',file]
    rollback='''#!/bin/bash
set -euo pipefail
current_id=$(docker inspect roll-drauf-vtt-app-1 --format '{{.Image}}')
if [[ "$current_id" == BASE_ID ]]; then exit 0; fi
current_image=$(docker inspect roll-drauf-vtt-app-1 --format '{{.Config.Image}}')
if [[ "$current_image" != NEW_IMAGE ]]; then echo 'Unexpected app image; reconcile before rollback.' >&2; exit 1; fi
cp -p PREVIOUS OVERRIDE
COMPOSE up -d --no-deps --no-build app
'''
    replacements={'BASE_ID':shlex.quote(record['base_image_id']),'NEW_IMAGE':shlex.quote(record['image']),
                  'PREVIOUS':shlex.quote(str(directory/'previous.override.yml')),'OVERRIDE':shlex.quote(str(override)),
                  'COMPOSE':shlex.join(compose)}
    for key,value in replacements.items():rollback=rollback.replace(key,value)
    (directory/'rollback.sh').write_text(rollback);(directory/'rollback.sh').chmod(0o700)
    run(['bash','-n',str(directory/'rollback.sh')])
    override.write_text(new)
    try:run(compose+['up','-d','--no-deps','--no-build','app'])
    except Exception:
        override.write_text(old);raise
    healthy=None
    for attempt in range(20):
        try:
            with urllib.request.urlopen('https://vtt.roll-drauf.de/health/live',timeout=5) as response:healthy=json.load(response)
            if healthy.get('status')=='ok':break
        except Exception:pass
        time.sleep(1)
    assert healthy and healthy.get('status')=='ok','Live health failed; use recorded rollback'
    actual=inspect('roll-drauf-vtt-app-1');assert actual['Image']==record['image_id']
    unchanged=all(inspect(name)['Id']==before['id'] and inspect(name)['State']['StartedAt']==before['started_at'] for name,before in record['other_services_before'].items())
    assert unchanged,'Another VTT service changed identity/start time'
    record.update(deployed_at=actual['State']['StartedAt'],health=healthy,other_services_unchanged=unchanged,
                  rollback=str(directory/'rollback.sh'),rollback_syntax_checked=True,rollback_executed=False)
    save(directory,record)
    print(json.dumps({'status':'deployed_pending_live_journey','image':record['image'],'image_id':actual['Image'],'other_services_unchanged':unchanged}))


parser=argparse.ArgumentParser();commands=parser.add_subparsers(dest='command',required=True)
p=commands.add_parser('prepare');p.add_argument('--package',required=True);p.add_argument('--base-source',required=True);p.add_argument('--expected-image',required=True);p.add_argument('--expected-revision')
p=commands.add_parser('schema');p.add_argument('directory');p.add_argument('--model',action='append',default=[])
p=commands.add_parser('activate');p.add_argument('directory')
args=parser.parse_args();{'prepare':prepare,'schema':schema,'activate':activate}[args.command](args)
