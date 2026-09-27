"""Package the reconciled specification and frozen evidence. No application access."""
from pathlib import Path
import hashlib
import json
import zipfile

ROOT=Path(__file__).resolve().parent
STEM='creation-engine-v1.2'
ARCHIVE='Roll_Drauf_Creation_Engine_v1.2_Review_Package.zip'
MANIFEST=STEM+'-package-manifest.json'

def sha(data): return hashlib.sha256(data).hexdigest()
def main():
    verify=json.loads((ROOT/(STEM+'-verification.json')).read_text())
    assert verify['spec_sha256']==sha((ROOT/(STEM+'.md')).read_bytes())
    for key,file in [('pdf',STEM+'.pdf'),('reconciliation_report_pdf',STEM+'-reconciliation-report.pdf')]:
        digest=sha((ROOT/file).read_bytes())
        assert verify[key]['sha256']==digest
        assert verify['visual_review_hashes'][file]==digest
    assert 'Pending' not in verify['visual_review']
    paths=sorted(p for p in ROOT.rglob('*') if p.is_file() and p.suffix in {'.md','.json','.py','.html','.pdf'} and p.name!=MANIFEST)
    files=[{'path':str(p.relative_to(ROOT)),'bytes':p.stat().st_size,'sha256':sha(p.read_bytes())} for p in paths]
    manifest={'date':'2026-09-25','edition':'1.2-reconciled','active_contract':{'spec':'1.1.4','wire':'1.1.3','registry':'A1'},
      'phase':'G1 Deploy remains authorized','files':files,'archive':ARCHIVE,
      'scope':'Reading edition, bounded research proposals, reconciliation report and frozen evidence; not a new implementation authorization.',
      'manifest_self_hash_excluded':True,'archive_hash_location':ARCHIVE+'.sha256'}
    (ROOT/MANIFEST).write_text(json.dumps(manifest,indent=2)+'\n')
    with zipfile.ZipFile(ROOT/ARCHIVE,'w',compression=zipfile.ZIP_DEFLATED) as out:
        for file in paths+[ROOT/MANIFEST]: out.write(file,'creation-engine-v1.2/'+str(file.relative_to(ROOT)))
    with zipfile.ZipFile(ROOT/ARCHIVE) as z:
        assert z.testzip() is None
        assert len(z.namelist())==len(files)+1
        for file in files: assert sha(z.read('creation-engine-v1.2/'+file['path']))==file['sha256']
    checksum=sha((ROOT/ARCHIVE).read_bytes())
    (ROOT/(ARCHIVE+'.sha256')).write_text(checksum+'  '+ARCHIVE+'\n')
    print(json.dumps({'archive':str(ROOT/ARCHIVE),'members':len(files)+1,'sha256':checksum,'verified':True},indent=2))

if __name__=='__main__': main()
