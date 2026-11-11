"""Pure immutable origin pins and the bounded grant vocabulary. No database reads."""
import copy
import re

SCHEMA = 'roll-drauf.origin-profile.v1'
PIN_SCHEMA = 'roll-drauf.origin-pin.v1'
ID_RE = re.compile(r'^homebrew\.(background|feat)\.([1-9][0-9]{0,9})$')


def parse_id(value):
    match = ID_RE.fullmatch(value) if isinstance(value,str) else None
    return (match[1],int(match[2])) if match else None


def selected_ids(state):
    """References in rule-bearing selection paths, never arbitrary prose."""
    state = state if isinstance(state,dict) else {}
    out = []
    def add(value):
        if isinstance(value,str) and value.startswith(('homebrew.background.','homebrew.feat.')) and value not in out:
            out.append(value)
    add((state.get('background') or {}).get('id') if isinstance(state.get('background'),dict) else None)
    choices = (state.get('species') or {}).get('choices',{}) if isinstance(state.get('species'),dict) else {}
    for value in choices.values() if isinstance(choices,dict) else []: add(value)
    for adv in state.get('advancements',[]) if isinstance(state.get('advancements'),list) else []:
        if isinstance(adv,dict) and adv.get('kind')=='feat': add(adv.get('featId'))
    for choices in (state.get('featureChoices') or {}).values() if isinstance(state.get('featureChoices'),dict) else []:
        if isinstance(choices,dict):
            for value in choices.values(): add(value)
    return out


def source_ref(entry):
    origin = entry.get('origin') or {}
    return {'id':entry['id'],'name':entry['name'],'revision':origin.get('revision'),
            'digest':origin.get('digest'),'source':entry.get('source')}


def entry_for(pin):
    profile = pin['profile']
    entry = copy.deepcopy(profile['entry'])
    entry['id'] = f"homebrew.{profile['kind']}.{pin['revisionId']}"
    entry['homebrew'] = True
    entry['origin'] = {key:copy.deepcopy(pin.get(key)) for key in ('revision','digest','scope','author','publishedAt')}
    entry['description'] = profile.get('description','')
    entry['source'] = {'sourceId':entry['id'],'revision':pin.get('revision'),'label':entry['name']}
    return entry


def pinned(block):
    raw = block.get('rulePins') if isinstance(block,dict) else None
    return [pin for pin in raw if isinstance(pin,dict) and pin.get('schema')==PIN_SCHEMA
            and type(pin.get('revisionId')) is int and isinstance(pin.get('profile'),dict)
            and pin['profile'].get('schema')==SCHEMA] if isinstance(raw,list) else []


def with_pins(data,pins):
    data = {**data}
    for pin in pins:
        entry = entry_for(pin)
        key = 'backgrounds' if pin['profile']['kind']=='background' else 'feats'
        data[key] = [row for row in data[key] if row['id']!=entry['id']] + [entry]
    return data
