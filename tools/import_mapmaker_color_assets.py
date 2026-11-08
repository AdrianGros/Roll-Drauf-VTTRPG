#!/usr/bin/env python3
"""Import the 17 reviewed artist packs in four batches. Requires Pillow; SVGs use Playwright.
Archive bytes are pinned. Nothing is executed from downloaded archives.
"""
import argparse,hashlib,io,json,re,tarfile,urllib.request,zipfile
from pathlib import Path
from PIL import Image
from mapmaker_catalog import ASSETS,rebuild

def sha(b):return hashlib.sha256(b).hexdigest()
def write_json(p,v):p.write_text(json.dumps(v,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
def members(path):
    if path.name.endswith('.zip'):
        with zipfile.ZipFile(path) as z:
            for n in z.namelist():
                if not n.endswith('/'):yield n,z.read(n)
    elif path.name.endswith('.gz'):
        with tarfile.open(path) as z:
            for m in z.getmembers():
                if m.isfile():yield m.name,z.extractfile(m).read()
    else:yield path.name,path.read_bytes()
def group(n):
    s=n.lower()
    if any(v in s for v in ('preview','sample','example','_ test','_ palette','githubreadme','logo')):return 'Referenzen & Szenen'
    if s.startswith('characters/') or '/characters/' in s:return 'Figuren & Kleidung'
    if 'structure/structures/' in s or re.search(r'(?:^|/)house\d',s):return 'Fertige Häuser'
    if 'structure/' in s or any(v in s for v in ('castle','building','/structure/')):return 'Gebäude & Bauteile'
    if 'terrain' in s or 'tile' in s:return 'Gelände & Tiles'
    if 'fx/' in s:return 'Effekte'
    return 'Objekte & Ausstattung'
def run(source,cache):
    dest=ASSETS/source['id'];dest.mkdir(exist_ok=True)
    path=cache/source['archive']
    if not path.exists():
        with urllib.request.urlopen(source['archiveUrl'],timeout=90) as r:data=r.read(650_000_001)
        if len(data)>650_000_000:raise ValueError('Oversized archive')
        path.write_bytes(data)
    if sha(path.read_bytes())!=source['archiveSha256']:raise ValueError('Hash mismatch '+path.name)
    manifest={**source,'retrievedAt':'2026-11-08','provenanceUrl':source['source'],'textures':[],'stamps':[],'creditFiles':[]};coverage=[];docs=[];lpcsource=source['id']=='lpc-revised'
    for original,data in members(path):
        n=original.removeprefix('LPC-main/') if lpcsource else original
        if Path(n).is_absolute() or '..' in Path(n).parts:raise ValueError('Unsafe archive path')
        suffix=Path(n).suffix.lower();rec=dict(sourcePath=n,originalSha256=sha(data),bytes=len(data))
        if suffix in ('.txt','.md'):
            target='credit_'+sha(n.encode())[:20]+'.txt';(dest/target).write_bytes(data);manifest['creditFiles'].append(dict(sourcePath=n,file=target,sha256=sha(data)));docs.append((n,data));rec.update(status='evidence',file=target)
        elif suffix in ('.png','.svg'):
            if not data:rec.update(status='upstream-defect',reason='Originaldatei ist leer (0 Bytes); enthält keine Bilddaten.')
            elif 'logo' in Path(n).stem.lower():rec.update(status='excluded-branding',reason='Anbieterlogo, kein Kartenmotiv; Urheber wird in Credits genannt.')
            else:
                png=data
                if suffix=='.svg':
                    from render_mapmaker_svg import render_svg
                    tmp=cache/(sha(data)+'.png')
                    if not tmp.exists():render_svg(data,tmp)
                    png=tmp.read_bytes()
                with Image.open(io.BytesIO(png)) as img:
                    img.load();w,h=img.size
                if max(w,h)>4096:raise ValueError('Image exceeds reviewed bound: '+n)
                digest=sha(png);file=digest[:32]+'.png';target=dest/file
                if not target.exists():target.write_bytes(png)
                asset='color:'+source['id']+'_'+sha(n.encode())[:16]
                if len(asset.split(':')[1])>40:raise ValueError('ID too long')
                label=str(Path(n).with_suffix('')).replace('/',' · ')
                sheet=(lpcsource and group(n)!='Fertige Häuser') or source['id'].startswith('2dpixx-') or source['batch']==4 or ('sheet' in n.lower() or 'tilemap' in n.lower())
                grid=64 if lpcsource and n.startswith('Characters/') else source['grid']
                manifest['stamps'].append(dict(id=asset,file=file,label=label,group=group(n),search=n,w=w,h=h,defaultSize=min(256,max(16,max(w,h))),sha256=digest,originalPath=n,originalSha256=sha(data),sheet=sheet,grid=grid,pixelArt=source['pixelArt']))
                rec.update(status='placeable',asset=asset,file=file,rasterized=suffix=='.svg')
        else:rec.update(status='technical-source',reason='Metadaten/Alternativformat; Bildmotive sind über die PNG-/SVG-Einträge platzierbar.')
        coverage.append(rec)
    # Retain unmodified upstream text and an explicit selected license route.
    license_candidates=[(n,b) for n,b in docs if 'license' in n.lower() or (source['id']=='green-village' and 'squid' in n.lower()) or (lpcsource and n=='Credits.txt')]
    evidence='\n\n'.join(n+'\n'+b.decode('utf-8-sig',errors='replace') for n,b in license_candidates)
    proof=f"{source['name']}\n{source['author']}\nSelected license: {source['license']}\n{source['licenseUrl']}\nOriginal source: {source['source']}\nDownload: {source['archiveUrl']}\nSHA256: {source['archiveSha256']}\nProvenance: {source['provenance']}\n\n"+evidence
    (dest/'License.txt').write_text(proof,encoding='utf-8');manifest['licenseEvidenceSha256']=sha((dest/'License.txt').read_bytes())
    manifest['exportCredit']=proof+'\n\nOriginal credits:\n'+'\n\n'.join(n+'\n'+b.decode('utf-8-sig',errors='replace') for n,b in docs if 'credit' in n.lower())
    write_json(dest/'manifest.json',manifest);write_json(dest/'coverage.json',dict(source=source['source'],archiveSha256=source['archiveSha256'],files=coverage,placeable=sum(r['status']=='placeable' for r in coverage),defects=[r for r in coverage if r['status']=='upstream-defect']))
    print(source['id'],len(manifest['stamps']),'placeable',sum(r['status']=='upstream-defect' for r in coverage),'upstream defects',flush=True)
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('--cache',type=Path,required=True);a.add_argument('--batch',type=int,choices=range(1,5),required=True);v=a.parse_args();v.cache.mkdir(exist_ok=True,parents=True)
    for s in json.loads((ASSETS/'color-source-lock.json').read_text())['sources']:
        if s['batch']==v.batch:run(s,v.cache)
    rebuild()
