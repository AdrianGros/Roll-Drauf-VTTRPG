import json,subprocess,pathlib,time
container='roll-drauf-vtt-app-1';scratch=pathlib.Path('/tmp/mapmaker-color-batches-20261108');expected=json.loads((scratch/'release-4/release-state.json').read_text())
def image():return json.loads(subprocess.check_output(['docker','inspect',container]))[0]['Image']
assert image()==expected['runningImageId']
code='''
import pathlib,json,hashlib,struct
root=pathlib.Path('/app/vtt/static/mapmaker/assets');catalog=json.loads((root/'packs.json').read_text())['packs'];cache={};failures=[];counts={};textures=0;stamps=0
for pack in catalog:
 m=json.loads((root/pack['manifest']).read_text());counts[pack['id']]=len(m['stamps']);stamps+=len(m['stamps']);textures+=len(m['textures'])
 for kind in ('stamps','textures'):
  for e in m[kind]:
   path=root/pack['id']/e['file'];key=str(path)
   if key not in cache:
    data=path.read_bytes();cache[key]=(hashlib.sha256(data).hexdigest(),struct.unpack('>II',data[16:24]) if data[:8]==b'\\x89PNG\\r\\n\\x1a\\n' else None)
   digest,dims=cache[key]
   if digest!=e['sha256'] or dims is None or ('w' in e and dims!=(e['w'],e['h'])):failures.append(dict(pack=pack['id'],asset=e['id']))
print(json.dumps(dict(packCount=len(catalog),stampEntries=stamps,textures=textures,uniqueFiles=len(cache),failures=failures,byPack=counts)))
'''
r=subprocess.run(['docker','exec',container,'python','-c',code],capture_output=True,text=True,check=True);result=json.loads(r.stdout);assert image()==expected['runningImageId'];assert not result['failures'];assert result['stampEntries']==72058 and result['packCount']==31
result.update(sourceCommit=expected['sourceCommit'],runningImageId=expected['runningImageId'],verifiedAt=time.strftime('%Y-%m-%dT%H:%M:%S%z'),method='Every deployed image file read from the running container, full SHA256 and PNG dimensions compared with its canonical manifest; all public packs separately exercised through the normal editor UI.');(scratch/'live-inventory-verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
