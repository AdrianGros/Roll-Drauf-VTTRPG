"""Render and verify documentation only. Run build_reconciled_spec.py and verify_reconciliation.py first."""
from pathlib import Path
import hashlib
import html
import json
import re
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from urllib.parse import urldefrag

import markdown
import weasyprint

ROOT = Path(__file__).resolve().parent
STEM = 'creation-engine-v1.2'
CSS = """
@page {
  size: A4; margin: 18mm 17mm 19mm;
  @top-left { content: 'ROLL DRAUF  /  CREATION ENGINE'; color: #607581;
    font: 8pt 'DejaVu Sans', sans-serif; }
  @top-right { content: 'v1.2 · RECONCILED'; color: #607581;
    font: 8pt 'DejaVu Sans', sans-serif; }
  @bottom-left { content: 'Approved baseline + scoped research · 25 September 2026'; color: #607581;
    font: 8pt 'DejaVu Sans', sans-serif; }
  @bottom-right { content: counter(page) ' / ' counter(pages); color: #607581;
    font: 8pt 'DejaVu Sans', sans-serif; }
}
body { font: 9.6pt/1.43 'DejaVu Sans', sans-serif; color: #22313d; }
h1 { font-size: 25pt; line-height: 1.15; color: #163c4d; margin: 5mm 0; }
h2 { font-size: 14pt; line-height: 1.3; color: #163c4d; margin: 7mm 0 3mm;
     border-bottom: 1pt solid #d4e4e8; padding-bottom: 2mm; }
h3 { font-size: 11.3pt; line-height: 1.3; color: #225d6a; margin: 5mm 0 2mm; }
h1,h2,h3,h4 { break-after: avoid; }
p { margin: 2.3mm 0; orphans: 3; widows: 3; }
a { color: #176477; text-decoration: none; overflow-wrap: anywhere; }
strong { color: #143343; }
li { margin: 1.2mm 0; }
ul,ol { padding-left: 5.5mm; }
code { font: 8pt 'DejaVu Sans Mono', monospace; overflow-wrap: anywhere; }
pre { white-space: pre-wrap; padding: 3mm; background: #f1f5f7; }
table { border-collapse: collapse; width: 100%; table-layout: fixed;
        margin: 3mm 0; font-size: 8.4pt; line-height: 1.38; }
th { background: #e8f1f3; color: #163c4d; font-weight: bold; text-align: left; }
th,td { padding: 1.9mm 2mm; border-bottom: .5pt solid #d5dee3;
        vertical-align: top; overflow-wrap: anywhere; }
th:first-child,td:first-child { width: 24%; }
table.acceptance th:first-child,table.acceptance td:first-child { width: 7%; }
table.findings th:first-child,table.findings td:first-child { width: 9%; }
table code { font-size: 7.6pt; }
tr { break-inside: avoid; }
thead { display: table-header-group; }
h4 { font-size: 10.2pt; color: #225d6a; margin: 4mm 0 2mm; }
.contents { break-before: page; break-after: page; font-size: 9.5pt; }
.toc ul { list-style: none; padding: 0; }
.toc li { margin: 2.2mm 0; }
.toc a::after { content: leader('.') target-counter(attr(href), page); }
@media screen {
  body { max-width: 1000px; margin: 28px auto; padding: 24px; }
  h1 { font-size: 34px; }
  .toc { background: #f1f5f7; padding: 18px; }
  .toc a::after { content: ''; }
}
"""

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def normalized(url):
    return urldefrag(html.unescape(url))[0].rstrip('/')

def render(stem, toc=False):
    source = (ROOT / (stem + '.md')).read_text()
    md = markdown.Markdown(extensions=['tables', 'fenced_code', 'sane_lists', 'toc'],
                           extension_configs={'toc': {'toc_depth': '2-2'}})
    body = md.convert(source)
    if toc:
        body = re.sub(r'(<h2 id="1-[^"]+">)',
                      '<nav class="contents"><h2>Contents</h2>' + md.toc + '</nav>\\1', body, count=1)
        # The document subtitle is not a numbered section.
        body = re.sub(r'<li><a href="#research-and-technical-specification-v12[^"]*">.*?</a></li>', '', body)
    body = re.sub(r'<table>(\s*<thead>\s*<tr>\s*<th>ID</th>)', r'<table class="acceptance">\1', body)
    body = re.sub(r'<table>(\s*<thead>\s*<tr>\s*<th>Finding</th>)', r'<table class="findings">\1', body)
    title = 'Roll Drauf Creation Engine v1.2' + (' — reconciliation report' if 'reconciliation-report' in stem else ' — reconciled edition')
    document = ("<!doctype html><html lang='en'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width, initial-scale=1'>"
                f"<title>{html.escape(title)}</title><style>{CSS}</style></head><body>{body}</body></html>")
    (ROOT / (stem + '.html')).write_text(document)
    pdf = ROOT / (stem + '.pdf')
    weasyprint.HTML(string=document, base_url=str(ROOT)).write_pdf(pdf)
    with tempfile.TemporaryDirectory(prefix='ce-spec-render-') as folder:
        bbox, text = Path(folder) / 'bounds.html', Path(folder) / 'rendered.txt'
        subprocess.run(['pdftotext', '-bbox', str(pdf), str(bbox)], check=True)
        subprocess.run(['pdftotext', '-layout', str(pdf), str(text)], check=True)
        tree = ET.parse(bbox)
        ns = {'x': 'http://www.w3.org/1999/xhtml'}
        pages = tree.findall('.//x:page', ns)
        outside = []
        for n, page in enumerate(pages, 1):
            width, height = float(page.attrib['width']), float(page.attrib['height'])
            for word in page.findall('x:word', ns):
                a = word.attrib
                if (float(a['xMin']) < 0 or float(a['yMin']) < 0 or
                        float(a['xMax']) > width or float(a['yMax']) > height):
                    outside.append({'page': n, 'text': word.text})
        assert not outside, outside
        rendered = text.read_text()
        result = {'pages': len(pages), 'words_checked_for_page_bounds': len(tree.findall('.//x:word', ns)),
                  'words_outside_page': outside, 'sha256': digest(pdf)}
    return rendered, result

def main():
    source=(ROOT/(STEM+'.md')).read_text()
    verification=json.loads((ROOT/(STEM+'-verification.json')).read_text())
    assert verification['spec_sha256']==digest(ROOT/(STEM+'.md')), 'Run verify_reconciliation.py first'
    rendered, full=render(STEM,toc=True)
    assert full['words_checked_for_page_bounds'] > 20000
    catalogue=json.loads((ROOT/(STEM+'-acceptance.json')).read_text())
    expected={x['id'] for x in catalogue['approved_cases']+catalogue['proposed_cases']}
    expected.update(x['id'] for x in catalogue['requirements'])
    assert all(x in rendered for x in expected)
    report_text, report=render(STEM+'-reconciliation-report')
    assert 'G1 remains in Deploy' in report_text
    assert 'contextToken' in rendered and 'sourceInstance' in rendered
    verification.update({'pdf':full,'reconciliation_report_pdf':report,
        'all_acceptance_and_requirement_ids_in_pdf':True,
        'rendering_tools':{'Python-Markdown':markdown.__version__,'WeasyPrint':weasyprint.__version__},
        'visual_review':'Pending sampled inspection of this final build.'})
    (ROOT/(STEM+'-verification.json')).write_text(json.dumps(verification,indent=2)+'\n')
    print(json.dumps({'spec_pdf':full,'report_pdf':report},indent=2))

if __name__=='__main__': main()
