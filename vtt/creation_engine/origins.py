"""Bounded conversion of an Eagle Background/Feat plus an explicit VTT supplement."""
import math
from vtt.rules_content.origin_profiles import SCHEMA
from .species import _Report,_empty,_dict,_edition,plain_text,_ENRICHER

SUPPLEMENT_SCHEMA='roll-drauf.origin-supplement.v1'
ABILITIES={'str','dex','con','int','wis','cha'}


def inspect(source,supplement,*,data,pack=None):
    report=_Report();source=source if isinstance(source,dict) else {}
    system=_dict(source.get('system'));kind=source.get('type')
    def block(path,message):report.add(path,'blocked','unsupported',message)
    if kind not in ('background','feat'):block('type','Wähle in Eagle einen Hintergrund oder ein Merkmal (Feat).')
    name=source.get('name')
    if not isinstance(name,str) or not 1<=len(name.strip())<=100:block('name','Name mit 1 bis 100 Zeichen erwartet.')
    edition=_edition(system,pack,report)
    for key,value in system.items():
        if key not in ('description','source','identifier') and not _empty(value):
            block('system.'+key,'Dieses Eagle-Regelfeld wird noch nicht ausgeführt. Entferne es und definiere unterstützte Regeln im VTT-Zusatz.')
    if not _empty(source.get('effects')):block('effects','Active Effects werden nicht ausgeführt. Entferne sie vor Veröffentlichung.')
    description=_dict(system.get('description'))
    for key,value in description.items():
        if key!='value' and not _empty(value):block('system.description.'+key,'Dieser Beschreibungsteil wird nicht übernommen.')
    raw=description.get('value','')
    if not isinstance(raw,str) or _ENRICHER.search(raw if isinstance(raw,str) else ''):block('system.description.value','Nur Beschreibungstext ohne Inline-Würfe oder Foundry-Verweise.')
    text=plain_text(raw)
    if len(text)>6000:block('system.description.value','Beschreibung auf 6000 Zeichen kürzen.')
    elif text:report.add('system.description.value','narrative','text','Beschreibung wird als Klartext angezeigt; sie erzeugt keine Regeln.')
    supplement=supplement if isinstance(supplement,dict) else {}
    fields={'schema','abilities','skills','toolId','featId'} if kind=='background' else {'schema','category','minLevel','prerequisite','grants'}
    if set(supplement)!=fields or supplement.get('schema')!=SUPPLEMENT_SCHEMA:
        block('supplement','Unbekannte oder fehlende Zusatzfelder; verwende das beschriftete VTT-Formular.')
        return {'playable':False,'edition':edition,'entries':report.entries,'profile':None}
    entry={'name':name}
    if kind=='background':
        abilities=supplement['abilities'];skills=supplement['skills'];tool=supplement['toolId']
        known_skills={row['id'] for row in data['skills']}
        if not isinstance(abilities,list) or len(abilities)!=3 or any(not isinstance(a,str) or a not in ABILITIES for a in abilities) or len(set(abilities))!=3:
            block('supplement.abilities','Genau drei verschiedene Attribute wählen.')
        if not isinstance(skills,list) or len(skills)!=2 or any(not isinstance(a,str) or a not in known_skills for a in skills) or len(set(skills))!=2:
            block('supplement.skills','Genau zwei verschiedene Fertigkeiten wählen.')
        tools={row['id'] for row in data['equipment']['items'] if row.get('category') in ('tool','tools') or row['id'].startswith('equipment.tools.')}
        if tool is not None and (not isinstance(tool,str) or tool not in tools):block('supplement.toolId','Werkzeug muss aus dem Regelkatalog stammen oder leer bleiben.')
        fid=supplement['featId']
        feat=next((row for row in data['feats'] if row['id']==fid),None) if isinstance(fid,str) else None
        if feat is None or feat['category']!='Herkunftstalent':block('supplement.featId','Ein freigegebenes Herkunftstalent wählen.')
        entry.update(abilities=abilities,skills=skills,tool=tool,toolChoice=None,featId=fid,
            feat=feat['name'] if feat else '',featChoice=None,
            startingEquipment={'B':[{'kind':'coins','coin':'GM','amount':50}]})
        report.add('supplement.startingEquipment','converted','coins','Startausrüstung dieses Hintergrunds: Geldpaket B, 50 GM.')
    elif kind=='feat':
        category=supplement['category'];level=supplement['minLevel'];need=supplement['prerequisite']
        if category not in ('origin','general'):block('supplement.category','Herkunftstalent oder allgemeines Talent wählen.')
        if type(level) is not int or not (1<=level<=20) or (category=='origin' and level!=1) or (category=='general' and level<4):
            block('supplement.minLevel','Herkunftstalent: Stufe 1; allgemeines Talent: Mindeststufe 4 bis 20.')
        if need is not None and (not isinstance(need,dict) or set(need)!= {'ability','min'} or not isinstance(need.get('ability'),str) or need.get('ability') not in ABILITIES or type(need.get('min')) is not int or not 3<=need['min']<=20):
            block('supplement.prerequisite','Attributsvoraussetzung: bekanntes Attribut, Mindestwert 3 bis 20.')
        if category=='origin' and need is not None:block('supplement.prerequisite','Herkunftstalente haben keine zusätzliche Voraussetzung.')
        grants=supplement['grants'];clean=[];seen=set()
        if not isinstance(grants,list) or len(grants)>12:
            block('supplement.grants','Höchstens zwölf unterstützte Grants.');grants=[]
        skills={row['id'] for row in data['skills']}
        for index,grant in enumerate(grants):
            path=f'supplement.grants[{index}]'
            if not isinstance(grant,dict):block(path,'Grant-Objekt erwartet.');continue
            key=grant.get('kind')
            if not isinstance(key,str):block(path,'Grant-Art muss eine bekannte Kennung sein.');continue
            target=(key,grant.get('skill') if isinstance(grant.get('skill'),str) else None)
            if target in seen:block(path,'Ein Grant pro Ziel; doppelte Beiträge entfernen.');continue
            seen.add(target)
            if key=='skill_proficiency':
                valid=set(grant)=={'kind','skill'} and isinstance(grant.get('skill'),str) and grant['skill'] in skills
            elif key=='initiative_pb':valid=set(grant)=={'kind'}
            elif key in ('ac','initiative','speed_meters','hp_per_level'):
                value=grant.get('value');limit={'ac':5,'initiative':10,'speed_meters':30,'hp_per_level':10}[key]
                valid=set(grant)=={'kind','value'} and type(value) in (int,float) and math.isfinite(value) and 0<value<=limit and (key=='speed_meters' or type(value) is int)
            else:valid=False
            if not valid:block(path,'Unbekannter Grant, Formel oder Wert außerhalb der unterstützten Grenzen.');continue
            clean.append(grant)
            report.add(path,'converted','grant',key+' wird aus dieser Fassung einmal angewendet.')
        entry.update(category='Herkunftstalent' if category=='origin' else 'Allgemeines Talent',repeatable=False,
            prerequisite={'minLevel':level,'abilities':need,'requiresFeature':None,'raw':None},abilityIncrease=None,choices=[],mechanics=clean)
    playable=kind in ('background','feat') and edition=='2024' and not report.blocked
    if playable:report.add('name','converted','profile','Typisierte Fassung: '+name.strip())
    return {'playable':playable,'edition':edition,'entries':report.entries,
        'profile':{'schema':SCHEMA,'edition':'2024','kind':kind,'description':text,'entry':entry} if playable else None}
