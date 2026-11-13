"""Pure rules engine for SRD 5.2.1 characters (no Flask, no database).

`evaluate(data, state)` takes the creator data (creator-data.json) and a character *choice state*
and returns the derived sheet values plus a list of findings. Every finding that rests on a rule
carries the rule reference (ruleId + verbatim quote) from the creator data.
"""

from __future__ import annotations

import json
import math
import re
from functools import lru_cache

from .validator import CONTENT_ROOT

PACKAGE_DIR = CONTENT_ROOT / "srd-5.2.1-de"
ABILITY_IDS = ("str", "dex", "con", "int", "wis", "cha")
ERROR, INCOMPLETE, WARNING, INFO = "error", "incomplete", "warning", "info"
OVERRIDE_KEYS = {
    "hp.max", "armorClass", "speed", "initiative", "proficiencyBonus", "passivePerception",
    "spellSaveDc", "spellAttack",
} | {f"ability.{a}" for a in ABILITY_IDS}


@lru_cache(maxsize=1)
def load_creator_data() -> dict:
    return json.loads((PACKAGE_DIR / "generated" / "creator-data.json").read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- small pure helpers

def ability_modifier(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(data: dict, total_level: int) -> int:
    return data["levels"][max(1, min(20, total_level)) - 1]["proficiencyBonus"]


def level_for_xp(data: dict, xp: int) -> int:
    level = 1
    for row in data["levels"]:
        if xp >= row["xp"]:
            level = row["level"]
    return level


def point_buy_cost(data: dict, scores: list[int]) -> int | None:
    costs = data["abilityScoreMethods"]["pointBuy"]["costs"]
    try:
        return sum(costs[str(score)] for score in scores)
    except KeyError:
        return None


def roll_total(dice: list[int]) -> int:
    return sum(dice) - min(dice)


def caster_level(data: dict, levels_by_class: dict[str, int]) -> int:
    rule = data["multiclass"]["casterLevel"]
    full = sum(levels_by_class.get(key, 0) for key in rule["full"])
    half = sum(levels_by_class.get(key, 0) for key in rule["half"])
    return full + math.ceil(half / 2)


def _int(value, default=None):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def class_option_eligibility(data: dict, state: dict, class_key: str, class_level: int) -> dict:
    """One source of truth for creator, progression and their selection UIs."""
    options = {o["id"]: o for o in data["classOptions"] if o["classKey"] == class_key}
    selections = _dict(_dict(state.get("featureChoices")).get(class_key))
    definitions = next((c["featureChoices"] for c in data["classes"] if c["classKey"] == class_key), [])
    # Only active, correctly typed class-option buckets can satisfy a dependency.
    selected = {
        pick for choice in definitions if choice["kind"] == "class-option" and choice["level"] <= class_level
        for pick in _list(selections.get(choice["id"]))
        if isinstance(pick, str) and pick in options and options[pick]["kind"] == choice["optionKind"]
    }
    cantrips = _list(_dict(_dict(state.get("spells")).get(class_key)).get("cantrips"))
    known = [data["spells"][s] for s in cantrips if isinstance(s, str)
             and s in data["spellLists"].get(class_key, []) and data["spells"][s]["level"] == 0]
    result = {}

    def judge(option_id, visiting=()):
        if option_id in result:
            return result[option_id]
        option = options[option_id]
        rule = option["requirements"]
        reasons = []
        minimum = rule.get("minClassLevel", 1)
        if class_level < minimum:
            reasons.append(f"Erfordert Klassenstufe {minimum}.")
        dependency = rule.get("optionId")
        if dependency:
            if dependency not in options or option_id in visiting:
                reasons.append("Ungültige Regelabhängigkeit.")
            elif dependency not in selected or not judge(dependency, (*visiting, option_id))["eligible"]:
                reasons.append(f"Erfordert die gültige Anrufung „{options[dependency]['name']}“.")
        kind = rule.get("knownCantrip")
        if kind and not any(s.get("invocationCantrip", {}).get("damage") and
                            (kind != "attack-damage" or s["invocationCantrip"]["attack"]) for s in known):
            reasons.append("Erfordert einen bekannten Hexenmeister-Zaubertrick, der Schaden " +
                           ("über einen Angriffswurf bewirkt." if kind == "attack-damage" else "bewirkt."))
        result[option_id] = {"eligible": not reasons, "reasons": reasons}
        return result[option_id]

    for option_id in options:
        judge(option_id)
    return result


def _parse_meters(text) -> float:
    match = re.fullmatch(r"\+?([\d,]+) m", str(text).strip())
    return float(match.group(1).replace(",", ".")) if match else 0.0


class _Lookup(dict):
    """Dict whose membership tests and gets tolerate unhashable (user supplied) keys."""

    def __contains__(self, key):
        try:
            return dict.__contains__(self, key)
        except TypeError:
            return False

    def get(self, key, default=None):
        try:
            return dict.get(self, key, default)
        except TypeError:
            return default


class _Findings:
    def __init__(self):
        self.items: list[dict] = []

    def add(self, severity: str, code: str, message: str, path: str = "", ref: dict | None = None):
        self.items.append({"severity": severity, "code": code, "message": message, "path": path, "ref": ref})


# --------------------------------------------------------------------------- evaluation

def evaluate(data: dict, state: dict) -> dict:
    state = _dict(state)
    findings = _Findings()
    from .origin_profiles import source_ref
    provenance = {}
    def part(label,value,source=None):
        return {'label':label,'value':value,'source':source}
    def explain(key,label,total,parts,stacking='add'):
        provenance[key] = {'label':label,'total':total,'contributions':parts,'stacking':stacking}
    ability_parts = {a:[] for a in ABILITY_IDS}
    skill_sources = {}

    classes = _Lookup({entry["classKey"]: entry for entry in data["classes"]})
    feats = _Lookup({entry["id"]: entry for entry in data["feats"]})
    species_map = _Lookup({entry["id"]: entry for entry in data["species"]})
    background_map = _Lookup({entry["id"]: entry for entry in data["backgrounds"]})
    skills = _Lookup({entry["id"]: entry for entry in data["skills"]})
    armor_map = _Lookup({entry["id"]: entry for entry in data["equipment"]["armor"]})
    ability_names = {entry["id"]: entry["name"] for entry in data["abilities"]}

    # ---- level history
    history: list[dict] = []
    for index, raw in enumerate(_list(state.get("levels"))):
        raw = _dict(raw)
        key = raw.get("classKey")
        if key not in classes:
            findings.add(ERROR, "unknown-class", f"Unbekannte Klasse in Stufe {index + 1}.", f"levels[{index}].classKey")
            continue
        history.append({"classKey": key, "hp": raw.get("hp", "fixed")})
    total_level = len(history)
    if total_level == 0:
        findings.add(INCOMPLETE, "no-class", "Wähle eine Klasse.", "levels")
    if total_level > data["maxLevel"]:
        findings.add(ERROR, "level-cap", f"Die Gesamtstufe darf {data['maxLevel']} nicht überschreiten.", "levels")
        history = history[: data["maxLevel"]]
        total_level = data["maxLevel"]
    levels_by_class: dict[str, int] = {}
    for entry in history:
        levels_by_class[entry["classKey"]] = levels_by_class.get(entry["classKey"], 0) + 1
    pb = proficiency_bonus(data, total_level or 1)
    first_class = history[0]["classKey"] if history else None

    # ---- ability scores
    method = state.get("abilityMethod")
    base = {a: _int(_dict(state.get("abilityBase")).get(a)) for a in ABILITY_IDS}
    methods = data["abilityScoreMethods"]
    if any(value is None for value in base.values()):
        findings.add(INCOMPLETE, "ability-missing", "Weise allen sechs Attributen einen Wert zu.", "abilityBase")
        base = {a: (value if value is not None else 10) for a, value in base.items()}
    values = [base[a] for a in ABILITY_IDS]
    if method == "standard-array":
        if sorted(values, reverse=True) != methods["standardArray"]["values"]:
            findings.add(ERROR, "standard-array", "Der Standardsatz muss genau 15, 14, 13, 12, 10 und 8 enthalten.", "abilityBase", methods["standardArray"]["source"])
    elif method == "point-buy":
        cost = point_buy_cost(data, values)
        pb_rule = methods["pointBuy"]
        if cost is None:
            findings.add(ERROR, "point-buy-range", "Beim Punktekauf müssen alle Werte zwischen 8 und 15 liegen.", "abilityBase", pb_rule["source"])
        elif cost > pb_rule["budget"]:
            findings.add(ERROR, "point-buy-budget", f"Der Punktekauf kostet {cost} Punkte, erlaubt sind {pb_rule['budget']}.", "abilityBase", pb_rule["source"])
        elif cost < pb_rule["budget"]:
            findings.add(WARNING, "point-buy-unspent", f"Es sind {pb_rule['budget'] - cost} Punkte nicht verbraucht.", "abilityBase", pb_rule["source"])
    elif method == "roll":
        sets = [_list(row) for row in _list(state.get("abilityRolls"))]
        ok_dice = len(sets) == 6 and all(len(row) == 4 and all(_int(d) in range(1, 7) for d in row) for row in sets)
        if not ok_dice:
            findings.add(INCOMPLETE, "roll-missing", "Würfle sechsmal 4W6 und trage die Würfel ein.", "abilityRolls", methods["roll"]["source"])
        elif sorted(roll_total([int(d) for d in row]) for row in sets) != sorted(values):
            findings.add(ERROR, "roll-mismatch", "Die zugewiesenen Werte passen nicht zu den gewürfelten Ergebnissen (jeweils ohne den niedrigsten Würfel).", "abilityBase", methods["roll"]["source"])
    elif method == "manual":
        if any(not 1 <= v <= 20 for v in values):
            findings.add(ERROR, "manual-range", "Manuelle Attributswerte müssen zwischen 1 und 20 liegen.", "abilityBase")
        findings.add(INFO, "manual-method", "Manuelle Werte folgen keiner SRD-Methode.", "abilityMethod")
    else:
        findings.add(INCOMPLETE, "ability-method", "Wähle eine Methode zur Attributserstellung.", "abilityMethod")

    bonus = {a: 0 for a in ABILITY_IDS}
    background = background_map.get(_dict(state.get("background")).get("id"))
    background_state = _dict(state.get("background"))
    if background is None:
        findings.add(INCOMPLETE, "background-missing", "Wähle einen Hintergrund.", "background.id")
    else:
        increases = {a: _int(v, 0) for a, v in _dict(background_state.get("abilityBonus")).items() if _int(v, 0)}
        pattern = sorted(increases.values(), reverse=True)
        rule = methods["backgroundBonus"]
        if not increases:
            findings.add(INCOMPLETE, "background-bonus", "Verteile den Attributsbonus deines Hintergrunds (+2/+1 oder +1/+1/+1).", "background.abilityBonus", rule["source"])
        elif pattern not in rule["options"] or any(a not in background["abilities"] for a in increases):
            findings.add(ERROR, "background-bonus", "Der Bonus muss +2/+1 oder +1/+1/+1 auf die drei Attribute deines Hintergrunds betragen.", "background.abilityBonus", rule["source"])
        for a, value in increases.items():
            if a in bonus:
                bonus[a] += value
                ability_parts[a].append(part(background['name'],value,source_ref(background)))

    # ---- species
    species = species_map.get(_dict(state.get("species")).get("id"))
    species_choices = _dict(_dict(state.get("species")).get("choices"))
    if species is None:
        findings.add(INCOMPLETE, "species-missing", "Wähle eine Spezies.", "species.id")
    else:
        for choice in species["choices"]:
            if choice["id"] in species_choices:
                value = species_choices[choice["id"]]
                options = choice.get("options")
                if choice["kind"] == "feat-category":
                    feat = feats.get(value)
                    valid = feat is not None and feat["category"] == choice["category"]
                elif options:
                    valid = value in [o["id"] if isinstance(o, dict) else o for o in options]
                elif choice["kind"] == "skill":
                    valid = value in skills
                else:
                    valid = True
                if not valid:
                    findings.add(ERROR, "species-choice-invalid", f"Ungültige Wahl für „{choice['id']}“.", f"species.choices.{choice['id']}", choice.get("source"))
            elif choice["kind"] != "size" or len(species["sizes"]) > 1:
                findings.add(INCOMPLETE, "species-choice-missing", f"Treffe die Wahl „{choice['id']}“ für {species['name']}.", f"species.choices.{choice['id']}", choice.get("source"))

    # ---- advancements (ASI / feats)
    advancements = [_dict(a) for a in _list(state.get("advancements"))]
    taken_feats: list[str] = []
    if background and (background.get("featId") or background.get("feat")):
        origin = feats.get(background.get('featId')) if background.get('featId') else next((f for f in data["feats"] if f["name"] == background["feat"]), None)
        if origin:
            taken_feats.append(origin["id"])
    versatile = species_choices.get("versatile")
    if versatile in feats:
        taken_feats.append(versatile)
    used_slots: set[tuple[str, int]] = set()
    boon_targets: set[str] = set()
    for index, adv in enumerate(advancements):
        key, class_level = adv.get("classKey"), _int(adv.get("classLevel"))
        path = f"advancements[{index}]"
        if key not in classes or class_level is None or class_level > levels_by_class.get(key, 0):
            findings.add(ERROR, "advancement-slot", "Diese Verbesserung gehört zu keiner erreichten Klassenstufe.", path)
            continue
        entry = classes[key]
        if class_level not in entry["asiLevels"] and class_level != entry["epicBoonLevel"]:
            findings.add(ERROR, "advancement-slot", f"Auf {entry['name']}-Stufe {class_level} gibt es keine Attributswerterhöhung.", path)
            continue
        if (key, class_level) in used_slots:
            findings.add(ERROR, "advancement-duplicate", "Für diese Stufe ist bereits eine Verbesserung eingetragen.", path)
            continue
        used_slots.add((key, class_level))
        if adv.get("kind") == "feat":
            feat = feats.get(adv.get("featId"))
            if feat is None:
                findings.add(ERROR, "feat-unknown", "Unbekanntes Talent.", path)
                continue
            if feat["id"] in taken_feats and not feat["repeatable"]:
                findings.add(ERROR, "feat-repeat", f"„{feat['name']}“ kann nicht mehrfach gewählt werden.", path, feat["source"])
            taken_feats.append(feat["id"])
            if feat["abilityIncrease"]:
                target = adv.get("increaseAbility")
                allowed = feat["abilityIncrease"]["abilities"]
                if target is None or target not in ABILITY_IDS:
                    findings.add(INCOMPLETE, "feat-increase", f"Wähle das Attribut für „{feat['name']}“.", path, feat["abilityIncrease"]["source"])
                elif allowed != "any" and target not in allowed:
                    findings.add(ERROR, "feat-increase", "Dieses Attribut ist für das Talent nicht erlaubt.", path, feat["abilityIncrease"]["source"])
                else:
                    bonus[target] += 1
                    ability_parts[target].append(part(feat['name'],1,source_ref(feat)))
                    if feat["abilityIncrease"]["max"] > 20:
                        boon_targets.add(target)
        elif adv.get("kind") == "asi":
            increases = {a: _int(v, 0) for a, v in _dict(adv.get("increases")).items() if _int(v, 0)}
            pattern = sorted(increases.values(), reverse=True)
            if pattern not in ([2], [1, 1]) or any(a not in ABILITY_IDS for a in increases):
                findings.add(ERROR, "asi-pattern", "Erhöhe ein Attribut um 2 oder zwei Attribute um je 1.", path)
            else:
                for a, value in increases.items():
                    bonus[a] += value
                    ability_parts[a].append(part('Attributswerterhöhung',value,{'id':f'advancements.{index}','classKey':key,'classLevel':class_level}))
        else:
            findings.add(INCOMPLETE, "advancement-kind", "Wähle Attributswerterhöhung oder Talent.", path)

    # ---- final scores
    abilities = {}
    for a in ABILITY_IDS:
        cap = 30 if a in boon_targets else 20
        score = base[a] + bonus[a]
        if score > cap:
            findings.add(WARNING, "ability-cap", f"{ability_names[a]} überschreitet das Maximum von {cap} und wird auf {cap} begrenzt.", f"abilities.{a}", methods["backgroundBonus"]["source"] if cap == 20 else None)
            score = cap
        abilities[a] = {"base": base[a], "bonus": bonus[a], "score": score, "modifier": ability_modifier(score)}
        parts = [part('Grundwert',base[a],{'id':'abilityBase.'+a})]+ability_parts[a]
        if score != base[a]+bonus[a]: parts.append(part('Attributsmaximum',score-base[a]-bonus[a],{'id':'ability-cap'}))
        explain('ability.'+a,ability_names[a],score,parts,'add_then_cap')
        explain('modifier.'+a,ability_names[a]+' Modifikator',ability_modifier(score),
                [part('Abrunden((Attribut − 10) / 2)',ability_modifier(score),{'id':'ability.'+a})],'ability_modifier')
    # ---- required advancement slots
    for key, class_level in levels_by_class.items():
        entry = classes[key]
        for slot in sorted(set(entry["asiLevels"] + [entry["epicBoonLevel"]])):
            if slot <= class_level and (key, slot) not in used_slots:
                label = "Epische Gabe" if slot == entry["epicBoonLevel"] else "Attributswerterhöhung oder Talent"
                findings.add(INCOMPLETE, "advancement-missing", f"{entry['name']}-Stufe {slot}: {label} wählen.", f"advancements.{key}.{slot}")

    # ---- multiclass prerequisites
    order: list[str] = []
    for entry in history:
        if entry["classKey"] not in order:
            order.append(entry["classKey"])
    rule = data["multiclass"]["prerequisite"]
    if len(order) > 1:
        for key in order:
            need = classes[key]["primaryAbilities"]
            scores = [abilities[a]["score"] for a in need["abilities"]]
            met = any(s >= rule["minimumScore"] for s in scores) if need["mode"] == "any" else all(s >= rule["minimumScore"] for s in scores)
            if not met:
                findings.add(ERROR, "multiclass-prerequisite", f"Mehrklassigkeit: {classes[key]['name']} verlangt Hauptattribut(e) von mindestens {rule['minimumScore']}.", f"levels.{key}", rule["source"])

    # ---- subclasses
    subclass_state = _dict(state.get("subclasses"))
    chosen_subclass: dict[str, str] = {}
    for key, class_level in levels_by_class.items():
        entry = classes[key]
        if class_level >= entry["subclassLevels"][0]:
            value = subclass_state.get(key)
            if value is None:
                findings.add(INCOMPLETE, "subclass-missing", f"{entry['name']}: Unterklasse wählen (ab Stufe {entry['subclassLevels'][0]}).", f"subclasses.{key}")
            elif value not in entry["subclasses"]:
                findings.add(ERROR, "subclass-invalid", f"Ungültige Unterklasse für {entry['name']}.", f"subclasses.{key}")
            else:
                chosen_subclass[key] = value
        elif key in subclass_state:
            findings.add(WARNING, "subclass-early", f"{entry['name']}: Unterklasse erst ab Stufe {entry['subclassLevels'][0]}.", f"subclasses.{key}")

    # ---- skills and proficiencies
    proficiency = _Lookup()
    skill_state = _dict(state.get("skills"))
    class_skills = [s for s in _list(skill_state.get("class")) if isinstance(s, str)]
    expertise: list[str] = []
    if first_class:
        entry = classes[first_class]
        wanted = entry["skillChoices"]
        options = wanted["options"]
        if len(class_skills) < wanted["count"]:
            findings.add(INCOMPLETE, "class-skills", f"{entry['name']}: Wähle {wanted['count']} Fertigkeiten.", "skills.class")
        elif len(set(class_skills)) != wanted["count"] or any(s not in skills or (options and s not in options) for s in class_skills):
            findings.add(ERROR, "class-skills", f"{entry['name']}: Genau {wanted['count']} verschiedene Fertigkeiten der Klassenliste wählen.", "skills.class")
        for skill in class_skills:
            if skill in skills:
                proficiency[skill] = "proficient"
                skill_sources.setdefault(skill,[]).append({'id':'class.'+first_class,'name':entry['name']})
    if background:
        for skill in background["skills"]:
            if proficiency.get(skill) == "proficient":
                findings.add(WARNING, "skill-duplicate", f"„{skills[skill]['name']}“ kommt aus Klasse und Hintergrund; wähle für die Klassenfertigkeit eine andere.", "skills.class")
            proficiency[skill] = "proficient"
            skill_sources.setdefault(skill,[]).append(source_ref(background))
    multiclass_skills = _dict(skill_state.get("multiclass"))
    for key in order[1:]:
        wanted = classes[key]["multiclassGrants"].get("skillChoices")
        if not wanted:
            continue
        picks = [s for s in _list(multiclass_skills.get(key)) if isinstance(s, str)]
        options = classes[key]["skillChoices"]["options"] if wanted["from"] == "class" else []
        if len(picks) < wanted["count"]:
            findings.add(INCOMPLETE, "multiclass-skills", f"{classes[key]['name']} (Mehrklassigkeit): Wähle {wanted['count']} Fertigkeit.", f"skills.multiclass.{key}")
        elif len(set(picks)) != wanted["count"] or any(s not in skills or (options and s not in options) for s in picks):
            findings.add(ERROR, "multiclass-skills", f"{classes[key]['name']} (Mehrklassigkeit): Genau {wanted['count']} gültige Fertigkeit wählen.", f"skills.multiclass.{key}")
        for skill in picks:
            if skill in skills:
                if proficiency.get(skill) == "proficient":
                    findings.add(WARNING, "skill-duplicate", f"„{skills[skill]['name']}“ ist schon geübt; wähle für {classes[key]['name']} eine andere Fertigkeit.", f"skills.multiclass.{key}")
                proficiency[skill] = "proficient"
                skill_sources.setdefault(skill,[]).append({'id':'class.'+key,'name':classes[key]['name']})
    for skill in _list(skill_state.get("other")):
        if skill in skills:
            proficiency.setdefault(skill, "proficient")
    if species and any(c["id"] == "keen-senses" for c in species["choices"]):
        chosen = species_choices.get("keen-senses")
        if chosen in skills:
            proficiency.setdefault(chosen, "proficient")
        skill_sources.setdefault(chosen,[]).append(source_ref(species))
    if species and species["id"].endswith(".human") and species_choices.get("skillful") in skills:
        proficiency.setdefault(species_choices["skillful"], "proficient")
    # Published homebrew Species declare their grants on the choice itself (species_profiles.species_entry).
    for choice in species["choices"] if species else []:
        chosen = species_choices.get(choice["id"])
        if choice.get("grants") != "proficiency" or chosen not in skills or chosen not in (choice.get("options") or ()):
            continue
        if proficiency.get(chosen) == "proficient":
            findings.add(WARNING, "skill-duplicate", f"„{skills[chosen]['name']}“ ist schon geübt; wähle für {species['name']} eine andere Fertigkeit.", f"species.choices.{choice['id']}")
        proficiency.setdefault(chosen, "proficient")
    feature_state = _dict(state.get("featureChoices"))
    acquired_at = {fid:1 for fid in taken_feats if fid in feats and feats[fid]['category']=='Herkunftstalent'}
    for adv in advancements:
        fid=adv.get('featId');key=adv.get('classKey');nth=_int(adv.get('classLevel'))
        if adv.get('kind')!='feat' or fid not in feats or not nth:continue
        class_count=0
        for index,level in enumerate(history):
            if level['classKey']==key:class_count+=1
            if class_count==nth:
                acquired_at[fid]=index+1;break
        if feats[fid].get('homebrew') and feats[fid]['category']!='Allgemeines Talent':
            findings.add(ERROR,'homebrew-category','Für eine Verbesserung ist ein allgemeines Talent erforderlich.','advancements')
    for key,class_level in levels_by_class.items():
        for choice in classes[key]['featureChoices']:
            fid=_dict(feature_state.get(key)).get(choice['id'])
            if choice['kind']=='feat-category' and choice['level']<=class_level and isinstance(fid,str) and fid in feats and feats[fid]['category'].startswith(choice['category']):
                acquired_at[fid]=total_level
    homebrew = [feats[fid] for fid in sorted(acquired_at) if feats[fid].get('homebrew')]
    grants = []
    for feat in homebrew:
        prereq = feat['prerequisite']
        if acquired_at[feat['id']] < (prereq.get('minLevel') or 1):
            findings.add(ERROR,'homebrew-prerequisite',f"{feat['name']}: Mindeststufe nicht erreicht.",'advancements',feat.get('source'))
        need = prereq.get('abilities')
        if need and abilities[need['ability']]['score'] < need['min']:
            findings.add(ERROR,'homebrew-prerequisite',f"{feat['name']}: Attributsvoraussetzung nicht erfüllt.",'advancements',feat.get('source'))
        for grant in feat.get('mechanics',[]):
            grants.append((grant,source_ref(feat)))
            if grant['kind']=='skill_proficiency':
                proficiency.setdefault(grant['skill'],'proficient')
                skill_sources.setdefault(grant['skill'],[]).append(source_ref(feat))

    for skill in _list(skill_state.get("expertise")):
        if proficiency.get(skill) == "proficient" and skill not in expertise:
            expertise.append(skill)
        elif skill in skills:
            findings.add(ERROR, "expertise-without-proficiency", f"Expertise in „{skills[skill]['name']}“ setzt Übung voraus.", "skills.expertise")
    expected_expertise = 0
    for key, class_level in levels_by_class.items():
        for choice in classes[key]["featureChoices"]:
            if choice["kind"] == "expertise" and choice["level"] <= class_level:
                expected_expertise += choice.get("count", 0)
    if len(expertise) < expected_expertise:
        findings.add(INCOMPLETE, "expertise-missing", f"Wähle {expected_expertise - len(expertise)} weitere Expertise-Fertigkeit(en).", "skills.expertise")
    elif len(expertise) > expected_expertise:
        findings.add(ERROR, "expertise-extra", "Es wurden mehr Expertise-Fertigkeiten gewählt, als deine Klassen gewähren.", "skills.expertise")
    for skill in expertise:
        proficiency[skill] = "expertise"

    # ---- feature choices
    feature_state = _dict(state.get("featureChoices"))
    option_eligibility = {key: class_option_eligibility(data, state, key, level) for key, level in levels_by_class.items()}
    for key, class_level in levels_by_class.items():
        entry = classes[key]
        chosen = _dict(feature_state.get(key))
        for choice in entry["featureChoices"]:
            if choice["level"] > class_level or choice["kind"] == "expertise":
                continue
            value = chosen.get(choice["id"])
            path = f"featureChoices.{key}.{choice['id']}"
            if choice["kind"] == "option":
                if value is None:
                    findings.add(INCOMPLETE, "choice-missing", f"{entry['name']}: Wähle „{choice['id']}“.", path, choice["source"])
                elif value not in choice["options"]:
                    findings.add(ERROR, "choice-invalid", f"Ungültige Wahl für „{choice['id']}“.", path, choice["source"])
            elif choice["kind"] == "feat-category":
                feat = feats.get(value)
                if value is None:
                    findings.add(INCOMPLETE, "choice-missing", f"{entry['name']}: Wähle ein {choice['category']}.", path, choice["source"])
                elif feat is None or not feat["category"].startswith(choice["category"]):
                    findings.add(ERROR, "choice-invalid", f"Erwartet wird ein {choice['category']}.", path, choice["source"])
            elif choice["kind"] in {"weapon-mastery", "language", "class-option"}:
                need = choice.get("count") or _int(_dict(choice.get("countByLevel")).get(str(class_level)), 0)
                picks = _list(value)
                if len(picks) < need:
                    findings.add(INCOMPLETE, "choice-missing", f"{entry['name']}: Wähle {need} Einträge für „{choice['id']}“.", path, choice["source"])
                elif len(picks) > need or len(set(map(str, picks))) != len(picks):
                    findings.add(ERROR, "choice-invalid", f"Für „{choice['id']}“ sind genau {need} verschiedene Einträge erlaubt.", path, choice["source"])
                elif choice["kind"] == "weapon-mastery":
                    weapons = _Lookup({w["id"]: w for w in data["equipment"]["weapons"]})
                    for pick in picks:
                        if pick not in weapons:
                            findings.add(ERROR, "choice-invalid", "Unbekannte Waffe.", path, choice["source"])
                        elif not _weapon_allowed(entry, weapons[pick]):
                            findings.add(ERROR, "mastery-proficiency", f"Für „{weapons[pick]['name']}“ fehlt dir die Waffenübung.", path, choice["source"])
                elif choice["kind"] == "class-option":
                    options = _Lookup({o["id"]: o for o in data["classOptions"]})
                    for pick in picks:
                        option = options.get(pick)
                        if option is None or option["classKey"] != key or option["kind"] != choice["optionKind"] or (option["minClassLevel"] or 1) > class_level:
                            findings.add(ERROR, "choice-invalid", "Diese Option ist für deine Klassenstufe nicht verfügbar.", path, choice["source"])
                        elif not option_eligibility[key][pick]["eligible"]:
                            findings.add(ERROR, "class-option-prerequisite", f"{option['name']}: " + " ".join(option_eligibility[key][pick]["reasons"]), path, option["prerequisiteSource"])

    for key in levels_by_class:
        picks = [str(p) for value in _dict(feature_state.get(key)).values() if isinstance(value, list) for p in value]
        if len(set(picks)) != len(picks):
            findings.add(ERROR, "choice-duplicate", f"{classes[key]['name']}: Eine Option wurde mehrfach gewählt.", f"featureChoices.{key}")

    # ---- hit points
    hit_dice: dict[int, int] = {}
    hp_total, hp_breakdown = 0, []
    for index, entry in enumerate(history):
        die = classes[entry["classKey"]]["hitDie"]
        hit_dice[die] = hit_dice.get(die, 0) + 1
        con = abilities["con"]["modifier"]
        if index == 0:
            gain = die + con
            label = "Stufe 1: Trefferwürfel-Maximum + KON"
        elif entry["hp"] == "fixed":
            gain = max(1, die // 2 + 1 + con)
            label = "fester Wert + KON"
        else:
            roll = _int(entry["hp"])
            if roll is None or not 1 <= roll <= die:
                findings.add(ERROR, "hp-roll", f"Stufe {index + 1}: Der gewürfelte Wert muss zwischen 1 und {die} liegen.", f"levels[{index}].hp")
                roll = 1
            gain = max(1, roll + con)
            label = "gewürfelt + KON"
        hp_total += gain
        hp_breakdown.append({"level": index + 1, "classKey": entry["classKey"], "gain": gain, "label": label})
    for rule_bonus in data["hitPointBonuses"]:
        extra = 0
        if rule_bonus["origin"] == "species" and species and species["id"] == rule_bonus["speciesId"]:
            extra = rule_bonus["perCharacterLevel"] * total_level
        elif rule_bonus["origin"] == "subclass" and chosen_subclass.get(rule_bonus["classKey"]) == rule_bonus["subclass"]:
            class_level = levels_by_class.get(rule_bonus["classKey"], 0)
            if class_level >= rule_bonus["minClassLevel"]:
                extra = rule_bonus["flat"] + rule_bonus["perClassLevelAbove"] * (class_level - rule_bonus["minClassLevel"])
        if extra:
            hp_total += extra
            hp_breakdown.append({"level": None, "classKey": None, "gain": extra, "label": rule_bonus["id"], "ref": rule_bonus["source"]})

    for grant,source in grants:
        if grant['kind']=='hp_per_level':
            extra = grant['value'] * total_level
            hp_total += extra
            hp_breakdown.append({'level':None,'classKey':None,'gain':extra,'label':source['name'],'ref':source})
    explain('hp.max','Trefferpunkte',hp_total,[part(row['label'],row['gain'],row.get('ref') or {'id':'levels.'+str(row['level']),'classKey':row['classKey']}) for row in hp_breakdown])

    # ---- armor class, speed, initiative
    equipment = _dict(state.get("equipment"))
    armor_id = equipment.get("armor") if isinstance(equipment.get("armor"), str) else None
    armor = armor_map.get(armor_id) if armor_id else None
    if equipment.get("armor") and armor is None:
        findings.add(ERROR, "armor-unknown", "Unbekannte Rüstung.", "equipment.armor")
    shield = bool(equipment.get("shield"))
    if shield and not _armor_trained(classes, levels_by_class, first_class, "shield"):
        findings.add(WARNING, "shield-untrained", "Du bist mit Schilden nicht vertraut.", "equipment.shield")
    if armor and armor["category"] == "shield":
        findings.add(ERROR, "armor-is-shield", "Ein Schild gehört in das Schild-Feld, nicht in die Rüstung.", "equipment.armor")
        armor = None
    dex = abilities["dex"]["modifier"]
    shield_bonus = next((a["base"] for a in data["equipment"]["armor"] if a["category"] == "shield"), 2)
    if armor:
        dex_part = {"full": dex, "capped": min(dex, armor["dexCap"] or 0), "none": 0}[armor["dex"]]
        ac_value = armor["base"] + dex_part + (shield_bonus if shield else 0)
        ac_parts = [part(armor['name'],armor['base'],{'id':armor['id']}),part('GES nach Rüstungslimit',dex_part,{'id':'modifier.dex'})]
        ac_formula = f"{armor['name']}: {armor['base']} + GES (begrenzt: {armor['dex']}) + Schild"
        if armor["strengthRequirement"] and abilities["str"]["score"] < armor["strengthRequirement"]:
            findings.add(WARNING, "armor-strength", f"{armor['name']} verlangt Stärke {armor['strengthRequirement']}; ohne sie sinkt deine Bewegungsrate um 3 m.", "equipment.armor")
        if armor["stealthDisadvantage"]:
            findings.add(INFO, "armor-stealth", f"{armor['name']} gibt Nachteil auf Würfe auf Heimlichkeit.", "equipment.armor")
        trained = _armor_trained(classes, levels_by_class, first_class, armor["category"])
        if not trained:
            findings.add(WARNING, "armor-untrained", f"Du bist mit {armor['name']} nicht vertraut: Nachteil auf Attributs-, Rettungs- und Angriffswürfe mit STÄ/GES, keine Zauber.", "equipment.armor")
    else:
        ac_value = 10 + dex + (shield_bonus if shield else 0)
        ac_parts = [part('Ungerüstete Basis',10,{'id':'armor.unarmored'}),part('GES',dex,{'id':'modifier.dex'})]
        ac_formula = "10 + GES" + (" + Schild" if shield else "")
        for formula in data["armorClassFormulas"]:
            if levels_by_class.get(formula["classKey"], 0) < formula["minClassLevel"]:
                continue
            if formula["subclass"] and chosen_subclass.get(formula["classKey"]) != formula["subclass"]:
                continue
            if shield and formula["shield"] == "forbidden":
                continue
            value = formula["base"] + sum(abilities[a]["modifier"] for a in formula["abilities"]) + (shield_bonus if shield else 0)
            if value > ac_value:
                ac_value = value
                ac_parts = [part(formula['id'],formula['base'],formula.get('source'))] + [part(a.upper(),abilities[a]['modifier'],{'id':'modifier.'+a}) for a in formula['abilities']]
                ac_formula = f"{formula['id']}: {formula['base']} + " + " + ".join(a.upper() for a in formula["abilities"]) + (" + Schild" if shield else "")
    if shield: ac_parts.append(part('Schild',shield_bonus,{'id':'equipment.shield'}))
    chosen_feats = set(taken_feats) | {v for k in feature_state.values() for v in _dict(k).values() if isinstance(v, str)}
    for rule_bonus in data["armorClassBonuses"]:
        if rule_bonus["featId"] in chosen_feats and (armor or not rule_bonus["requiresArmor"]):
            ac_value += rule_bonus["bonus"]
            ac_parts.append(part(rule_bonus['id'],rule_bonus['bonus'],rule_bonus.get('source')))
            ac_formula += f" + {rule_bonus['bonus']} ({rule_bonus['id']})"

    for grant,source in grants:
        if grant['kind']=='ac':
            ac_value += grant['value']; ac_parts.append(part(source['name'],grant['value'],source))
    explain('armorClass','Rüstungsklasse',ac_value,ac_parts,'best_formula_then_add')
    speed = species["speedMeters"] if species else 9.0
    speed_parts = [part(species['name'] if species else 'Grundbewegung',speed,source_ref(species) if species else None)]
    for rule_bonus in data["speedBonuses"]:
        class_level = levels_by_class.get(rule_bonus["classKey"], 0)
        if class_level < rule_bonus["minClassLevel"]:
            continue
        if "unless" in rule_bonus and armor and armor["category"] in rule_bonus["unless"]:
            continue
        if rule_bonus.get("armor") == "none" and (armor or shield):
            continue
        if "meters" in rule_bonus:
            speed += rule_bonus["meters"]
            speed_parts.append(part(rule_bonus.get('id') or rule_bonus['classKey'],rule_bonus['meters'],rule_bonus.get('source')))
        else:
            column = next(r for r in classes[rule_bonus["classKey"]]["levels"] if r["level"] == class_level)["columns"].get(rule_bonus["column"])
            speed += _parse_meters(column)
            speed_parts.append(part(rule_bonus.get('id') or rule_bonus['classKey'],_parse_meters(column),rule_bonus.get('source')))
    initiative_parts = [part('GES',dex,{'id':'modifier.dex'})] + [part(r.get('id') or r['featId'],pb,r.get('source')) for r in data['initiativeBonuses'] if r['featId'] in chosen_feats]
    initiative = abilities["dex"]["modifier"] + sum(pb for r in data["initiativeBonuses"] if r["featId"] in chosen_feats)
    for grant,source in grants:
        if grant['kind']=='speed_meters':
            speed += grant['value']; speed_parts.append(part(source['name'],grant['value'],source))
        if grant['kind'] in ('initiative','initiative_pb'):
            value = pb if grant['kind']=='initiative_pb' else grant['value']
            initiative += value; initiative_parts.append(part(source['name'],value,source))
    explain('speed','Bewegung (m)',speed,speed_parts)
    explain('initiative','Initiative',initiative,initiative_parts)
    explain('proficiencyBonus','Übungsbonus',pb,[part('Gesamtstufe '+str(total_level),pb,{'id':'levels.proficiencyBonus'})],'level_table')

    # ---- saves and skills
    save_profs = set(classes[first_class]["savingThrows"]) if first_class else set()
    saves = {a: {"proficient": a in save_profs, "bonus": abilities[a]["modifier"] + (pb if a in save_profs else 0)} for a in ABILITY_IDS}
    skill_rows = {}
    for skill_id, skill in skills.items():
        level = proficiency.get(skill_id, "none")
        multiplier = {"none": 0, "proficient": 1, "expertise": 2}[level]
        skill_rows[skill_id] = {"name": skill["name"], "ability": skill["ability"], "proficiency": level, "bonus": abilities[skill["ability"]]["modifier"] + multiplier * pb}
    passive = 10 + skill_rows["wahrnehmung"]["bonus"] if "wahrnehmung" in skill_rows else 10

    for a,row in saves.items():
        explain('save.'+a,ability_names[a]+' Rettungswurf',row['bonus'],
                [part(ability_names[a],abilities[a]['modifier'],{'id':'modifier.'+a}),part('Rettungswurf-Übung',pb if row['proficient'] else 0,{'id':'class.'+str(first_class)})])
    for sid,row in skill_rows.items():
        multiplier = {'none':0,'proficient':1,'expertise':2}[row['proficiency']]
        explain('skill.'+sid,row['name'],row['bonus'],[part(ability_names[row['ability']],abilities[row['ability']]['modifier'],{'id':'modifier.'+row['ability']}),
            part('Expertise' if multiplier==2 else 'Fertigkeitsübung',multiplier*pb,{'id':'proficiency.'+sid,'grantedBy':skill_sources.get(sid,[]),'expertiseSelection':'skills.expertise' if multiplier==2 else None})],'highest_proficiency_then_add')
    explain('passivePerception','Passive Wahrnehmung',passive,[part('Basis',10),part('Wahrnehmung',passive-10,{'id':'skill.wahrnehmung'})])

    # ---- spellcasting
    casting = _spellcasting(data, state, levels_by_class, abilities, pb, findings)

    for key,row in casting['classes'].items():
        parts = [part(row['ability'].upper(),abilities[row['ability']]['modifier'],{'id':'modifier.'+row['ability']}),part('Übungsbonus',pb,{'id':'proficiencyBonus'})]
        explain('spellAttack.'+key,'Zauberangriff '+classes[key]['name'],row['attackBonus'],parts)
        explain('spellSaveDc.'+key,'Zauber-SG '+classes[key]['name'],row['saveDc'],[part('Basis',8)]+parts)
    result = {
        "level": total_level,
        "classes": [
            {"classKey": key, "name": classes[key]["name"], "level": levels_by_class[key], "subclass": chosen_subclass.get(key), "hitDie": classes[key]["hitDie"]}
            for key in order
        ],
        "proficiencyBonus": pb,
        "abilities": abilities,
        "saves": saves,
        "skills": skill_rows,
        "hitPoints": {"max": hp_total, "breakdown": hp_breakdown},
        "hitDice": {f"d{die}": count for die, count in sorted(hit_dice.items())},
        "armorClass": {"value": ac_value, "formula": ac_formula},
        "initiative": initiative,
        "speedMeters": speed,
        "passivePerception": passive,
        "spellcasting": casting,
        "feats": taken_feats,
        "classOptionEligibility": option_eligibility,
    }
    result['provenance'] = provenance
    result['provenanceRuleset'] = {'id':data['rulesetId'],'version':data['rulesetVersion']}
    result["overrides"] = _apply_overrides(state, result, findings)
    for override in result['overrides']:
        keys = [override['key']]
        if override['key'] in ('spellAttack','spellSaveDc'): keys = [k for k in provenance if k.startswith(override['key']+'.')]
        for key in keys:
            if key in provenance:
                row = provenance[key]
                row['contributions'].append(part('Manuell: '+override['reason'],override['value']-row['total'],{'id':'overrides.'+override['key']}))
                row['total'] = override['value']; row['stacking'] += '_then_override'
        if override['key'].startswith('ability.'):
            a=override['key'].split('.')[1];mod=result['abilities'][a]['modifier']
            explain('modifier.'+a,ability_names[a]+' Modifikator',mod,
                [part('Abrunden((Attribut − 10) / 2)',mod,{'id':'ability.'+a})],'ability_modifier_after_override')

    severities = {item["severity"] for item in findings.items}
    result["findings"] = findings.items
    result["valid"] = ERROR not in severities
    result["complete"] = result["valid"] and INCOMPLETE not in severities
    return result


def _weapon_allowed(class_entry: dict, weapon: dict) -> bool:
    for grant in class_entry["weaponProficiencies"]:
        if grant["category"] != weapon["category"]:
            continue
        required = grant.get("requiresProperty")
        if not required or any(prop["name"] in required for prop in weapon["properties"]):
            return True
    return False


def _armor_trained(classes: dict, levels_by_class: dict, first_class: str | None, category: str) -> bool:
    if first_class and category in classes[first_class]["armorProficiencies"]:
        return True
    for key in levels_by_class:
        if key == first_class:
            continue
        if category in classes[key]["multiclassGrants"].get("armor", []):
            return True
    return False


def _spellcasting(data: dict, state: dict, levels_by_class: dict, abilities: dict, pb: int, findings: _Findings) -> dict:
    classes = {c["classKey"]: c for c in data["classes"]}
    spells = _Lookup(data["spells"])
    chosen = _dict(state.get("spells"))
    per_class = {}
    for key, class_level in levels_by_class.items():
        casting = classes[key]["spellcasting"]
        if not casting:
            continue
        row = next(r for r in casting["levels"] if r["level"] == class_level)
        ability = casting["ability"]
        mod = abilities[ability]["modifier"]
        selection = _dict(chosen.get(key))
        cantrips, prepared = [s for s in _list(selection.get("cantrips"))], [s for s in _list(selection.get("prepared"))]
        known = [s for s in _list(selection.get("spellbook"))]
        allowed = _Lookup.fromkeys(data["spellLists"][key])
        if casting["kind"] == "pact":
            max_grade = row["slotGrade"]
        else:
            max_grade = max([grade + 1 for grade, count in enumerate(row["slots"]) if count] or [0])
        path = f"spells.{key}"
        name = classes[key]["name"]
        if len(cantrips) < row["cantrips"]:
            findings.add(INCOMPLETE, "cantrips-missing", f"{name}: Wähle {row['cantrips']} Zaubertricks.", path + ".cantrips", casting["abilitySource"])
        elif len(cantrips) > row["cantrips"]:
            findings.add(ERROR, "cantrips-extra", f"{name}: Höchstens {row['cantrips']} Zaubertricks.", path + ".cantrips", casting["abilitySource"])
        for spell_id in cantrips:
            spell = spells.get(spell_id)
            if spell is None or spell["level"] != 0 or spell_id not in allowed:
                findings.add(ERROR, "cantrip-invalid", f"Ungültiger Zaubertrick für {name}.", path + ".cantrips")
        pool = prepared
        if casting["preparation"]["mode"] == "spellbook":
            if len(known) < casting["spellbook"]["startingSpells"] + casting["spellbook"]["perLevel"] * (class_level - 1):
                findings.add(INCOMPLETE, "spellbook-missing", f"{name}: Zauberbuch auf {casting['spellbook']['startingSpells'] + casting['spellbook']['perLevel'] * (class_level - 1)} Zauber füllen.", path + ".spellbook", casting["spellbook"]["startingSource"])
            for spell_id in known:
                spell = spells.get(spell_id)
                if spell is None or spell["level"] < 1 or spell_id not in allowed:
                    findings.add(ERROR, "spell-invalid", f"Ungültiger Zauber im Zauberbuch ({name}).", path + ".spellbook")
            if any(s not in known for s in prepared):
                findings.add(ERROR, "prepared-not-in-book", "Vorbereitete Zauber müssen im Zauberbuch stehen.", path + ".prepared")
        if len(pool) < row["prepared"]:
            findings.add(INCOMPLETE, "prepared-missing", f"{name}: Bereite {row['prepared']} Zauber vor.", path + ".prepared", casting["preparation"]["source"])
        elif len(pool) > row["prepared"]:
            findings.add(ERROR, "prepared-extra", f"{name}: Höchstens {row['prepared']} vorbereitete Zauber.", path + ".prepared", casting["preparation"]["source"])
        for spell_id in pool:
            spell = spells.get(spell_id)
            if spell is None or spell["level"] < 1 or spell_id not in allowed:
                findings.add(ERROR, "spell-invalid", f"Ungültiger Zauber für {name}.", path + ".prepared")
            elif spell["level"] > max_grade:
                findings.add(ERROR, "spell-grade", f"„{spell['name']}“ ({spell['level']}. Grad) übersteigt deine Zauberplätze.", path + ".prepared")
        per_class[key] = {
            "ability": ability,
            "saveDc": 8 + mod + pb,
            "attackBonus": mod + pb,
            "cantrips": row["cantrips"],
            "prepared": row["prepared"],
            "maxGrade": max_grade,
            "kind": casting["kind"],
            "ritualCasting": casting["ritualCasting"],
        }
    non_pact = {k: v for k, v in levels_by_class.items() if per_class.get(k, {}).get("kind") in {"full", "half"}}
    slots = None
    caster = 0
    if non_pact:
        caster = caster_level(data, non_pact)
        slots = list(data["multiclass"]["spellSlotsByCasterLevel"][str(min(20, caster))])
    pact = None
    if "warlock" in levels_by_class:
        row = next(r for r in classes["warlock"]["spellcasting"]["levels"] if r["level"] == levels_by_class["warlock"])
        pact = {"slots": row["slots"], "grade": row["slotGrade"]}
    return {"classes": per_class, "casterLevel": caster, "slots": slots, "pact": pact}


def _apply_overrides(state: dict, result: dict, findings: _Findings) -> list[dict]:
    applied = []
    for key, spec in _dict(state.get("overrides")).items():
        spec = _dict(spec)
        if key not in OVERRIDE_KEYS:
            findings.add(ERROR, "override-unknown", f"Unbekannte Überschreibung „{key}“.", f"overrides.{key}")
            continue
        computed = _read_override_target(result, key)
        if computed is None:
            continue
        if "set" in spec:
            value = _int(spec["set"]) if key != "speed" else spec["set"]
        elif "add" in spec:
            value = computed + (_int(spec["add"]) if key != "speed" else float(spec["add"]))
        else:
            findings.add(ERROR, "override-invalid", f"Überschreibung „{key}“ braucht set oder add.", f"overrides.{key}")
            continue
        if value is None:
            findings.add(ERROR, "override-invalid", f"Überschreibung „{key}“ ist keine Zahl.", f"overrides.{key}")
            continue
        _write_override_target(result, key, value)
        applied.append({"key": key, "computed": computed, "value": value, "reason": str(spec.get("reason", ""))[:200]})
        findings.add(INFO, "override-active", f"„{key}“ ist manuell von {computed} auf {value} gesetzt.", f"overrides.{key}")
    return applied


def _read_override_target(result: dict, key: str):
    if key == "hp.max":
        return result["hitPoints"]["max"]
    if key == "armorClass":
        return result["armorClass"]["value"]
    if key == "speed":
        return result["speedMeters"]
    if key.startswith("ability."):
        return result["abilities"][key.split(".")[1]]["score"]
    if key == "spellSaveDc":
        values = [c["saveDc"] for c in result["spellcasting"]["classes"].values()]
        return max(values) if values else None
    if key == "spellAttack":
        values = [c["attackBonus"] for c in result["spellcasting"]["classes"].values()]
        return max(values) if values else None
    return {"initiative": result["initiative"], "proficiencyBonus": result["proficiencyBonus"], "passivePerception": result["passivePerception"]}[key]


def _write_override_target(result: dict, key: str, value) -> None:
    if key == "hp.max":
        result["hitPoints"]["max"] = value
    elif key == "armorClass":
        result["armorClass"]["value"] = value
    elif key == "speed":
        result["speedMeters"] = value
    elif key.startswith("ability."):
        ability = result["abilities"][key.split(".")[1]]
        ability["score"], ability["modifier"] = value, ability_modifier(value)
    elif key in {"spellSaveDc", "spellAttack"}:
        field = "saveDc" if key == "spellSaveDc" else "attackBonus"
        for entry in result["spellcasting"]["classes"].values():
            entry[field] = value
    else:
        result[key] = value
