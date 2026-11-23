"""Freeze a reviewable index from DOM observations and a source-text cross-check."""
import collections
import csv
import hashlib
import json
import re
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
captures=json.loads((HERE/'evidence/captures.json').read_text())
sources=[ROOT/'vtt/templates/play.html',ROOT/'vtt/play/surfaces/dm.json',*sorted((ROOT/'vtt/static/js').glob('play-*.js')),ROOT/'vtt/static/js/display-preferences.js',ROOT/'vtt/static/js/vtt-main-nav.js',*sorted((ROOT/'vtt/static/css').glob('play-*.css')),ROOT/'vtt/static/css/display-preferences.css']
lines=[(str(p.relative_to(ROOT)),n,line) for p in sources for n,line in enumerate(p.read_text().splitlines(),1)]
registry={}
def tidy(text):return re.sub(r'\s+',' ',text or '').strip()
def normalized(selector):
    selector=re.sub(r':nth-of-type\(\d+\)',':nth-of-type(*)',selector)
    selector=re.sub(r'#paSlot\d+','#paSlot*',selector)
    return selector
def caption(e):
    if e['tag']=='select':return e.get('label') or e.get('aria_label') or e.get('id') or 'Auswahl'
    return e.get('text') or e.get('label') or e.get('aria_label') or e.get('title') or e.get('placeholder') or e.get('id') or e['tag']
def references(e):
    ident=e.get('id')
    if ident:
        found=[{'file':p,'line':n,'match':'element-id'} for p,n,s in lines if ident in s]
        if found:return found[:3]
    text=tidy(e.get('direct_text') or e.get('text') or '')
    if len(text)>2:
        found=[{'file':p,'line':n,'match':'literal-text'} for p,n,s in lines if text in s]
        if found:return found[:3]
    roots=re.findall(r'#([\w-]+)',e.get('selector',''))
    for ident in roots:
        ident=ident.removeprefix('window-')
        found=[{'file':p,'line':n,'match':'region-anchor'} for p,n,s in lines if ident in s]
        if found:return found[:2]
    return []
def add(e,state,seat,facet=None,value=None):
    text=tidy(value if facet else caption(e))
    if not text and e['kind']=='information':return
    selector=normalized(e['selector'])
    discriminator=''
    if not e['id']:
        discriminator=text
        if e['kind']=='control' and ('token-marker' in e.get('classes','') or 'turn-item' in e.get('classes','')):
            discriminator='parameterized-entity-row'
        elif e['kind']=='control' and e.get('attributes'):
            discriminator=json.dumps(e['attributes'],sort_keys=True)
    key=(facet or e['kind'],e['id'] or selector,e['tag'],text if e['tag']=='option' or facet else discriminator)
    if key not in registry:
        registry[key]={'id':None,'category':'K' if e['kind']=='control' and not facet else 'I',
         'subtype':facet or ({'label':'Beschriftung','p':'Beschreibung/Status','option':'Optionsbeschriftung','summary':'Aufklappen','button':'Button','select':'Auswahlliste','input':'Eingabe','textarea':'Texteingabe'}.get(e['tag'],e['role'] or e['tag'])),
         'zone':e['zone'],'location':e['location'],'caption':text,'dom_id':e['id'],'selector':e['selector'],
         'associated_control':e.get('associated_control') or ('#'+e['id'] if facet and e['id'] else None),
         'direct_label':e.get('direct_text') if e['tag']=='label' else None,
         'role':e['role'],'input_type':e['type'],'source_references':references(e),'captions':[],
         'accessible_label':e.get('aria_label'),'visible_text':e.get('text'),
         'seats':[],'states':[],'visible_states':[],'observations':{},'attributes':e['attributes'],
         'source_only':False,'parameterized':':nth-of-type' in selector or e['tag']=='option',
         'options':e.get('options'),'description':e.get('title') or e.get('placeholder') or '',
         'label_quality':'not-applicable' if e['tag'] not in ['input','select','textarea'] else 'explicit' if e.get('label') or e.get('aria_label') else 'placeholder/title only' if e.get('title') or e.get('placeholder') else 'no explicit label observed'}
    row=registry[key]
    if e.get('options'):
        existing={(o['value'],o['text']) for o in row.get('options') or []}
        row['options']=(row.get('options') or [])+[o for o in e['options'] if (o['value'],o['text']) not in existing]
    for field,val in [('captions',text),('states',state),('seats',seat)]:
        if val not in row[field]:row[field].append(val)
    if e['visible']:
        if state not in row['visible_states']:row['visible_states'].append(state)
        row['observations'][state]={'rect':e['rect'],'in_viewport':e['in_viewport'],'disabled':e['disabled'],'style':e['style']}
for c in captures:
    for e in c['elements']:
        if e['tag']=='input' and e.get('type')=='hidden':continue
        e={**e,'selector':e['selector'].replace('html:nth-of-type(0)','html')}
        # Rule-derived catalogue entries are data; index the common option label once
        # per repeated slot family, while preserving each field's complete option set.
        add(e,c['state'],c['seat'])
        for facet,field in [('Tooltip','title'),('Platzhalter','placeholder')]:
            if e.get(field):add(e,c['state'],c['seat'],facet,e[field])

# Cross-check dormant template controls against the captured composition.
from html.parser import HTMLParser
class Controls(HTMLParser):
    def __init__(self):super().__init__();self.controls=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag in ['button','input','select','textarea','summary'] and a.get('id') and a.get('type')!='hidden':self.controls.append((tag,a))
static=[]
for p in [ROOT/'vtt/templates/play.html',ROOT/'vtt/play/surfaces/dm.json']:
    contents=[p.read_text()] if p.suffix=='.html' else list(json.loads(p.read_text()).values())
    for source in contents:
        parser=Controls();parser.feed(source);static.extend((str(p.relative_to(ROOT)),tag,a) for tag,a in parser.controls)
seen_ids={r['dom_id'] for r in registry.values() if r['category']=='K'}
missing=[]
for source,tag,attrs in static:
    ident=attrs['id']
    if ident in seen_ids:continue
    missing.append({'dom_id':ident,'tag':tag,'source':source})
    e={'id':ident,'selector':'#'+ident,'tag':tag,'kind':'control','zone':'R','location':'Quelltext-Altcontainer/bedingtes Template; im Audit nicht montiert','text':attrs.get('aria-label') or attrs.get('title') or attrs.get('placeholder') or ident,'direct_text':'','aria_label':attrs.get('aria-label'),'label':'','title':attrs.get('title'),'placeholder':attrs.get('placeholder'),'role':attrs.get('role'),'type':attrs.get('type'),'attributes':{},'visible':False,'associated_control':None}
    add(e,'source-only','unverified')
    for r in registry.values():
        if r['dom_id']==ident:r['source_only']=True

# Feedback and confirmation strings can be absent from every successful journey.
# Keep them in a separate indexed appendix, with code location and no claimed pixels.
observed_text=' '.join(t for row in registry.values() for t in row['captions'])
source_strings=[]
seen_strings=set()
pattern=re.compile(r'\b(?:VTTUi(?:HTML)?|uiText|tr|text)\(\s*("(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\')')
for path,n,line in lines:
    for m in pattern.finditer(line):
        literal=m.group(1)
        try:text=json.loads(literal) if literal[0]=='"' else literal[1:-1].replace("\\'", "'").replace('\\n','\n')
        except ValueError:continue
        text=tidy(text)
        if len(text)<3 or len(text)>650 or text in observed_text or text in seen_strings:continue
        seen_strings.add(text)
        source_strings.append({'id':f'PT-Q-{len(source_strings)+1:03}','category':'I','subtype':'Quelltext-Text (Feedback/Bestätigung/bedingte Beschriftung)','caption':text,'location':path+':'+str(n),'verified_on_screen':False,'note':'Bildschirmposition erst beim auslösenden Zustand bestimmbar; kein zusätzlicher sichtbarer Button gezählt.'})

zone_counter=collections.Counter()
items=[]
for row in registry.values():
    zone_counter[row['zone']]+=1
    row['id']=f"PT-{row['zone']}-{zone_counter[row['zone']]:03}"
    # Keep the frozen observation identity; separate a field's name from its
    # option data instead of presenting DOM textContent as one combined label.
    if row.get('direct_label'):row['caption']=row['direct_label']
    elif row['subtype']=='Auswahlliste' and row.get('options'):
        position=row['caption'].find(row['options'][0]['text'])
        if position>0:row['caption']=row['caption'][:position].strip()
    items.append(row)
result={'schema':1,'source_revision':'a6abcce9e34b289efb88cb525a0c4c3ae87037e4','index_policy':'Frozen research ledger; do not renumber existing entries when extending. K=Kontrollelement, I=Informationselement. Repeated entity rows are families, not feature counts.','items':items,'conditional_source_texts':source_strings,'source_template_controls_not_mounted':missing}
parts=[]
for name,value in result.items():
    encoded='[\n'+',\n'.join(json.dumps(row,ensure_ascii=False,separators=(',',':')) for row in value)+'\n]' if name in ['items','conditional_source_texts'] else json.dumps(value,ensure_ascii=False)
    parts.append(json.dumps(name)+': '+encoded)
(HERE/'inventory.json').write_text('{\n'+',\n'.join(parts)+'\n}\n')
with (HERE/'inventory.csv').open('w',newline='') as f:
    fields=['Index','Kategorie','Untertyp','Text','Zugaenglicher Name','Ort','DOM','Selektor','Rollen','Sichtbare Zustaende','Quelle','Beschriftung','Beschreibung']
    w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
    for r in items:w.writerow(dict(zip(fields,[r['id'],r['category'],r['subtype'],r['caption'],r.get('accessible_label') or '',r['location'],r['dom_id'],r['selector'],','.join(r['seats']),','.join(r['visible_states']),'; '.join(p['file']+':'+str(p['line']) for p in r['source_references']),r['label_quality'],r['description']])))
    for r in source_strings:w.writerow({'Index':r['id'],'Kategorie':'I','Untertyp':r['subtype'],'Text':r['caption'],'Ort':r['location'],'Quelle':r['location'],'Beschreibung':r['note']})
counts={'indexed_DOM_families':len(items),'controls':sum(r['category']=='K' for r in items),'information':sum(r['category']=='I' for r in items),'conditional_source_texts':len(source_strings),'not_mounted_template_controls':len(missing),'by_zone':dict(zone_counter),'captured_states':len(captures),'sources':[{ 'path':str(p.relative_to(ROOT)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sources]}
(HERE/'inventory-summary.json').write_text(json.dumps(counts,indent=2)+'\n')
footer=[r for r in items if r['zone']=='B' and r['category']=='K']
md=['# Index des unteren Menübandes','', 'K = Kontrollelement; zugehörige Labels, Tooltips und Hilfetexte besitzen eigene I-Einträge im CSV/JSON. Sichtbarkeit gilt für den erfassten Zustand, nicht für jede Sitzung.','', '| Index | Beschriftung | Selektor | Funktionstyp | Sichtbarkeit in DM-Grundansicht |','|---|---|---|---|---|']
for row in footer:
    attrs=row['attributes'];ident=row['dom_id'] or ''
    kind='Werkzeugmodus' if 'data-tool' in attrs else 'Ansichtsschalter' if ident=='btnVisionToggle' else 'Interaktionsschalter' if ident=='btnMeasureSnap' else 'Navigation/Menü' if ident=='btnBack' else 'Fensteröffner'
    visibility='Altcontainer; im Freifenstermodus deaktiviert' if ident=='btnTableSheet' else 'sichtbar' if 'dm-desktop-baseline' in row['visible_states'] else 'kontextabhängig/verborgen'
    md.append(f"| {row['id']} | {row['caption']} | `{row['selector']}` | {kind} | {visibility} |")
(HERE/'footer-index.md').write_text('\n'.join(md)+'\n')
print(json.dumps(counts,indent=2))
