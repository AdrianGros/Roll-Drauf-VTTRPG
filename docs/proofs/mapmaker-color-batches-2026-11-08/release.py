import pathlib,json,subprocess,sys,re,time,urllib.request,tarfile,hashlib
root=pathlib.Path('/home/admin/projects/roll-drauf-vtt');scratch=pathlib.Path('/tmp/mapmaker-color-batches-20261108');batch=int(sys.argv[1]);source=subprocess.check_output(['git','rev-parse',sys.argv[2]],cwd=root,text=True).strip();run=scratch/f'release-{batch}';run.mkdir(exist_ok=True);setup=pathlib.Path('/srv/migration/2026-10-07/setup');override=setup/'production.duck-species.override.yml';container='roll-drauf-vtt-app-1'
def inspect(*args):return json.loads(subprocess.check_output(['docker',*args]))[0]
live=inspect('inspect',container);base=live['Image'];base_tag=live['Config']['Image'];files=live['Config']['Labels']['com.docker.compose.project.config_files'].split(',');project=live['Config']['Labels']['com.docker.compose.project']
assert project=='migration-production' and files==[str(setup/'production.compose.json'),str(override)]
expected='sha256:85338a2498ce88cd1575cab86d19c53a2cffbd438d43e2fe27ea0190511bd127' if batch==1 else json.loads((scratch/f'release-{batch-1}'/'release-state.json').read_text())['runningImageId']
if batch==4 and (scratch/'production-reconciliation.json').exists():
 reconciliation=json.loads((scratch/'production-reconciliation.json').read_text());assert reconciliation['mapmakerMatchesBatch3'];expected=reconciliation['approvedBaseImage']
assert base==expected,'Live release changed; reconcile before proceeding'
image_tag=f'roll-drauf-vtt-app:mapmaker-color-b{batch}-20261108-{source[:8]}';rollback_tag=f'roll-drauf-vtt-app:before-mapmaker-color-b{batch}-20261108';subprocess.run(['docker','tag',base,rollback_tag],check=True)
build=run/'build';build.mkdir(exist_ok=True)
archive=subprocess.Popen(['git','archive',source,'vtt/static/mapmaker'],stdout=subprocess.PIPE,cwd=root)
with tarfile.open(fileobj=archive.stdout,mode='r|') as tf:tf.extractall(build,filter='data')
assert archive.wait()==0
(build/'Dockerfile').write_text(f'FROM {base_tag}\nLABEL org.opencontainers.image.revision="{source}" org.roll-drauf.slice="mapmaker-color-b{batch}-20261108"\nCOPY vtt/static/mapmaker/ /app/vtt/static/mapmaker/\n')
with (run/'build.log').open('w') as log:subprocess.run(['docker','build','-t',image_tag,str(build)],stdout=log,stderr=subprocess.STDOUT,check=True)
old_image=inspect('image','inspect',base);new_image=inspect('image','inspect',image_tag)
assert new_image['RootFS']['Layers'][:len(old_image['RootFS']['Layers'])]==old_image['RootFS']['Layers']
for k in ['Cmd','Entrypoint','Env','WorkingDir','User','ExposedPorts','Healthcheck']:assert old_image['Config'].get(k)==new_image['Config'].get(k),k
assert inspect('inspect',container)['Image']==base
ops=setup/f'mapmaker-color-b{batch}-20261108';ops.mkdir(exist_ok=True);backup=ops/'production.duck-species.override.before.yml';before=override.read_text();assert not backup.exists();backup.write_text(before)
updated,n=re.subn(r'(?m)^(\s+image:\s*)'+re.escape(base_tag)+r'\s*$',lambda m:m[1]+image_tag,before);assert n==1
state=dict(batch=batch,sourceCommit=source,baseRevision=live['Config']['Labels'].get('org.opencontainers.image.revision'),baseImage=base,baseTag=base_tag,imageTag=image_tag,builtImageId=new_image['Id'],rollbackTag=rollback_tag,overrideBackup=str(backup),composeProject=project,composeFiles=files,baseLayersPreserved=True,baseImageConfigPreserved=True)
cmd=['docker','compose','-p',project]
for f in files:cmd+=['-f',f]
cmd+=['up','-d','--no-deps','--no-build','app']
try:
 override.write_text(updated+'\n')
 with (run/'deploy.log').open('w') as log:subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,check=True)
 healthy=False
 for _ in range(20):
  try:
   with urllib.request.urlopen('https://vtt.roll-drauf.de/health/live',timeout=10) as r:healthy=r.status==200
  except Exception:pass
  if healthy:break
  time.sleep(2)
 if not healthy:raise RuntimeError('Public health failed')
 running=inspect('inspect',container);assert running['Image']==new_image['Id'];state.update(runningImageId=running['Image'],deployedAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'))
except Exception:
 override.write_text(before);subprocess.run(cmd,check=False);raise
(run/'release-state.json').write_text(json.dumps(state,indent=2)+'\n');(ops/'release-state.json').write_bytes((run/'release-state.json').read_bytes())
(ops/'rollback.sh').write_text('#!/bin/bash\nset -euo pipefail\n[ "$(docker inspect -f \'{{.Image}}\' roll-drauf-vtt-app-1)" = "'+state['runningImageId']+'" ] || { echo "Live image changed; reconcile before rollback"; exit 1; }\ncp '+str(backup)+' '+str(override)+'\n'+' '.join(cmd)+'\n')
(ops/'rollback.sh').chmod(0o700)
print(json.dumps(state,indent=2))
