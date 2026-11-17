#!/usr/bin/env python3
"""Build the structured English SRD 5.2.1 rulebook package (srd-5.2.1-en).

The input is the text layer of the official English PDF, extracted with
``pdftotext -layout`` (poppler).  The builder never paraphrases: every official
block is the extracted source text, re-flowed (two-column reading order, line
joins, soft-hyphen removal) and structured into headings, paragraphs, lists,
definition lists, tables and stat blocks.  Roll Drauf's own English reading
notes are separate ``original-note`` blocks flagged ``editorial`` so readers,
the compendium and tests can always tell them apart from the citable rules text.

Usage (repository root):

    pdftotext -layout vtt/static/regelwerk/SRD_CC_v5.2.1.pdf /tmp/vtt-srd-en-source-20261117.txt
    python3 tools/build_english_srd.py --source-text /tmp/vtt-srd-en-source-20261117.txt \\
        --pdf vtt/static/regelwerk/SRD_CC_v5.2.1.pdf

The same input bytes always produce the same output bytes (stdlib only, no
timestamps, sorted keys).  ``generated/build-report.json`` lists the detected
page layout, document markers, coverage checks and every warning.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "vtt" / "rules_content" / "srd-5.2.1-en"
DEFAULT_PDF = ROOT / "vtt" / "static" / "regelwerk" / "SRD_CC_v5.2.1.pdf"
BUILDER = "tools/build_english_srd.py"
BUILDER_VERSION = "1.0.0"
RULESET_ID = "srd-5.2.1-en"
ROUTE = "/regelwerk/5.2.1/en"
PDF_SHA256 = "8974902d109d6e63672d7c490bde9ccf052410503d9cfa768237154fbc5e3d87"
PDF_URL = "https://media.dndbeyond.com/compendium-images/srd/5.2/SRD_CC_v5.2.1.pdf"
PAGE_COUNT = 364
FIRST_BODY_PAGE = 5
NOTE_TITLE = "Roll Drauf reading note"
ATTRIBUTION = (
    "This work includes material from the System Reference Document 5.2.1 (“SRD 5.2.1”) by Wizards of the "
    "Coast LLC, available at https://www.dndbeyond.com/srd. The SRD 5.2.1 is licensed under the Creative "
    "Commons Attribution 4.0 International License, available at "
    "https://creativecommons.org/licenses/by/4.0/legalcode."
)
EDITORIAL_POLICY = {
    "officialBody": "extracted",
    "paraphrased": False,
    "statement": (
        "All blocks except Roll Drauf reading notes are the official SRD 5.2.1 text, extracted from the text "
        "layer of the English PDF. Extraction restores the two-column reading order, joins line breaks, removes "
        "soft hyphens and structures the text into headings, paragraphs, lists, tables and stat blocks. The "
        "official text is not paraphrased, summarised or reworded. Blocks of type original-note with "
        "editorial=true are Roll Drauf's own explanatory English text and are not part of the SRD."
    ),
    "editorialBlockType": "original-note",
    "editorialFlag": "editorial",
    "structuralLabels": "Stat block labels 'Type' and the ability score row layout are structural, not source text.",
}

FOOTER = re.compile(r"^\s*(\d{1,3})\s+System Reference Document 5\.2\.1\s*$")
_SEG = re.compile(r"\S+(?: \S+)*")
SCHOOLS = ("Abjuration", "Conjuration", "Divination", "Enchantment", "Evocation", "Illusion", "Necromancy",
           "Transmutation")
_SCHOOL = "|".join(SCHOOLS)
SPELL_HEAD = re.compile(rf"^(?:Level (?P<level>[1-9]) (?P<school>{_SCHOOL})|(?P<cschool>{_SCHOOL}) Cantrip) \(")
SPELL_PROPS = ("Casting Time", "Range", "Components", "Duration")
SPELL_PROP = re.compile(r"^(Casting Time|Range|Components?|Duration):\s*(.*)$")
ITEM_HEAD = re.compile(r"^(?P<cat>Armor|Weapon|Wondrous Item|Potion|Ring|Rod|Scroll|Staff|Wand)\b")
RARITY_WORD = re.compile(r"\b(Very Rare|Uncommon|Common|Rare|Legendary|Artifact)\b")
FEAT_HEAD = re.compile(r"^(?P<cat>Origin|General|Fighting Style|Epic Boon) Feat\b(?P<rest>.*)$")
SIZE = r"(?:Tiny|Small|Medium|Large|Huge|Gargantuan)"
SB_TYPE = re.compile(rf"^{SIZE}\b[^,]*,\s*\S")
ABILITY = re.compile(r"\b(Str|Dex|Con|Int|Wis|Cha)\s*(\d+) ([+−\-–]\d+) ([+−\-–]?\d+)")
ABILITY_LINE = re.compile(r"^(?:(?:Str|Dex|Con|Int|Wis|Cha)\s*\d+ [+−\-–]\d+ [+−\-–]?\d+\s*)+$")
MOD_SAVE = re.compile(r"^(?:MOD SAVE\s*)+$")
STAT_LABELS = ("Saving Throws", "Skills", "Vulnerabilities", "Resistances", "Immunities", "Gear", "Senses",
               "Languages", "CR")
STAT_SECTIONS = ("Traits", "Actions", "Bonus Actions", "Reactions", "Legendary Actions")
ACTION_HEAD = re.compile(r"^(?:[A-Z0-9][^.:]{0,60}?(?: \([^)]*\))?\. |Legendary Action Uses:|At Will:|\d+/Day(?: Each)?:)")
LABELS = ("Casting Time", "Range", "Components", "Duration", "Creature Type", "Size", "Speed", "Ability Scores",
          "Feat", "Skill Proficiencies", "Tool Proficiency", "Tool Proficiencies", "Equipment", "Prerequisite",
          "Cost", "Ability", "Weight", "Utilize", "Craft", "Variants", "Repeatable")
LABEL = re.compile(r"^(" + "|".join(re.escape(label) for label in LABELS) + r"):\s*(.*)$")
NUMBERED = re.compile(r"^\d{1,2}: ")
LEVEL_FEATURE = re.compile(r"^Level (\d{1,2}): (.+)$")
SUBCLASS = re.compile(r"^(\w+) Subclass: (.+)$")
SMALL_WORDS = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "the", "to",
               "with", "without", "via", "against", "vs", "per", "than", "but", "nor", "up", "over"}


class BuildError(RuntimeError):
    pass


@dataclass
class Line:
    page: int
    col: str
    x: int
    text: str
    segs: list
    indent: int = 0
    used: bool = False

    @property
    def flat(self) -> str:
        return " ".join(segment for _, segment in self.segs)


# ---------------------------------------------------------------------------
# Text helpers
# ---------------------------------------------------------------------------


def clean(text: str) -> str:
    return " ".join(str(text).split())


def norm(text: str) -> str:
    text = clean(text).replace("’", "'").replace("“", '"').replace("”", '"')
    return text.casefold()


def slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode("ascii").lower()
    text = text.replace("'", "")
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def normalized_search_text(value: object) -> str:
    # Must stay identical to vtt.rules_content.generator.normalized_search_text.
    normalized = unicodedata.normalize("NFKC", str(value or "")).casefold()
    return " ".join(normalized.split())


def ends_sentence(text: str) -> bool:
    stripped = text.rstrip().rstrip("”’\")]")
    return bool(stripped) and (stripped[-1] in ".!?:" or stripped.endswith("…"))


def titleish(text: str) -> bool:
    if not text or not (text[0].isupper() or text[0].isdigit() or text[0] in "“\"(+"):
        return False
    words = re.findall(r"[A-Za-z][A-Za-z’'\-]*", text)
    if not words:
        return False
    for word in words:
        if word.lower().strip("’'") in SMALL_WORDS:
            continue
        if not word[0].isupper():
            return False
    return True


def name_line(line: Line) -> bool:
    text = line.text
    return (
        len(line.segs) == 1 and 2 <= len(text) <= 56 and line.indent <= 3 and text[-1] not in ".,;:!?"
        and titleish(text) and not LABEL.match(text) and not text.startswith("•") and not NUMBERED.match(text)
    )


def balanced(text: str) -> bool:
    return text.count("(") <= text.count(")")


def needs_more(text: str) -> bool:
    text = text.rstrip()
    return (not balanced(text)) or text.endswith((",", "-", " or", " and", " Very", "(Requires"))


def build_lexicon(stream: list[Line]) -> set[str]:
    words: set[str] = set()
    for line in stream:
        tokens = re.findall(r"[A-Za-z][A-Za-z’']*(?:-[A-Za-z][A-Za-z’']*)*", line.text)
        if line.text.endswith("-") and tokens:
            tokens = tokens[:-1]
        words.update(token.lower() for token in tokens[1:])
    return words


_HYPHEN_END = re.compile(r"(\S*?)([A-Za-z][A-Za-z’']*)-$")
_WORD_START = re.compile(r"^([A-Za-z][A-Za-z’']*)")


def _keep_hyphen(prefix: str, left: str, right: str, lexicon: set[str]) -> bool:
    joined = (left + right).lower()
    hyphenated = f"{left}-{right}".lower()
    if any(char.isdigit() for char in prefix):
        return True
    if hyphenated in lexicon and joined not in lexicon:
        return True
    if joined in lexicon:
        return False
    if right[:1].isupper():
        return True
    return prefix.endswith("-")


def join_text(parts: list[str], lexicon: set[str]) -> str:
    out = ""
    for part in parts:
        part = clean(part)
        if not part:
            continue
        if not out:
            out = part
            continue
        hyphen = _HYPHEN_END.search(out)
        start = _WORD_START.match(part)
        if hyphen and start:
            if _keep_hyphen(hyphen.group(1), hyphen.group(2), start.group(1), lexicon):
                out += part
            else:
                out = out[:-1] + part
        elif out.endswith(("—", "/", "–")):
            out += part
        else:
            out += " " + part
    return out


def summary(text: str, limit: int = 220) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rsplit(" ", 1)[0].rstrip(",;:") + "…"


# ---------------------------------------------------------------------------
# Pages and columns
# ---------------------------------------------------------------------------


def read_pages(text: str) -> list[list[str]]:
    raw_pages = text.replace("\r", "").split("\f")
    if raw_pages and not raw_pages[-1].strip():
        raw_pages = raw_pages[:-1]
    pages = []
    for index, raw in enumerate(raw_pages, start=1):
        lines = [line.replace("\t", " ").rstrip() for line in raw.split("\n")]
        while lines and not lines[-1].strip():
            lines.pop()
        match = FOOTER.match(lines[-1]) if lines else None
        if not match:
            raise BuildError(f"page {index}: footer 'N System Reference Document 5.2.1' not found")
        if int(match.group(1)) != index:
            raise BuildError(f"page {index}: footer names page {match.group(1)}")
        lines.pop()
        pages.append(lines)
    if len(pages) != PAGE_COUNT:
        raise BuildError(f"expected {PAGE_COUNT} pages, found {len(pages)}")
    return pages


def _prose(part: str) -> bool:
    part = part.strip()
    return bool(part) and "  " not in part and len(part) >= 30 and part.count(" ") >= 4


def find_gutter(lines: list[str]) -> int | None:
    rows = [line for line in lines if line.strip()]
    if len(rows) < 6:
        return None
    width = max(len(line) for line in rows)
    best_score, best = 0, None
    for gutter in range(36, min(100, width - 8)):
        clear = starts = 0
        for line in rows:
            if len(line) <= gutter - 1 or (line[gutter - 1] == " " and line[gutter - 2] == " "):
                clear += 1
                if len(line) > gutter and line[gutter] != " ":
                    starts += 1
        if clear < 0.8 * len(rows) or starts < max(4, 0.2 * len(rows)):
            continue
        rights = [line[gutter:].strip() for line in rows if len(line) > gutter and line[gutter:].strip()]
        prose = sum(1 for right in rights if "  " not in right and len(right) >= 20)
        if prose < 0.30 * len(rights) and not any("School" in row for row in rows):
            continue
        if starts > best_score:
            best_score, best = starts, gutter
    return best


def split_at_gutter(line: str, gutter: int) -> int | None:
    """Index where the right column starts, None for left-only lines, -1 for crossing lines."""
    if len(line) <= gutter - 1 or not line[gutter - 1:].strip():
        return None
    if not line[: max(gutter - 3, 0)].strip():
        return len(line) - len(line.lstrip())
    if line[gutter - 1] == " ":
        return gutter
    if gutter >= 3 and line[gutter - 2] == " " and line[gutter - 3] == " ":
        return gutter - 1
    return -1


def find_bands(lines: list[str], gutter: int) -> list[tuple[int, int]]:
    """Full-width regions (tables spanning both columns) on a two-column page."""
    count = len(lines)

    def kind(index: int) -> str:
        line = lines[index]
        if not line.strip():
            return "blank"
        if split_at_gutter(line, gutter) == -1:
            return "core"
        segs = [(match.start(), match.group()) for match in _SEG.finditer(line)]
        # Equipment/class tables may have a header cell exactly on the gutter.
        # Ability rows and parallel spell lists are independent column content.
        if (any("Armor Class (AC)" in candidate for candidate in lines)
                and len(segs) >= 4 and not re.match(r"^(?:Str|Int|MOD SAVE)\b", line.strip())
                and not any(part in SCHOOLS for _, part in segs)
                and sum(x < gutter - 3 for x, _ in segs) >= 2
                and sum(x > gutter + 4 for x, _ in segs) >= 2):
            return "core"
        lefts = [seg for seg in segs if seg[0] < gutter - 3]
        window = [seg for seg in segs if gutter - 2 <= seg[0] <= gutter + 4]
        far = [seg for seg in segs if seg[0] > gutter + 4]
        if lefts and not window and len(far) >= 2:
            return "core"
        return "text"

    kinds = [kind(index) for index in range(count)]
    clusters: list[list[int]] = []
    for index, value in enumerate(kinds):
        if value != "core":
            continue
        if clusters and index - clusters[-1][1] <= 5:
            clusters[-1][1] = index
        else:
            clusters.append([index, index])
    bands: list[tuple[int, int]] = []
    for first, last in clusters:
        members = sum(1 for index in range(first, last + 1) if kinds[index] == "core")
        crossing = any(split_at_gutter(lines[index], gutter) == -1 for index in range(first, last + 1))
        if members < 2 and not crossing:
            continue
        top = first
        while top - 1 >= 0 and first - (top - 1) <= 4 and kinds[top - 1] != "blank":
            above = lines[top - 1]
            cut = split_at_gutter(above, gutter)
            left = above if cut in (None, -1) else above[:cut]
            right = "" if cut in (None, -1) else above[cut:]
            if _prose(left) or _prose(right) or left.strip().endswith("."):
                break
            top -= 1
        bottom, blanks = last, 0
        while bottom + 1 < count:
            following = bottom + 1
            if kinds[following] == "blank":
                blanks += 1
                if blanks >= 2:
                    break
                bottom = following
                continue
            line = lines[following]
            cut = split_at_gutter(line, gutter)
            left = line if cut in (None, -1) else line[:cut]
            if kinds[following] != "core":
                if _prose(left):
                    break
                if blanks and len(list(_SEG.finditer(line))) < 3:
                    break
            blanks = 0
            bottom = following
        while bottom > last and kinds[bottom] == "blank":
            bottom -= 1
        if bands and top <= bands[-1][1] + 1:
            bands[-1] = (bands[-1][0], max(bottom, bands[-1][1]))
        else:
            bands.append((top, bottom))
    return bands


def make_line(page: int, col: str, raw: str, start: int, origin: int) -> Line:
    part = raw[start:]
    segs = [(match.start() + start - origin, match.group()) for match in _SEG.finditer(part)]
    # Some PDF trait rows use one space at the visual cell boundary.
    trait = re.match(r"^\s*(Primary Ability|Hit Point Die|Saving Throw Proficiencies|Skill Proficiencies|Weapon Proficiencies|Armor Training|Starting Equipment) (.+)$", part)
    if len(segs) == 1 and trait:
        left = segs[0][0]
        segs = [(left, trait.group(1)), (left + len(trait.group(1)) + 1, trait.group(2))]
    return Line(page, col, segs[0][0], part.strip(), segs)


def page_stream(lines: list[str], page: int, layout: dict) -> list[Line]:
    # These two pages pair a full-width table with prose, or a narrow left
    # column with an indented right table. The PDF's fixed layout is known;
    # record these source-specific boundaries instead of cutting table cells.
    gutter = {9: 66, 26: 65, 36: 74, 75: 63, 95: 56, 155: 67, 211: 64}.get(page, find_gutter(lines))
    out: list[Line] = []
    if gutter is None:
        for raw in lines:
            if raw.strip():
                out.append(make_line(page, "S", raw, 0, 0))
        layout[str(page)] = {"gutter": None, "bands": []}
        return out
    # From Spells onward all source tables stay inside their own column.
    # A table facing prose (or another table) is not a full-width band.
    bands = find_bands(lines, gutter) if page < 104 else []
    if 28 <= page <= 82:
        # Only progression tables span the page in class chapters. A Core
        # Traits table or a spell list opposite prose stays in its own column.
        bands = [(first, last) for first, last in bands
                 if re.match(r"^[A-Z][a-z]+ Features$", lines[first].strip())]
    layout[str(page)] = {"gutter": gutter, "bands": [[first + 1, last + 1] for first, last in bands]}

    def columns(chunk: list[str]) -> None:
        lefts, rights = [], []
        for raw in chunk:
            if not raw.strip():
                continue
            cut = split_at_gutter(raw, gutter)
            if cut is None or cut == -1:
                lefts.append(make_line(page, "L", raw, 0, 0))
                continue
            if raw[:cut].strip():
                lefts.append(make_line(page, "L", raw[:cut], 0, 0))
            rights.append(make_line(page, "R", raw, cut, gutter))
        out.extend(lefts)
        out.extend(rights)

    cursor = 0
    for first, last in bands:
        columns(lines[cursor:first])
        for raw in lines[first: last + 1]:
            if raw.strip():
                out.append(make_line(page, "F", raw, 0, 0))
        cursor = last + 1
    columns(lines[cursor:])
    return out


def assign_indents(stream: list[Line]) -> None:
    groups: dict[tuple[int, str], list[Line]] = {}
    for line in stream:
        groups.setdefault((line.page, line.col), []).append(line)
    for items in groups.values():
        counts = Counter(line.x for line in items if len(line.segs) == 1 and len(line.text) >= 25)
        if counts:
            base = min(counts, key=lambda value: (-counts[value], value))
        else:
            base = min(line.x for line in items)
        for line in items:
            line.indent = line.x - base


def rel(line: Line, x: int) -> int:
    return x - (line.x - line.indent)


# ---------------------------------------------------------------------------
# Document plan
# ---------------------------------------------------------------------------

SECTIONS = (
    ("playing-the-game", "Playing the Game"),
    ("character-creation", "Character Creation"),
    ("classes", "Classes"),
    ("character-origins", "Character Origins"),
    ("feats", "Feats"),
    ("equipment", "Equipment"),
    ("spells", "Spells"),
    ("rules-glossary", "Rules Glossary"),
    ("gameplay-toolbox", "Gameplay Toolbox"),
    ("magic-items", "Magic Items"),
    ("monsters", "Monsters"),
    ("animals", "Animals"),
)
CLASSES = (
    ("Barbarian", 28, "Path of the Berserker", False),
    ("Bard", 31, "College of Lore", True),
    ("Cleric", 36, "Life Domain", True),
    ("Druid", 41, "Circle of the Land", True),
    ("Fighter", 47, "Champion", False),
    ("Monk", 49, "Warrior of the Open Hand", False),
    ("Paladin", 53, "Oath of Devotion", True),
    ("Ranger", 57, "Hunter", True),
    ("Rogue", 61, "Thief", False),
    ("Sorcerer", 64, "Draconic Sorcery", True),
    ("Warlock", 70, "Fiend Patron", True),
    ("Wizard", 77, "Evoker", True),
)
SPLITS = {
    "spells": ("Spells", "spells", ("ab", "cd", "ef", "gh", "il", "mo", "pr", "ss", "tv", "wz")),
    "glossary": ("Rules Glossary", "rules-glossary", ("ab", "cd", "eh", "il", "mr", "ss", "tz")),
    "magic-items": ("Magic Items", "magic-items", ("ab", "cd", "eg", "hl", "mo", "pr", "ss", "tz")),
    "monsters": ("Monsters", "monsters", ("ab", "cd", "eg", "hk", "ln", "or", "ss", "tz")),
    "animals": ("Animals", "animals", ("ac", "dg", "ho", "pr", "sz")),
}

NOTES = {
    "core.rhythm-and-abilities": (
        "Start here. This chapter explains how play flows — the Game Master describes a scene, the players say "
        "what their characters do, and dice settle what is uncertain — and introduces the six abilities every "
        "later rule builds on. Keep the Ability Modifiers table at hand: almost every roll adds one of them."),
    "core.d20-tests": (
        "Every uncertain outcome resolves the same way: roll a d20, add modifiers, compare the total with a "
        "target number. This chapter covers the three D20 Tests — ability checks, saving throws and attack "
        "rolls — and how Advantage and Disadvantage change the roll."),
    "core.proficiency": (
        "Proficiency is the game's measure of training. Read here how the Proficiency Bonus grows, which skill "
        "belongs to which ability, and how tool proficiency and Expertise are applied."),
    "core.actions": (
        "On your turn you take one action, and rules may give you a Bonus Action or a Reaction. This chapter "
        "lists the actions every creature can take; class features and spells add more."),
    "core.social-interaction": (
        "Conversations are played out first and rolled second. This chapter explains creature attitudes and "
        "how the Influence action can change them."),
    "core.exploration": (
        "Exploration raises the same questions again and again: what can you see, can you stay hidden, what "
        "happens when you fall, how far do you travel. The rules in this chapter answer them."),
    "core.combat": (
        "Combat is the most structured part of play. The chapter follows a round in order — Initiative, "
        "movement, attacks, cover — and then covers ranged, melee, mounted and underwater fighting."),
    "core.damage-and-healing": (
        "Hit Points, damage types, Resistance and healing work the same for characters and monsters. Pay "
        "special attention to dropping to 0 Hit Points and to Temporary Hit Points."),
    "character-creation.overview": (
        "A step-by-step path from an empty sheet to a playable level 1 character: choose a class and an origin, "
        "determine ability scores, then fill in the remaining details."),
    "character-creation.advancement": (
        "How characters gain experience and levels, what improves at each level, and how to create a character "
        "who starts above level 1."),
    "character-creation.multiclassing": (
        "Optional rules for combining classes. Check the prerequisites, and use the spell slot table when you "
        "combine spellcasting classes."),
    "character-creation.trinkets": (
        "Small curiosities a new character might carry. Roll on the table or choose freely; trinkets have no "
        "rules effect of their own."),
    "origins.backgrounds": (
        "A background describes where a character comes from. It provides ability score increases, an Origin "
        "feat, skill and tool proficiencies, and starting equipment. Four backgrounds are presented."),
    "origins.species": (
        "Your species determines creature type, size, Speed and a set of special traits. Nine species are "
        "presented in alphabetical order."),
    "feats": (
        "Feats are special talents. Origin feats come from a background, General feats can replace an Ability "
        "Score Improvement, and Fighting Style and Epic Boon feats are tied to class features and high levels."),
    "equipment.coins-and-weapons": (
        "Coins, the weapon tables and the weapon properties. Mastery properties apply only when a feature, such "
        "as Weapon Mastery, lets you use them."),
    "equipment.armor": (
        "Armor categories, the Armor table and how long it takes to don and doff armor. Wearing armor you are "
        "not trained with has serious drawbacks."),
    "equipment.tools": (
        "Each tool lists its ability, its weight, the checks it helps with and the items it can craft."),
    "equipment.adventuring-gear": "Prices, weights and rules for everyday adventuring equipment.",
    "equipment.mounts-and-vehicles": (
        "Mounts and other animals, tack and harness, and land, water and air vehicles with their statistics."),
    "equipment.services": "Lifestyle expenses, food and lodging, hirelings and paid spellcasting.",
    "equipment.crafting": (
        "How to craft nonmagical items, brew Potions of Healing and scribe Spell Scrolls."),
    "spells.rules": (
        "How characters gain spells, what spell slots are, and the rules that apply whenever a spell is cast: "
        "casting time, range, components, duration, targets and areas of effect."),
    "toolbox.travel-and-backgrounds": (
        "Game Master tools for travel pace and for designing new backgrounds."),
    "toolbox.curses": "Curses and magical contagions the Game Master can use as threats or story hooks.",
    "toolbox.environment": "Environmental effects such as extreme heat and cold, deep water and thin air.",
    "toolbox.fear": "Rules for fear and mental stress.",
    "toolbox.poison": "Kinds of poison and sample poisons with their effects and prices.",
    "toolbox.traps": "How traps are built and resolved, followed by sample traps.",
    "toolbox.combat-encounters": "How to build combat encounters of a chosen difficulty with an XP budget.",
    "magic-items.rules": (
        "General rules for magic items: categories, rarity, Attunement and activation, cursed and sentient "
        "items, resilience and crafting."),
    "monsters.overview": "How to read a stat block and how to run a monster at the table.",
}
FAMILY_NOTES = {
    "spells": (
        "Spells {range} in alphabetical order. Under each name you find the spell level, school and the classes "
        "that can prepare it, followed by casting time, range, components and duration."),
    "glossary": (
        "Rules Glossary {range}. A bracketed tag such as [Action] or [Condition] tells you what kind of rule a "
        "term defines."),
    "magic-items": (
        "Magic items {range} in alphabetical order. The line under each name gives the item's category, its "
        "rarity and whether it requires Attunement."),
    "monsters": "Monsters {range}. Related creatures are grouped under a shared heading.",
    "animals": (
        "Animals {range}: beasts and dinosaurs that serve as mounts, companions, Wild Shape forms or threats."),
}


def build_plan() -> list[dict]:
    def doc(doc_id, slug_, title, section, marker, page, subsections=(), mode="prose", **extra):
        return {"id": doc_id, "slug": slug_, "title": title, "section": section, "marker": marker,
                "page": page, "subsections": [(text, level) for text, level in subsections], "mode": mode, **extra}

    three = lambda *names: [(name, 3) for name in names]  # noqa: E731
    plan = [
        doc("core.rhythm-and-abilities", "rhythm-of-play-and-abilities", "Rhythm of Play and the Six Abilities",
            "Playing the Game", "Playing the Game", 5, three("Rhythm of Play", "The Six Abilities")),
        doc("core.d20-tests", "d20-tests", "D20 Tests", "Playing the Game", "D20 Tests", 6,
            three("Ability Checks", "Saving Throws", "Attack Rolls", "Advantage/Disadvantage",
                  "Advantage and Disadvantage")),
        doc("core.proficiency", "proficiency", "Proficiency", "Playing the Game", "Proficiency", 8),
        doc("core.actions", "actions", "Actions", "Playing the Game", "Actions", 9,
            three("Bonus Actions", "Reactions")),
        doc("core.social-interaction", "social-interaction", "Social Interaction", "Playing the Game",
            "Social Interaction", 10),
        doc("core.exploration", "exploration", "Exploration", "Playing the Game", "Exploration", 11,
            three("Vision and Light", "Hiding", "Interacting with Objects", "Hazards", "Travel")),
        doc("core.combat", "combat", "Combat", "Playing the Game", "Combat", 13,
            three("The Order of Combat", "Movement and Position", "Making an Attack", "Ranged Attacks",
                  "Melee Attacks", "Mounted Combat", "Underwater Combat")),
        doc("core.damage-and-healing", "damage-and-healing", "Damage and Healing", "Playing the Game",
            "Damage and Healing", 16,
            three("Hit Points", "Damage Rolls", "Critical Hits", "Saving Throws and Damage", "Damage Types",
                  "Resistance and Vulnerability", "Immunity", "Healing", "Dropping to 0 Hit Points",
                  "Temporary Hit Points")),
        doc("character-creation.overview", "character-creation", "Creating a Character", "Character Creation",
            "Character Creation", 19, three("Choose a Character Sheet", "Create Your Character")),
        doc("character-creation.advancement", "level-advancement", "Level Advancement", "Character Creation",
            "Level Advancement", 23, three("Starting at Higher Levels")),
        doc("character-creation.multiclassing", "multiclassing", "Multiclassing", "Character Creation",
            "Multiclassing", 24),
        doc("character-creation.trinkets", "trinkets", "Trinkets", "Character Creation", "Trinkets", 26),
    ]
    for name, page, subclass, caster in CLASSES:
        subsections = [(f"{name} Subclass: {subclass}", 3)]
        if caster:
            subsections.append((f"{name} Spell List", 3))
        if name == "Sorcerer":
            subsections.append(("Metamagic Options", 3))
        if name == "Warlock":
            subsections.append(("Eldritch Invocation Options", 3))
        marker = name
        if name == "Barbarian":
            marker = "Classes"
            subsections.insert(0, ("Barbarian", 2))
        plan.append(doc(f"classes.{name.lower()}", name.lower(), name, "Classes", marker, page, subsections,
                        "class", class_name=name, subclass=subclass, caster=caster))
    plan += [
        doc("origins.backgrounds", "backgrounds", "Character Backgrounds", "Character Origins", "Character Origins",
            83, [("Character Backgrounds", 2)] + three("Acolyte", "Criminal", "Sage", "Soldier"), "backgrounds"),
        doc("origins.species", "species", "Character Species", "Character Origins", "Character Species", 83,
            three("Dragonborn", "Dwarf", "Elf", "Gnome", "Goliath", "Halfling", "Human", "Orc", "Tiefling"),
            "species"),
        doc("feats", "feats", "Feats", "Feats", "Feats", 87,
            three("Feat Descriptions", "Origin Feats", "General Feats", "Fighting Style Feats", "Epic Boon Feats"),
            "feats"),
        doc("equipment.coins-and-weapons", "coins-and-weapons", "Coins and Weapons", "Equipment", "Equipment", 89,
            three("Coins", "Weapons", "Properties", "Mastery Properties"), "equipment"),
        doc("equipment.armor", "armor", "Armor", "Equipment", "Armor", 92, (), "equipment"),
        doc("equipment.tools", "tools", "Tools", "Equipment", "Tools", 93, (), "equipment"),
        doc("equipment.adventuring-gear", "adventuring-gear", "Adventuring Gear", "Equipment", "Adventuring Gear",
            94, (), "equipment"),
        doc("equipment.mounts-and-vehicles", "mounts-and-vehicles", "Mounts and Vehicles", "Equipment",
            "Mounts and Vehicles", 100, (), "equipment"),
        doc("equipment.services", "lifestyle-and-services", "Lifestyle, Lodging and Services", "Equipment",
            "Lifestyle Expenses", 101, three("Food, Drink, and Lodging", "Hirelings", "Spellcasting", "Magic Items"),
            "equipment"),
        doc("equipment.crafting", "crafting", "Crafting", "Equipment", "Crafting Nonmagical Items", 103,
            three("Brewing Potions of Healing", "Scribing Spell Scrolls"), "equipment"),
        doc("spells.rules", "gaining-and-casting-spells", "Gaining and Casting Spells", "Spells", "Spells", 104,
            three("Gaining Spells", "Casting Spells")),
        doc("spells", "spells", "Spell Descriptions", "Spells", "Spell Descriptions", 107, (), "spells",
            split="spells"),
        doc("glossary", "rules-glossary", "Rules Glossary", "Rules Glossary", "Rules Glossary", 176, (),
            "glossary", split="glossary"),
        doc("toolbox.travel-and-backgrounds", "travel-pace-and-backgrounds", "Travel Pace and Creating a Background",
            "Gameplay Toolbox", "Gameplay Toolbox", 192, three("Travel Pace", "Creating a Background")),
        doc("toolbox.curses", "curses-and-magical-contagions", "Curses and Magical Contagions", "Gameplay Toolbox",
            "Curses and Magical Contagions", 193),
        doc("toolbox.environment", "environmental-effects", "Environmental Effects", "Gameplay Toolbox",
            "Environmental Effects", 195),
        doc("toolbox.fear", "fear-and-mental-stress", "Fear and Mental Stress", "Gameplay Toolbox",
            "Fear and Mental Stress", 196),
        doc("toolbox.poison", "poison", "Poison", "Gameplay Toolbox", "Poison", 197),
        doc("toolbox.traps", "traps", "Traps", "Gameplay Toolbox", "Traps", 199),
        doc("toolbox.combat-encounters", "combat-encounters", "Combat Encounters", "Gameplay Toolbox",
            "Combat Encounters", 202),
        doc("magic-items.rules", "magic-item-rules", "Magic Item Rules", "Magic Items", "Magic Items", 204,
            three("Magic Item Categories", "Magic Item Rarity", "Activating a Magic Item", "“The Next Dawn”",
                  "Cursed Items", "Magic Item Resilience", "Crafting Magic Items", "Sentient Magic Items")),
        doc("magic-items", "magic-items", "Magic Items A–Z", "Magic Items", "Magic Items A–Z", 209, (), "items",
            split="magic-items"),
        doc("monsters.overview", "stat-blocks-and-running-monsters", "Stat Blocks and Running a Monster", "Monsters",
            "Monsters", 254, three("Stat Block Overview", "Parts of a Stat Block", "Running a Monster")),
        doc("monsters", "monsters", "Monsters A–Z", "Monsters", "Monsters A–Z", 258, (), "monsters",
            split="monsters"),
        doc("animals", "animals", "Animals", "Animals", "Animals", 344, (), "animals", split="animals"),
    ]
    for index, item in enumerate(plan):
        item["order"] = (index + 1) * 100
    return plan


def class_note(item: dict) -> str:
    name, subclass = item["class_name"], item["subclass"]
    text = (f"This chapter presents the {name}. Start with the Core {name} Traits table and the {name} Features "
            f"table, then read the class features in level order.")
    if item["caster"]:
        text += f" The {name} Spell List names every spell the class can prepare."
    return text + f" The {subclass} subclass follows at the end."


# ---------------------------------------------------------------------------
# Segmentation: reading-order lines -> blocks
# ---------------------------------------------------------------------------


def column_for(position: int, cols: list[int]) -> int:
    best = 0
    for index, start in enumerate(cols):
        if start <= position + 2:
            best = index
    return best


def split_wide(position: int, text: str, cols: list[int]) -> list[tuple[int, str]]:
    index = column_for(position, cols)
    if index + 1 >= len(cols) or position + len(text) <= cols[index + 1] + 1:
        return [(position, text)]
    limit = cols[index + 1] - position - 1
    cut = text.rfind(" ", 0, max(limit, 1) + 1)
    if cut <= 0:
        return [(position, text)]
    return [(position, text[:cut])] + split_wide(position + cut + 1, text[cut + 1:], cols)


def merge_starts(starts: list[int], new: list[int]) -> list[int]:
    merged = sorted(set(starts) | set(new))
    out: list[int] = []
    for value in merged:
        if out and value - out[-1] <= 2:
            continue
        out.append(value)
    return out


def aligned(line: Line, starts: list[int]) -> bool:
    hits = sum(1 for x, _ in line.segs if any(abs(rel(line, x) - start) <= 2 for start in starts))
    return hits >= min(2, len(line.segs))


def build_grid(lines: list[Line], keyed: bool, lexicon: set[str]) -> tuple[list[str], list[list[str]]]:
    multi = [line for line in lines if len(line.segs) >= 2]
    if not multi:
        return [""], [[join_text([line.flat for line in lines], lexicon)]]
    template = multi[0]
    for line in multi:
        if len(line.segs) > len(template.segs):
            template = line
    cols = [rel(template, x) for x, _ in template.segs]

    def cells_of(line: Line) -> list[list[str]]:
        cells: list[list[str]] = [[] for _ in cols]
        for x, text in line.segs:
            # Single-cell category rows span visual columns without becoming
            # several unrelated cells (for example Light/Medium/Heavy Armor).
            pieces = [(rel(line, x), text)] if len(line.segs) == 1 else split_wide(rel(line, x), text, cols)
            for position, piece in pieces:
                cells[column_for(position, cols)].append(piece)
        return cells

    index = 0
    header = None
    if not keyed:
        head = cells_of(lines[0])
        index = 1
        while (index < len(lines) and index < 3 and len(lines[index].segs) >= 2
               and (not head[0] or not cells_of(lines[index])[0])):
            head = [left + right for left, right in zip(head, cells_of(lines[index]))]
            index += 1
        header = [join_text(cell, lexicon) for cell in head]
    rows: list[list[list[str]]] = []
    for line in lines[index:]:
        cells = cells_of(line)
        filled = [k for k, cell in enumerate(cells) if cell]
        if rows and filled and (not cells[0] or (keyed and filled == [0] and len(line.segs) == 1)
                                or (filled == [0] and line.text[:1].islower())):
            for k in filled:
                rows[-1][k].extend(cells[k])
            continue
        rows.append(cells)
    columns = header if header is not None else [""] * len(cols)
    result = [[join_text(cell, lexicon) for cell in row] for row in rows]
    result = [row for row in result if [norm(value) for value in row] != [norm(value) for value in columns]]
    if columns and norm(columns[-1]) == "cost":
        for row in result:
            if not row[-1] and len(row) > 1:
                price = re.search(r"([\d,]+ [CSEGP]P)$", row[-2])
                if price:
                    row[-1] = price.group(1)
                    row[-2] = row[-2][:price.start()].strip()
            if len(columns) == 3 and norm(columns[1]) == "weight" and row[1].startswith("lb"):
                weight = re.search(r" (\d+(?:[½¼¾])?)$", row[0])
                if weight:
                    row[0], row[1] = row[0][:weight.start()], weight.group(1) + " " + row[1]
    return columns, result


class Segmenter:
    def __init__(self, plan: dict, lines: list[Line], lexicon: set[str], warn, marker_found: bool):
        self.plan = plan
        self.L = lines
        self.n = len(lines)
        self.lex = lexicon
        self.warn = warn
        self.mode = plan["mode"]
        self.toc = {norm(text): (text, level) for text, level in plan["subsections"]}
        self.blocks: list[dict] = []
        self.marker_found = marker_found

    # --- predicates -------------------------------------------------------

    def line(self, index: int) -> Line | None:
        return self.L[index] if 0 <= index < self.n else None

    def toc_match(self, index: int) -> int:
        line = self.L[index]
        if not self.toc or len(line.segs) != 1 or line.indent > 8 or line.col == "F":
            return 0
        if norm(line.text) in self.toc:
            return 1
        joined = line.text
        for extra in (1, 2):
            following = self.line(index + extra)
            if following is None or len(following.segs) != 1:
                break
            joined += " " + following.text
            if norm(joined) in self.toc:
                return extra + 1
        return 0

    def stat_start(self, index: int) -> bool:
        if index + 2 >= self.n:
            return False
        first, second, third = self.L[index], self.L[index + 1], self.L[index + 2]
        return name_line(first) and bool(SB_TYPE.match(second.text)) and third.flat.startswith("AC ")

    def spell_start(self, index: int) -> bool:
        following = self.line(index + 1)
        return following is not None and name_line(self.L[index]) and bool(SPELL_HEAD.match(following.text))

    def item_title_lines(self, index: int) -> int:
        for count in (1, 2):
            parts = self.L[index:index + count]
            following = self.line(index + count)
            if (len(parts) != count or following is None or not ITEM_HEAD.match(following.text)
                    or any(len(part.segs) != 1 or part.indent > 3 for part in parts)
                    or not titleish(" ".join(part.text for part in parts))):
                continue
            text = following.text
            after = self.line(index + count + 1)
            if after is not None and needs_more(text):
                text += " " + after.text
            if RARITY_WORD.search(text) or re.search(r"\bRarity Varies\b|\bVaries\b", text, re.I):
                return count
        return 0

    def item_start(self, index: int) -> bool:
        return bool(self.item_title_lines(index))

    def equipment_start(self, index: int) -> bool:
        following = self.line(index + 1)
        return (self.mode == "equipment" and following is not None
                and name_line(self.L[index])
                and bool(re.search(r"\((?:[\d,]+ [CSEGP]P|Varies)\)$", self.L[index].text)))

    def feat_start(self, index: int) -> bool:
        following = self.line(index + 1)
        return following is not None and name_line(self.L[index]) and bool(FEAT_HEAD.match(following.text))

    def entry_start(self, index: int) -> bool:
        if self.stat_start(index):
            return True
        if self.mode == "spells" and self.spell_start(index):
            return True
        if self.mode == "items" and self.item_start(index):
            return True
        return self.mode == "feats" and self.feat_start(index)

    def label_line(self, line: Line) -> bool:
        return line.indent <= 2 and line.col != "F" and all(LABEL.match(text) for _, text in line.segs)

    def is_heading(self, index: int) -> bool:
        line = self.L[index]
        text = line.text
        following = self.line(index + 1)
        if following is None or len(line.segs) != 1 or line.indent > 4 or len(text.split()) > 10:
            return False
        if text.endswith(":"):
            return name_line(following) and titleish(text)
        if not name_line(line):
            return False
        first = following.text[:1]
        return first.isupper() or first.isdigit() or first in "•“\"(+−-—"

    def table_start(self, index: int) -> bool:
        line = self.L[index]
        if len(line.segs) < 2 or line.col == "F" or self.label_line(line):
            return False
        multi = 1
        for k in range(index + 1, min(index + 4, self.n)):
            if self.L[k].col == "F":
                break
            if len(self.L[k].segs) >= 2:
                multi += 1
        if multi >= 2:
            return True
        following = self.line(index + 1)
        return (following is not None and len(following.segs) == 1
                and rel(following, following.x) >= rel(line, line.segs[1][0]) - 2)

    def block_start(self, index: int, previous: Line) -> bool:
        current = self.L[index]
        if current.col == "F" or previous.col == "F":
            return True
        if self.toc_match(index) or self.entry_start(index) or self.equipment_start(index):
            return True
        if self.mode == "class" and LEVEL_FEATURE.match(current.text):
            return True
        text = current.text
        if text.startswith("•") and current.indent <= 2:
            return True
        if NUMBERED.match(text) and current.indent <= 2:
            return True
        if ends_sentence(previous.text) and self.label_line(current):
            return True
        if self.table_start(index):
            return True
        return ends_sentence(previous.text) and self.is_heading(index)

    @staticmethod
    def new_paragraph(previous: Line, current: Line) -> bool:
        if not ends_sentence(previous.text):
            return False
        if (current.page, current.col) == (previous.page, previous.col):
            return current.indent >= 2 and current.indent > previous.indent + 1
        return current.indent >= 2

    # --- emitters ---------------------------------------------------------

    def emit(self, block: dict, used: list[Line]) -> dict:
        for line in used:
            line.used = True
        block["_pages"] = sorted({line.page for line in used})
        self.blocks.append(block)
        return block

    def run(self) -> list[dict]:
        index = 0
        if self.marker_found and self.n:
            index = self.plan.get("_marker_lines", 1)
            self.emit({"type": "heading", "level": 2,
                       "text": clean(" ".join(line.text for line in self.L[:index])), "_role": "marker"}, self.L[:index])
        else:
            self.emit({"type": "heading", "level": 2, "text": self.plan["title"], "_role": "marker",
                       "editorial": True}, [])
        while index < self.n:
            following = self.step(index)
            if following <= index:
                following = self.paragraph(index)
            index = max(following, index + 1)
        self.attach_captions()
        return self.blocks

    def step(self, index: int) -> int:
        line = self.L[index]
        if line.col == "F":
            end = index
            while end < self.n and self.L[end].col == "F" and self.L[end].page == line.page:
                end += 1
            self.table(self.L[index:end], band=True)
            return end
        matched = self.toc_match(index)
        if matched:
            return self.toc_heading(index, matched)
        if self.stat_start(index):
            return self.stat_block(index)
        if self.mode == "spells" and self.spell_start(index):
            return self.spell(index)
        if self.mode == "items" and self.item_start(index):
            return self.item(index)
        if self.mode == "feats" and self.feat_start(index):
            return self.feat(index)
        if self.label_line(line):
            return self.definitions(index)
        if self.table_start(index):
            return self.table_from(index)
        if self.is_heading(index) or (self.mode == "class" and LEVEL_FEATURE.match(line.text)):
            return self.heading(index)
        if line.text.startswith("•"):
            return self.bullets(index)
        return self.paragraph(index)

    def toc_heading(self, index: int, count: int) -> int:
        used = self.L[index: index + count]
        text = clean(" ".join(line.text for line in used))
        _, level = self.toc.pop(norm(text))
        self.emit({"type": "heading", "level": level, "text": text, "_role": "toc"}, used)
        return index + count

    def heading_level(self, text: str) -> int:
        if self.mode in ("glossary", "monsters", "animals"):
            return 3
        if self.mode in ("spells", "items"):
            return 4
        if self.mode == "class":
            if re.match(r"^(Core .+ Traits|Becoming an? .+|.+ Class Features)$", text):
                return 3
            return 4
        return 4 if self.plan["subsections"] else 3

    def heading(self, index: int) -> int:
        used = [self.L[index]]
        text = self.L[index].text
        following = self.line(index + 1)
        if text.endswith(":") and following is not None and name_line(following):
            used.append(following)
            text += " " + following.text
        text = clean(text)
        self.emit({"type": "heading", "level": self.heading_level(text), "text": text, "_role": "generic"}, used)
        return index + len(used)

    def paragraph(self, index: int) -> int:
        used = [self.L[index]]
        cursor = index + 1
        while cursor < self.n:
            previous, current = used[-1], self.L[cursor]
            if self.block_start(cursor, previous) or self.new_paragraph(previous, current):
                break
            used.append(current)
            cursor += 1
        self.emit({"type": "paragraph", "text": join_text([line.text for line in used], self.lex)}, used)
        return cursor

    def bullets(self, index: int) -> int:
        items: list[list[str]] = []
        used: list[Line] = []
        base = self.L[index].indent
        cursor = index
        while cursor < self.n:
            line = self.L[cursor]
            if line.text.startswith("•") and line.col != "F":
                items.append([line.text.lstrip("•").strip()])
                used.append(line)
                cursor += 1
                continue
            if not items or self.block_start(cursor, used[-1]):
                break
            moved = (line.page, line.col) != (used[-1].page, used[-1].col)
            if line.indent >= base + 1 or (moved and not ends_sentence(items[-1][-1])):
                items[-1].append(line.text)
                used.append(line)
                cursor += 1
                continue
            break
        self.emit({"type": "unordered-list", "items": [join_text(item, self.lex) for item in items]}, used)
        return cursor

    def definitions(self, index: int) -> int:
        entries: list[dict] = []
        used: list[Line] = []
        cursor = index
        while cursor < self.n:
            line = self.L[cursor]
            if self.label_line(line):
                for _, text in line.segs:
                    match = LABEL.match(text)
                    entries.append({"term": match.group(1), "definition": match.group(2).strip()})
                used.append(line)
                cursor += 1
                continue
            last = entries[-1]["definition"]
            if entries[-1]["term"] == "Prerequisite" and (line.text == "Invocation" or line.text.startswith("That Deals Damage")):
                entries[-1]["definition"] = join_text([last, line.text], self.lex)
                used.append(line)
                cursor += 1
                continue
            if self.block_start(cursor, used[-1]) or self.is_heading(cursor):
                break
            if needs_more(last) or line.text[:1].islower() or (line.indent >= 2 and not ends_sentence(last)):
                entries[-1]["definition"] = join_text([last, line.text], self.lex)
                used.append(line)
                cursor += 1
                continue
            break
        self.emit({"type": "definition-list", "entries": entries}, used)
        return cursor

    def table_from(self, index: int) -> int:
        first = self.L[index]
        rows = [first]
        starts = merge_starts([], [rel(first, x) for x, _ in first.segs])
        previous = self.blocks[-1] if self.blocks else None
        keyed = bool(previous and previous["type"] == "heading" and re.match(r"^Core .+ Traits$", previous["text"]))
        grouped = False
        cursor = index + 1
        while cursor < self.n:
            line = self.L[cursor]
            if line.col == "F" or self.toc_match(cursor) or self.entry_start(cursor):
                break
            if line.text.startswith("•") or self.label_line(line):
                break
            if len(line.segs) >= 2:
                rows.append(line)
                starts = merge_starts(starts, [rel(line, x) for x, _ in line.segs])
                cursor += 1
                continue
            position = rel(line, line.x)
            second = next((start for start in starts if start > starts[0] + 4), None)
            if second is not None and position >= second - 3:
                rows.append(line)
                cursor += 1
                continue
            following = self.line(cursor + 1)
            if keyed and position <= starts[0] + 2 and len(line.text) <= 30 and following is not None \
                    and len(following.segs) >= 2:
                rows.append(line)
                cursor += 1
                continue
            if (len(line.text) <= 45 and not ends_sentence(line.text)
                    and (len(rows) == 1 or grouped or line.text == "Saddle")
                    and following is not None and len(following.segs) >= 2 and aligned(following, starts)):
                grouped = True
                rows.append(line)
                cursor += 1
                continue
            if line.text[:1].islower() and len(line.text) <= 40:
                rows.append(line)
                cursor += 1
                continue
            break
        self.table(rows, band=False, keyed=keyed)
        return cursor

    def table(self, rows: list[Line], band: bool, keyed: bool = False) -> None:
        caption = ""
        body = list(rows)
        if (band and len(body) >= 2 and len(body[0].segs) == 1 and len(body[0].text) <= 60
                and titleish(body[0].text)):
            caption = clean(body[0].text)
            body = body[1:]
        columns, cells = build_grid(body, keyed, self.lex)
        if len(columns) == 4 and [norm(value) for value in columns] == ["item", "cost", "item", "cost"]:
            # Two small price tables printed side by side are a sequential list.
            cells = []
            for page in dict.fromkeys(line.page for line in body):
                _, page_cells = build_grid([line for line in body if line.page == page], keyed, self.lex)
                cells.extend(row[:2] for row in page_cells if any(row[:2]))
                cells.extend(row[2:] for row in page_cells if any(row[2:]))
            columns = columns[:2]
        self.emit({"type": "table", "caption": caption, "columns": columns, "rows": cells,
                   **({"_keyed": True} if keyed else {})}, rows)

    def attach_captions(self) -> None:
        out: list[dict] = []
        for block in self.blocks:
            previous = out[-1] if out else None
            if (block["type"] == "table" and not block["caption"] and previous is not None
                    and previous["type"] == "heading" and previous.get("_role") == "generic"):
                block["caption"] = previous["text"]
                block["_pages"] = sorted(set(block["_pages"]) | set(previous["_pages"]))
                if re.match(r"^Core .+ Traits$", previous["text"]):
                    block["_keyed"] = True
                out[-1] = block
                continue
            out.append(block)
        self.blocks = out

    # --- structured entries -------------------------------------------------

    def subtitle(self, index: int) -> tuple[str, list[Line]]:
        used = [self.L[index]]
        text = self.L[index].text
        cursor = index + 1
        while cursor < self.n and needs_more(text) and len(used) < 4:
            text = join_text([text, self.L[cursor].text], self.lex)
            used.append(self.L[cursor])
            cursor += 1
        return clean(text), used

    def spell(self, index: int) -> int:
        name = self.L[index]
        head, head_lines = self.subtitle(index + 1)
        cursor = index + 1 + len(head_lines)
        while ")" not in head.split("(", 1)[-1] and cursor < self.n and len(head_lines) < 4:
            head = join_text([head, self.L[cursor].text], self.lex)
            head_lines.append(self.L[cursor])
            cursor += 1
        props: dict[str, str] = {}
        prop_lines: list[Line] = []
        current = None
        while cursor < self.n:
            text = self.L[cursor].text
            if self.entry_start(cursor):
                break
            match = SPELL_PROP.match(text)
            if match and match.group(1) not in props:
                current = "Components" if match.group(1) == "Component" else match.group(1)
                props[current] = match.group(2).strip()
                prop_lines.append(self.L[cursor])
                cursor += 1
                continue
            # The four properties always come in sequence, so any line before the last one continues a value.
            if current and not SPELL_PROP.match(text) and (len(props) < len(SPELL_PROPS) or needs_more(props[current])):
                props[current] = join_text([props[current], text], self.lex)
                prop_lines.append(self.L[cursor])
                cursor += 1
                continue
            break
        if set(props) != set(SPELL_PROPS):
            self.warn(f"spell {name.text!r} (p. {name.page}): properties {sorted(props)}")
        match = SPELL_HEAD.match(head)
        classes_match = re.search(r"\(([^)]*)\)", head)
        classes = sorted(c.strip() for c in (classes_match.group(1) if classes_match else "").split(",") if c.strip())
        entity = {
            "type": "spell",
            "name": clean(name.text),
            "level": int(match.group("level")) if match.group("level") else 0,
            "school": match.group("school") or match.group("cschool"),
            "classes": classes,
            "castingTime": props.get("Casting Time", ""),
            "range": props.get("Range", ""),
            "components": props.get("Components", ""),
            "duration": props.get("Duration", ""),
            "concentration": "Concentration" in props.get("Duration", ""),
            "ritual": "Ritual" in props.get("Casting Time", ""),
        }
        self.emit({"type": "heading", "level": 3, "text": clean(name.text), "_role": "entry", "_entity": entity},
                  [name])
        self.emit({"type": "paragraph", "text": head, "_meta": True}, head_lines)
        if props:
            self.emit({"type": "definition-list",
                       "entries": [{"term": key, "definition": props[key]} for key in SPELL_PROPS if key in props],
                       "_meta": True}, prop_lines)
        return cursor

    def item(self, index: int) -> int:
        title_count = self.item_title_lines(index)
        names = self.L[index:index + title_count]
        name = names[0]
        title = clean(" ".join(part.text for part in names))
        text, used = self.subtitle(index + title_count)
        outside = re.sub(r"\([^)]*\)", "", text)
        rarities = sorted({match.group(1) for match in RARITY_WORD.finditer(outside)})
        if len(rarities) == 1 and not re.search(r"\bVaries\b", outside, re.I):
            rarity = rarities[0]
        else:
            rarity = "Varies"
        entity = {
            "type": "magic-item",
            "name": title,
            "category": ITEM_HEAD.match(text).group("cat"),
            "detail": text,
            "rarity": rarity,
            "attunement": "attunement" in text.lower(),
        }
        self.emit({"type": "heading", "level": 3, "text": title, "_role": "entry", "_entity": entity}, names)
        self.emit({"type": "paragraph", "text": text, "_meta": True}, used)
        return index + title_count + len(used)

    def feat(self, index: int) -> int:
        name = self.L[index]
        text, used = self.subtitle(index + 1)
        match = FEAT_HEAD.match(text)
        prerequisite = re.search(r"\(Prerequisite: (.+)\)\s*$", text)
        entity = {
            "type": "feat",
            "name": clean(name.text),
            "category": f"{match.group('cat')} Feat",
            "prerequisite": prerequisite.group(1) if prerequisite else None,
        }
        self.emit({"type": "heading", "level": 4, "text": clean(name.text), "_role": "entry", "_entity": entity},
                  [name])
        self.emit({"type": "paragraph", "text": text, "_meta": True}, used)
        return index + 1 + len(used)

    def stat_end(self, index: int) -> bool:
        if self.entry_start(index) or self.toc_match(index):
            return True
        previous = self.line(index - 1)
        return (index + 1 < self.n and self.stat_start(index + 1) and name_line(self.L[index])
                and previous is not None and ends_sentence(previous.text))

    def stat_block(self, index: int) -> int:
        name, kind = self.L[index], self.L[index + 1]
        used = [name, kind]
        entries = [{"label": "Type", "value": clean(kind.text)}]
        abilities: dict[str, tuple[str, str, str]] = {}
        cursor = index + 2
        last = None
        while cursor < self.n:
            line = self.L[cursor]
            text = line.flat
            if text in STAT_SECTIONS or (cursor > index + 2 and self.stat_end(cursor)):
                break
            if text.startswith("AC "):
                match = re.match(r"^AC (.+?)(?: Initiative (.+))?$", text)
                entries.append({"label": "AC", "value": match.group(1)})
                if match.group(2):
                    entries.append({"label": "Initiative", "value": match.group(2)})
                last = None
            elif text.startswith("Initiative "):
                entries.append({"label": "Initiative", "value": text[len("Initiative "):]})
                last = None
            elif text.startswith(("HP ", "Speed ")):
                label, _, value = text.partition(" ")
                last = {"label": label, "value": value}
                entries.append(last)
            elif MOD_SAVE.match(text):
                pass
            elif ABILITY_LINE.match(text):
                for match in ABILITY.finditer(text):
                    abilities[match.group(1)] = (match.group(2), match.group(3), match.group(4))
            else:
                label = next((item for item in STAT_LABELS if text == item or text.startswith(item + " ")), None)
                if label:
                    last = {"label": label, "value": text[len(label):].strip()}
                    entries.append(last)
                    if label == "CR":
                        last = None
                elif last is not None:
                    last["value"] = join_text([last["value"], text], self.lex)
                else:
                    break
            used.append(line)
            cursor += 1
        ability_entries = [
            {"label": key, "value": f"{abilities[key][0]} · MOD {abilities[key][1]} · SAVE {abilities[key][2]}"}
            for key in ("Str", "Dex", "Con", "Int", "Wis", "Cha") if key in abilities
        ]
        if len(ability_entries) != 6:
            self.warn(f"stat block {name.text!r} (p. {name.page}): {len(ability_entries)} ability scores")
        position = next((k for k, entry in enumerate(entries) if entry["label"] == "Speed"), len(entries) - 1) + 1
        entries[position:position] = ability_entries
        sections: list[dict] = []
        previous: Line | None = None
        while cursor < self.n:
            line = self.L[cursor]
            if self.stat_end(cursor) or line.col == "F":
                break
            if line.flat in STAT_SECTIONS:
                sections.append({"title": line.flat, "paras": []})
                used.append(line)
                previous = None
                cursor += 1
                continue
            if not sections:
                break
            paras = sections[-1]["paras"]
            fresh = previous is None or (ends_sentence(previous.text)
                                         and (line.indent >= 2 or bool(ACTION_HEAD.match(line.text))))
            if paras and not fresh:
                paras[-1].append(line.text)
            else:
                paras.append([line.text])
            used.append(line)
            previous = line
            cursor += 1
        block = {
            "type": "stat-block",
            "name": clean(name.text),
            "entries": entries,
            "sections": [{"title": s["title"], "text": "\n".join(join_text(p, self.lex) for p in s["paras"])}
                         for s in sections],
        }
        if self.mode in ("monsters", "animals"):
            block["_entity"] = creature_entity(block, "animal" if self.mode == "animals" else "monster", self.warn)
        self.emit(block, used)
        return cursor


def _first_int(value: str | None) -> int | None:
    match = re.match(r"^\s*(\d+)", value or "")
    return int(match.group(1)) if match else None


def creature_entity(block: dict, origin: str, warn) -> dict | None:
    values = {}
    for entry in block["entries"]:
        values.setdefault(entry["label"], entry["value"])
    kind = values.get("Type", "")
    size_match = re.match(rf"^({SIZE})\b", kind)
    head, _, alignment = kind.partition(", ")
    rest = re.sub(rf"^{SIZE}(?: or (?:{SIZE}|Smaller|Larger))? ", "", head, count=1)
    creature_type = re.sub(r"\s*\(.*\)$", "", rest).strip()
    swarm = re.match(r"^Swarm of (?:Tiny|Small|Medium) (\w+?)s?$", creature_type)
    if swarm:
        creature_type = swarm.group(1)
    subtype = re.search(r"\(([^)]*)\)$", rest)
    cr = re.match(r"^(\d+(?:/\d+)?) \((?:XP )?([\d,]+)(?: XP)?", values.get("CR", ""))
    if not cr:
        warn(f"stat block {block['name']!r}: unparsed CR {values.get('CR')!r}")
        return None
    legendary = any(section["title"] == "Legendary Actions" for section in block["sections"])
    return {
        "type": "creature",
        "name": block["name"],
        "origin": origin,
        "size": size_match.group(1) if size_match else None,
        "creatureType": creature_type,
        "subtype": subtype.group(1) if subtype else None,
        "alignment": alignment.strip(),
        "armorClass": _first_int(values.get("AC")),
        "hitPoints": _first_int(values.get("HP")),
        "speed": values.get("Speed", ""),
        "challenge": cr.group(1),
        "challengeValue": float(Fraction(cr.group(1))),
        "xp": int(cr.group(2).replace(",", "")),
        "legendary": legendary,
        "summary": f"{kind} · AC {values.get('AC', '–')} · HP {values.get('HP', '–')} · CR {cr.group(1)}",
    }


# ---------------------------------------------------------------------------
# Documents, rule ids, entities
# ---------------------------------------------------------------------------


def letter_group(groups: tuple[str, ...], text: str) -> int:
    letter = next((char for char in unicodedata.normalize("NFKD", text).lower() if char.isalpha()), "a")
    for index, pair in enumerate(groups):
        if pair[0] <= letter <= pair[1]:
            return index
    return len(groups) - 1


def split_catalog(item: dict, blocks: list[dict], warn) -> list[dict]:
    label, family_slug, groups = SPLITS[item["split"]]
    mode = item["mode"]
    level3 = [block for block in blocks if block["type"] == "heading" and block["level"] == 3]
    by_heading = mode not in ("monsters", "animals") or len(level3) >= 10
    assigned: list[list[dict]] = [[] for _ in groups]
    current = 0
    started = mode != "glossary"
    for block in blocks:
        anchor = None
        if by_heading and block["type"] == "heading" and block["level"] == 3:
            anchor = block["text"]
        elif not by_heading and block["type"] == "stat-block":
            anchor = block["name"]
        if anchor is not None:
            if not started and norm(anchor) == "ability check":
                started = True
            if started:
                current = max(current, letter_group(groups, anchor))
        assigned[current].append(block)
    if mode == "glossary" and not started:
        warn("glossary: first term 'Ability Check' not found; glossary kept in one group")
    docs = []
    for index, chunk in enumerate(assigned):
        if not chunk:
            continue
        first, last = groups[index][0], groups[index][1]
        letters = first.upper() if first == last else f"{first.upper()}–{last.upper()}"
        range_slug = first if first == last else f"{first}-{last}"
        if chunk[0] is not blocks[0]:
            chunk.insert(0, {"type": "heading", "level": 2, "text": f"{label} {letters}", "_role": "marker",
                             "editorial": True, "_pages": []})
        docs.append({
            "documentId": f"{item['split']}.{range_slug}",
            "slug": f"{family_slug}-{range_slug}",
            "title": f"{label} {letters}",
            "section": item["section"],
            "order": item["order"] + index + 1,
            "family": item["split"],
            "range": letters,
            "mode": mode,
            "plan": item,
            "blocks": chunk,
        })
    return docs


def assign_rule_ids(document: dict) -> None:
    used: set[str] = set()
    parents: dict[int, str] = {}
    counters: Counter = Counter()
    current = ""
    for index, block in enumerate(document["blocks"]):
        if "_fixed_key" in block:
            key = block.pop("_fixed_key")
        elif index == 0:
            key = ""
        elif block["type"] == "heading":
            level = block["level"]
            parent = next((parents[l] for l in range(level - 1, 1, -1) if l in parents), "")
            base = slug(block["text"]) or "section"
            key = base if level <= 3 or not parent else f"{parent}.{base}"
            for l in [l for l in parents if l >= level]:
                del parents[l]
        elif block["type"] == "stat-block":
            base = slug(block["name"]) or "stat-block"
            key = f"{current}.{base}" if current else base
        else:
            kind = {"paragraph": "p", "unordered-list": "list", "ordered-list": "list", "definition-list": "dl",
                    "table": "table", "original-note": "note"}[block["type"]]
            counters[(current, kind)] += 1
            key = f"{current}.{kind}-{counters[(current, kind)]}" if current else f"{kind}-{counters[(current, kind)]}"
        candidate, suffix = key, 2
        while candidate in used:
            candidate = f"{key}-{suffix}"
            suffix += 1
        used.add(candidate)
        block["ruleId"] = f"{document['documentId']}.{candidate}" if candidate else document["documentId"]
        if block["type"] == "heading":
            parents[block["level"]] = candidate
            current = candidate


def _position(blocks: list[dict], block: dict) -> int:
    return next(index for index, other in enumerate(blocks) if other is block)


def section_end(blocks: list[dict], start: int) -> int:
    head = blocks[start]
    if head["type"] != "heading":
        return start + 1
    for index in range(start + 1, len(blocks)):
        other = blocks[index]
        if other["type"] == "heading" and other["level"] <= head["level"]:
            return index
    return len(blocks)


def first_paragraph(blocks: list[dict], start: int, end: int) -> str:
    for block in blocks[start + 1: end]:
        if block["type"] == "paragraph" and not block.get("_meta") and not block.get("editorial"):
            return summary(block["text"])
    return ""


def table_entities(document: dict, warn) -> list[dict]:
    """Weapons, armor, gear, mounts, vehicles and services from equipment tables."""
    out = []
    for block in document["blocks"]:
        if block["type"] != "table":
            continue
        header = [norm(column) for column in block["columns"]]

        def col(*names):
            for name in names:
                for k, value in enumerate(header):
                    if value == name or value.startswith(name):
                        return k
            return None

        caption = block["caption"] or ""
        group = None
        for row_index, row in enumerate(block["rows"]):
            filled = [cell for cell in row if cell]
            if len(filled) <= 1:
                group = filled[0] if filled else group
                continue

            def cell(k):
                return row[k] if k is not None and k < len(row) else ""

            name = row[0]
            if name == block["columns"][0] and row == block["columns"]:
                continue
            if document["documentId"] == "equipment.services" and group:
                name = f"{group}: {name}"
            elif document["documentId"] == "equipment.mounts-and-vehicles" and group:
                name = f"{group}: {name}"
            base = {"name": name, "tableId": block["ruleId"], "rowIndex": row_index}
            if col("mastery") is not None and col("damage") is not None:
                match = re.match(r"^(Simple|Martial) (Melee|Ranged) Weapons$", group or "")
                if not match:
                    warn(f"weapon row {name!r} without weapon group")
                    continue
                entity = {**base, "type": "weapon", "weaponClass": match.group(1), "weaponKind": match.group(2),
                          "damage": cell(col("damage")), "properties": cell(col("properties")),
                          "mastery": cell(col("mastery")), "weight": cell(col("weight")), "cost": cell(col("cost"))}
                entity["summary"] = f"{entity['damage']} · {entity['properties']}"
            elif col("armor class") is not None:
                match = re.match(r"^(Light|Medium|Heavy) Armor\b|^(Shield)\b", group or "")
                if not match:
                    warn(f"armor row {name!r} without armor group")
                    continue
                entity = {**base, "type": "armor", "armorCategory": match.group(1) or match.group(2),
                          "armorClass": cell(col("armor class")), "strength": cell(col("strength")),
                          "stealth": cell(col("stealth")), "weight": cell(col("weight")), "cost": cell(col("cost"))}
                entity["summary"] = f"AC {entity['armorClass']} · {entity['cost']}"
            elif col("carrying capacity") is not None:
                entity = {**base, "type": "mount", "carryingCapacity": cell(col("carrying capacity")),
                          "cost": cell(col("cost"))}
                entity["summary"] = f"{entity['carryingCapacity']} · {entity['cost']}"
            elif col("crew") is not None:
                entity = {**base, "type": "vehicle", "speed": cell(col("speed")), "crew": cell(col("crew")),
                          "passengers": cell(col("passengers")), "cargoTons": cell(col("cargo")),
                          "armorClass": cell(col("ac")), "hitPoints": cell(col("hp")), "cost": cell(col("cost"))}
                entity["summary"] = f"{entity['speed']} · {entity['cost']}"
            elif col("cost") is not None and document["documentId"] in (
                    "equipment.services", "equipment.adventuring-gear", "equipment.mounts-and-vehicles"):
                kind = "service" if document["documentId"] == "equipment.services" else "gear"
                entity = {**base, "type": kind, "category": group or caption or document["title"],
                          "cost": cell(col("cost"))}
                if kind == "gear":
                    entity["weight"] = cell(col("weight"))
                entity["summary"] = ""
            else:
                continue
            entity["_anchor"] = block
            out.append(entity)
    return out


def document_entities(document: dict, warn) -> list[dict]:
    blocks = document["blocks"]
    mode = document["mode"]
    out: list[dict] = []
    for index, block in enumerate(blocks):
        entity = block.get("_entity")
        if entity:
            entity = dict(entity)
            entity["_anchor"] = block
            if entity["type"] != "creature":
                entity["summary"] = first_paragraph(blocks, index, section_end(blocks, index))
            out.append(entity)
    if mode == "class":
        out.extend(class_entities(document, warn))
    elif mode == "species":
        out.extend(species_entities(document))
    elif mode == "backgrounds":
        out.extend(background_entities(document))
    elif mode == "glossary":
        started = False
        for index, block in enumerate(blocks):
            if block["type"] != "heading" or block["level"] != 3:
                continue
            match = re.match(r"^(.+?)\s*\[(.+)\]$", block["text"])
            name = match.group(1) if match else block["text"]
            started = started or norm(name) == "ability check" or document["documentId"] != "glossary.a-b"
            if not started:
                continue
            out.append({"type": "glossary", "name": name, "category": match.group(2) if match else "Rule",
                        "summary": first_paragraph(blocks, index, section_end(blocks, index)), "_anchor": block})
    elif mode == "equipment":
        out.extend(table_entities(document, warn))
        out.extend(equipment_text_entities(document, out))
    return out


def _dl_values(blocks: list[dict], start: int, end: int) -> dict[str, str]:
    values: dict[str, str] = {}
    for block in blocks[start:end]:
        if block["type"] == "definition-list":
            for entry in block["entries"]:
                values.setdefault(entry["term"], entry["definition"])
    return values


def equipment_text_entities(document: dict, existing: list[dict]) -> list[dict]:
    """Tools and run-in gear entries ("Name (5 GP). ...") that are not table rows."""
    blocks = document["blocks"]
    known = {norm(entity["name"]) for entity in existing}
    out = []
    category = document["title"]
    price = re.compile(r"^(?P<name>[A-Z][^().]{1,48}?) \((?P<cost>[\d,]+ [CSEGP]P|Varies)\)(?:\.\s*(?P<text>.*))?$")
    for index, block in enumerate(blocks):
        text = block.get("text", "") if block["type"] in ("heading", "paragraph") else ""
        if document["documentId"] == "equipment.services" and block["type"] == "heading":
            lifestyle = re.match(r"^(.+) \((Free|[\d,]+ [CSEGP]P per Day)\)$", text)
            if lifestyle:
                out.append({"type": "service", "name": lifestyle.group(1), "category": "Lifestyle Expenses",
                            "cost": lifestyle.group(2), "summary": first_paragraph(blocks, index, section_end(blocks, index)),
                            "_anchor": block})
                continue
        match = price.match(text)
        if not match:
            if block["type"] == "heading" and block["level"] <= 3 and index:
                category = block["text"]
            continue
        name = match.group("name").strip()
        if document["documentId"] == "equipment.tools":
            values = _dl_values(blocks, index + 1, min(index + 4, len(blocks)))
            weight = values.get("Weight", "")
            ability = values.get("Ability", "")
            out.append({"type": "tool", "name": name, "category": category, "ability": ability,
                        "weight": weight, "cost": match.group("cost"),
                        "summary": summary(values.get("Utilize", "") or match.group("text") or ""),
                        "_anchor": block})
            continue
        if norm(name) in known:
            for entity in existing:
                if norm(entity["name"]) == norm(name) and not entity.get("summary"):
                    entity["summary"] = summary(match.group("text") or "")
                    entity["detailBlock"] = block
            continue
        if document["documentId"] == "equipment.adventuring-gear":
            out.append({"type": "gear", "name": name, "category": category, "weight": "",
                        "cost": match.group("cost"), "summary": summary(match.group("text") or ""),
                        "_anchor": block})
    return out


def class_entities(document: dict, warn) -> list[dict]:
    blocks = document["blocks"]
    plan = document["plan"]
    name = plan["class_name"]
    out = []
    heading_index = next((k for k, b in enumerate(blocks) if b["type"] == "heading" and b["text"] == name), 0)
    traits = next((b for b in blocks if b["type"] == "table" and b["caption"] == f"Core {name} Traits"), None)
    progression = next((b for b in blocks if b["type"] == "table" and b["caption"] == f"{name} Features"), None)
    features = next((b for b in blocks if b["type"] == "heading" and b["text"] == f"{name} Class Features"), None)
    values: dict[str, str] = {}
    if traits:
        rows = ([traits["columns"]] if any(traits["columns"]) else []) + traits["rows"]
        for row in rows:
            if len(row) >= 2 and row[0]:
                values[clean(row[0])] = clean(" ".join(row[1:]))
    else:
        warn(f"class {name}: Core {name} Traits table not found")

    def value(prefix):
        return next((v for k, v in values.items() if k.startswith(prefix)), "")

    die = re.search(r"D(\d+)", value("Hit Point Die"))
    saves = value("Saving Throw")
    spellcaster = any(b["type"] == "heading" and b["text"] in (f"{name} Spell List",) for b in blocks) or any(
        b["type"] == "heading" and re.match(r"^Level \d+: (Spellcasting|Pact Magic)$", b["text"]) for b in blocks)
    out.append({
        "type": "class", "name": name, "hitDie": int(die.group(1)) if die else None,
        "primaryAbility": value("Primary Ability"),
        "savingThrows": [part for part in re.split(r",? and |, ", saves) if part],
        "spellcaster": spellcaster, "armorTraining": value("Armor Training"),
        "summary": first_paragraph(blocks, heading_index, len(blocks)),
        "_anchor": blocks[heading_index], "_end": features, "_extra": [progression] if progression else [],
    })
    subclass = None
    option_kind = None
    for index, block in enumerate(blocks):
        if block["type"] != "heading":
            continue
        end = section_end(blocks, index)
        match = SUBCLASS.match(block["text"])
        if match and block["level"] == 3:
            subclass = match.group(2)
            option_kind = None
            motto = next((b["text"] for b in blocks[index + 1: index + 3] if b["type"] == "heading"), "")
            out.append({"type": "subclass", "name": subclass, "className": name, "motto": motto,
                        "summary": first_paragraph(blocks, index, end), "_anchor": block})
            continue
        if block["level"] == 3:
            option_kind = {"Metamagic Options": "Metamagic Option",
                           "Eldritch Invocation Options": "Eldritch Invocation"}.get(block["text"])
            continue
        feature = LEVEL_FEATURE.match(block["text"])
        if feature:
            out.append({"type": "class-feature", "name": feature.group(2), "className": name,
                        "level": int(feature.group(1)), "subclass": subclass,
                        "summary": first_paragraph(blocks, index, end), "_anchor": block})
        elif option_kind and block["level"] == 4:
            values_here = _dl_values(blocks, index + 1, end)
            prerequisite = values_here.get("Prerequisite")
            if prerequisite is None:
                text = next((b["text"] for b in blocks[index + 1: end] if b["type"] == "paragraph"), "")
                found = re.match(r"^Prerequisite: ([^.]+)", text)
                prerequisite = found.group(1) if found else None
            out.append({"type": "class-option", "name": block["text"], "className": name,
                        "optionKind": option_kind, "prerequisite": prerequisite,
                        "summary": first_paragraph(blocks, index, end), "_anchor": block})
    return out


def species_entities(document: dict) -> list[dict]:
    blocks = document["blocks"]
    out = []
    for index, block in enumerate(blocks):
        if block["type"] != "heading" or block.get("_role") != "toc":
            continue
        end = section_end(blocks, index)
        values = _dl_values(blocks, index + 1, end)
        traits = []
        darkvision = None
        for other in blocks[index + 1: end]:
            if other["type"] != "paragraph":
                continue
            match = re.match(r"^([A-Z][A-Za-z’' -]{2,40})\. ", other["text"])
            if match and match.group(1) not in traits:
                traits.append(match.group(1))
                if match.group(1) == "Darkvision":
                    feet = re.search(r"range of (\d+) feet", other["text"])
                    darkvision = int(feet.group(1)) if feet else None
        size_text = values.get("Size", "")
        out.append({"type": "species", "name": block["text"], "creatureType": values.get("Creature Type", ""),
                    "sizes": sorted(set(re.findall(r"\b(Tiny|Small|Medium|Large)\b", size_text)),
                                    key=("Tiny", "Small", "Medium", "Large").index),
                    "sizeText": size_text, "speed": values.get("Speed", ""), "darkvision": darkvision,
                    "traits": traits, "summary": first_paragraph(blocks, index, end), "_anchor": block})
    return out


def background_entities(document: dict) -> list[dict]:
    blocks = document["blocks"]
    out = []
    for index, block in enumerate(blocks):
        if block["type"] != "heading" or block.get("_role") != "toc" or block["level"] != 3:
            continue
        end = section_end(blocks, index)
        values = _dl_values(blocks, index + 1, end)
        feat_text = re.sub(r"\s*\(see .*\)\s*$", "", values.get("Feat", "")).strip()
        feat_match = re.match(r"^(.+?) \((.+)\)$", feat_text)
        out.append({"type": "background", "name": block["text"],
                    "abilities": [part.strip() for part in values.get("Ability Scores", "").split(",") if part.strip()],
                    "feat": feat_match.group(1) if feat_match else feat_text,
                    "featChoice": feat_match.group(2) if feat_match else None,
                    "skills": [part for part in re.split(r",? and |, ", values.get("Skill Proficiencies", "")) if part],
                    "tool": values.get("Tool Proficiency") or values.get("Tool Proficiencies"),
                    "summary": first_paragraph(blocks, index, end), "_anchor": block})
    return out


# ---------------------------------------------------------------------------
# Source coverage checks
# ---------------------------------------------------------------------------

_INDEX_ENTRY = re.compile(r"([A-Z][A-Za-z’'\-]*(?:[ ,][A-Za-z’'\-()]+)*?)\s*\.{2,}\s*(\d{1,3})(?!\d)")
_NOT_STAT_BLOCKS = {"monsters", "stat block overview", "parts of a stat block", "running a monster",
                    "monsters a–z", "animals", "index of stat blocks"}


def stat_block_index(pages: list[list[str]]) -> list[str]:
    names = set()
    for lines in pages[1:4]:
        for line in lines:
            for match in _INDEX_ENTRY.finditer(line):
                name, page = clean(match.group(1)), int(match.group(2))
                if page >= 254 and len(name) >= 3 and norm(name) not in _NOT_STAT_BLOCKS:
                    names.add(name)
    return sorted(names, key=str.casefold)


def spell_list_names(stream: list[Line]) -> list[str]:
    # Tables can occupy both columns. Read the cell immediately before each
    # school, never the prose from the other column on the same physical row.
    names = set()
    for line in stream:
        if not 28 <= line.page <= 82:
            continue
        segments = [part for _, part in line.segs]
        for index, part in enumerate(segments):
            if part in SCHOOLS and index:
                candidate = clean(segments[index - 1])
                if len(candidate) > 1 and titleish(candidate):
                    names.add(candidate)
    return sorted(names, key=str.casefold)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def encode(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def digest(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def block_text(block: dict) -> str:
    kind = block["type"]
    if kind in ("heading", "paragraph"):
        return block["text"]
    if kind in ("ordered-list", "unordered-list"):
        return " ".join(block["items"])
    if kind == "definition-list":
        return " ".join(f"{entry['term']} {entry['definition']}" for entry in block["entries"])
    if kind == "table":
        return " ".join([block["caption"], *block["columns"]] + [cell for row in block["rows"] for cell in row])
    if kind == "stat-block":
        parts = [block["name"]] + [f"{e['label']} {e['value']}" for e in block["entries"]]
        parts += [f"{s['title']} {s['text']}" for s in block["sections"]]
        return " ".join(parts)
    return " ".join(value for value in (block.get("title"), block["text"]) if value)


def public_block(block: dict) -> dict:
    return {key: value for key, value in block.items() if not key.startswith("_")}


def build(source_text: str, source_bytes: bytes, pdf_sha: str | None) -> tuple[dict[str, object], dict]:
    warnings: list[str] = []
    warn = warnings.append
    pages = read_pages(source_text)
    legal = clean(" ".join(pages[0]))
    if clean(ATTRIBUTION).replace("/ legalcode", "/legalcode") not in legal.replace("/ legalcode", "/legalcode"):
        raise BuildError("page 1 does not contain the required CC-BY-4.0 attribution statement")
    layout: dict[str, dict] = {}
    stream: list[Line] = []
    for number in range(FIRST_BODY_PAGE, PAGE_COUNT + 1):
        stream.extend(page_stream(pages[number - 1], number, layout))
    assign_indents(stream)
    lexicon = build_lexicon(stream)

    plan = build_plan()
    markers: list[int | None] = []
    cursor = 0
    marker_report = []
    for item in plan:
        found = None
        target = norm(item["marker"])
        for index in range(cursor, len(stream)):
            line = stream[index]
            if line.page < item["page"]:
                continue
            if line.page > item["page"] + 1:
                break
            joined_marker = line.text
            marker_lines = 1
            if len(line.segs) == 1 and index + 1 < len(stream) and norm(joined_marker) != target:
                following = stream[index + 1]
                if following.page == line.page and following.col == line.col and len(following.segs) == 1:
                    joined_marker += " " + following.text
                    marker_lines = 2
            if len(line.segs) == 1 and norm(joined_marker) == target:
                item["_marker_lines"] = marker_lines
                found = index
                break
        if found is None:
            warn(f"marker {item['marker']!r} not found on page {item['page']}–{item['page'] + 1}")
            found = next((k for k in range(cursor, len(stream)) if stream[k].page >= item["page"]), len(stream))
            item["_marker_found"] = False
        else:
            item["_marker_found"] = True
        marker_report.append({"documentId": item["id"], "marker": item["marker"], "page": stream[found].page
                              if found < len(stream) else None, "found": item["_marker_found"]})
        markers.append(found)
        cursor = found + 1 if item["_marker_found"] else found
    if markers[0] != 0:
        warn(f"{markers[0]} body lines precede the first chapter marker and are attached to it")
        markers[0] = 0
        plan[0]["_marker_found"] = False

    documents: list[dict] = []
    for index, item in enumerate(plan):
        start = markers[index]
        end = markers[index + 1] if index + 1 < len(plan) else len(stream)
        lines = stream[start:end]
        blocks = Segmenter(item, lines, lexicon, warn, item["_marker_found"]).run()
        if item.get("split"):
            documents.extend(split_catalog(item, blocks, warn))
        else:
            documents.append({"documentId": item["id"], "slug": item["slug"], "title": item["title"],
                              "section": item["section"], "order": item["order"], "mode": item["mode"],
                              "plan": item, "blocks": blocks})

    for document in documents:
        item = document["plan"]
        if "family" in document:
            note = FAMILY_NOTES[document["family"]].format(range=document["range"])
        elif item["mode"] == "class":
            note = class_note(item)
        else:
            note = NOTES[document["documentId"]]
        document["blocks"].insert(1, {"type": "original-note", "title": NOTE_TITLE, "text": note,
                                      "editorial": True, "_fixed_key": "roll-drauf-note", "_pages": []})
        assign_rule_ids(document)

    # Entities
    entities: list[dict] = []
    for document in documents:
        for entity in document_entities(document, warn):
            anchor = entity.pop("_anchor")
            end_block = entity.pop("_end", None)
            extra = entity.pop("_extra", [])
            detail = entity.pop("detailBlock", None)
            blocks = document["blocks"]
            if "tableId" in entity:
                entity_id = f"{anchor['ruleId']}.{slug(entity['name'])}"
                pages_ = anchor["_pages"]
                if detail is not None:
                    entity["detailId"] = detail["ruleId"]
            else:
                entity_id = anchor["ruleId"]
                start = _position(blocks, anchor)
                stop = _position(blocks, end_block) if end_block is not None else section_end(blocks, start)
                if end_block is not None:
                    entity["excerptEnd"] = end_block["ruleId"]
                pages_ = sorted({page for block in blocks[start:stop] + extra for page in block["_pages"]})
                if extra:
                    entity["extraBlocks"] = [block["ruleId"] for block in extra]
            entity.update({"id": entity_id, "documentId": document["documentId"], "sourcePages": pages_,
                           "anchor": anchor["ruleId"],
                           "url": f"{ROUTE}/{document['slug']}#{anchor['ruleId']}"})
            entities.append(entity)
    seen: dict[str, int] = {}
    for entity in entities:
        if entity["id"] in seen:
            seen[entity["id"]] += 1
            entity["id"] = f"{entity['id']}-{seen[entity['id']]}"
            warn(f"duplicate entity id renamed to {entity['id']}")
        else:
            seen[entity["id"]] = 1
    entities.sort(key=lambda item: (item["type"], item["name"].casefold(), item["id"]))
    counts = dict(sorted(Counter(entity["type"] for entity in entities).items()))

    # Coverage checks against the source's own inventories
    body_lines = [line for line in stream]
    consumed = sum(1 for line in body_lines if line.used)
    unconsumed = [{"page": line.page, "col": line.col, "text": line.text[:80]}
                  for line in body_lines if not line.used]
    represented = sorted({line.page for line in body_lines if line.used})
    expected_creatures = stat_block_index(pages)
    found_creatures = {norm(e["name"]) for e in entities if e["type"] == "creature"}
    expected_spells = spell_list_names(stream)
    found_spells = {norm(e["name"]) for e in entities if e["type"] == "spell"}
    checks = {
        "statBlockIndex": {
            "expected": len(expected_creatures),
            "found": sum(1 for name in expected_creatures if norm(name) in found_creatures),
            "missing": [name for name in expected_creatures if norm(name) not in found_creatures],
        },
        "classSpellLists": {
            "expected": len(expected_spells),
            "found": sum(1 for name in expected_spells if norm(name) in found_spells),
            "missing": [name for name in expected_spells if norm(name) not in found_spells],
        },
        "fixedCounts": {
            name: {"expected": expected, "found": counts.get(name, 0)}
            for name, expected in (("class", 12), ("subclass", 12), ("species", 9), ("background", 4), ("feat", 17))
        },
    }
    missing_pages = [page for page in range(FIRST_BODY_PAGE, PAGE_COUNT + 1) if page not in represented]
    complete = (not unconsumed and not missing_pages and not checks["statBlockIndex"]["missing"]
                and not checks["classSpellLists"]["missing"]
                and all(v["expected"] == v["found"] for v in checks["fixedCounts"].values()))

    # Package files
    files: dict[str, object] = {}
    manifest_documents = []
    navigation_sections = []
    search_entries = []
    for document in documents:
        blocks = [public_block(block) for block in document["blocks"]]
        pages_ = sorted({page for block in document["blocks"] for page in block["_pages"]})
        public = {
            "schemaVersion": "regelwerk.document.v1",
            "rulesetId": RULESET_ID,
            "documentId": document["documentId"],
            "slug": document["slug"],
            "title": document["title"],
            "navigationPath": [document["section"], document["title"]],
            "order": document["order"],
            "sourcePages": pages_,
            "contentStatus": "extracted",
            "editorialBlocks": [block["ruleId"] for block in blocks if block.get("editorial")],
            "blocks": blocks,
        }
        files[f"documents/{document['documentId']}.json"] = public
        manifest_documents.append({"documentId": document["documentId"], "slug": document["slug"],
                                   "title": document["title"], "digest": digest(public)})
        heading_stack: list[tuple[int, str]] = []
        for position, block in enumerate(blocks):
            if block["type"] == "heading":
                heading_stack = [item for item in heading_stack if item[0] < block["level"]]
                heading_stack.append((block["level"], block["text"]))
            heading = heading_stack[-1][1] if heading_stack else document["title"]
            text = block_text(block)
            search_entries.append({
                "documentId": document["documentId"], "ruleId": block["ruleId"], "title": document["title"],
                "heading": heading, "headingPath": [item[1] for item in heading_stack], "text": text,
                "normalizedText": normalized_search_text(" ".join([document["title"], heading, text])),
                "url": f"{ROUTE}/{document['slug']}#{block['ruleId']}", "order": [document["order"], position],
                "editorial": bool(block.get("editorial")),
            })
    for section_id, title in SECTIONS:
        docs = [d for d in documents if d["section"] == title]
        if docs:
            navigation_sections.append({"sectionId": section_id, "title": title, "documents": [
                {"documentId": d["documentId"], "slug": d["slug"], "title": d["title"],
                 "navigationPath": [title, d["title"]], "order": d["order"], "url": f"{ROUTE}/{d['slug']}"}
                for d in docs]})
    attribution = ATTRIBUTION + "\n"
    manifest = {
        "schemaVersion": "regelwerk.package.v1",
        "rulesetId": RULESET_ID,
        "rulesetVersion": "1.0.0",
        "edition": "2024",
        "locale": "en-US",
        "status": "published",
        "publishedAt": "2026-11-17T00:00:00Z",
        "title": "Roll Drauf Rulebook — SRD 5.2.1 (English)",
        "source": {
            "title": "System Reference Document 5.2.1",
            "publisher": "Wizards of the Coast LLC",
            "url": PDF_URL,
            "sha256": PDF_SHA256,
            "pdfVerified": pdf_sha == PDF_SHA256,
            "pageCount": PAGE_COUNT,
            "localCopy": "/static/regelwerk/SRD_CC_v5.2.1.pdf",
            "localReader": "/regelwerk/en",
            "textLayer": {"tool": "pdftotext -layout (poppler)", "sha256": hashlib.sha256(source_bytes).hexdigest(),
                          "bytes": len(source_bytes)},
        },
        "license": {
            "id": "CC-BY-4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/legalcode",
            "attributionFile": "attribution.txt",
            "attributionSha256": hashlib.sha256(attribution.encode("utf-8")).hexdigest(),
        },
        "editorialPolicy": EDITORIAL_POLICY,
        "builder": {"tool": BUILDER, "version": BUILDER_VERSION},
        "documents": manifest_documents,
    }
    package_digest = digest({"manifest": manifest})
    navigation = {
        "schemaVersion": "regelwerk.navigation.v1",
        "rulesetId": RULESET_ID,
        "rulesetVersion": manifest["rulesetVersion"],
        "sourceVersion": "5.2.1",
        "locale": "en-US",
        "kind": "srd",
        "status": manifest["status"],
        "title": manifest["title"],
        "packageDigest": package_digest,
        "readerUrl": ROUTE,
        "licenseUrl": f"{ROUTE}/license",
        "compendiumUrl": "/regelwerk/compendium?locale=en",
        "pdfUrl": "/regelwerk/en",
        "sections": navigation_sections,
    }
    public_entities = []
    for entity in entities:
        public_entities.append({key: value for key, value in entity.items() if not key.startswith("_")})
    compendium = {"schemaVersion": "regelwerk.compendium.v1", "rulesetId": RULESET_ID,
                  "rulesetVersion": manifest["rulesetVersion"], "packageDigest": package_digest,
                  "counts": counts, "entities": public_entities}
    search_index = {"schemaVersion": "regelwerk.search-index.v1", "rulesetId": RULESET_ID,
                    "rulesetVersion": manifest["rulesetVersion"], "packageDigest": package_digest,
                    "entries": search_entries}
    editorial_count = sum(1 for e in search_entries if e["editorial"])
    coverage = {
        "schemaVersion": "regelwerk.coverage.v1",
        "rulesetId": RULESET_ID,
        "rulesetVersion": manifest["rulesetVersion"],
        "packageDigest": package_digest,
        "complete": complete,
        "pageCount": PAGE_COUNT,
        "frontMatterPages": {"legal": [1], "contentsAndIndex": [2, 3, 4],
                             "treatment": "Page 1 is reproduced as the license page; pages 2–4 are replaced by "
                                          "navigation and used to verify the stat block inventory."},
        "representedPageRanges": _ranges(represented),
        "missingPageRanges": _ranges(missing_pages),
        "sourceLines": {"total": len(body_lines), "consumed": consumed, "unconsumed": len(unconsumed)},
        "documents": len(documents),
        "sections": [title for _, title in SECTIONS],
        "entityCounts": counts,
        "checks": checks,
        "blocks": {"official": len(search_entries) - editorial_count, "editorial": editorial_count},
        "editorialPolicy": EDITORIAL_POLICY["statement"],
    }
    report = {
        "builder": {"tool": BUILDER, "version": BUILDER_VERSION},
        "sourceTextSha256": manifest["source"]["textLayer"]["sha256"],
        "pdfSha256": pdf_sha,
        "markers": marker_report,
        "layout": layout,
        "documents": [{"documentId": d["documentId"], "blocks": len(d["blocks"]),
                       "headings": sum(1 for b in d["blocks"] if b["type"] == "heading"),
                       "tables": sum(1 for b in d["blocks"] if b["type"] == "table"),
                       "statBlocks": sum(1 for b in d["blocks"] if b["type"] == "stat-block")} for d in documents],
        "unconsumedLines": unconsumed[:200],
        "checks": checks,
        "warnings": warnings[:1000],
        "warningCount": len(warnings),
    }
    files.update({
        "manifest.json": manifest,
        "attribution.txt": attribution,
        "generated/navigation.json": navigation,
        "generated/search-index.json": search_index,
        "generated/compendium.json": compendium,
        "generated/coverage.json": coverage,
        "generated/build-report.json": report,
    })
    return files, coverage


def _ranges(values: list[int]) -> list[dict]:
    out: list[dict] = []
    for value in sorted(values):
        if out and value == out[-1]["last"] + 1:
            out[-1]["last"] = value
        else:
            out.append({"first": value, "last": value})
    return out


def write(files: dict[str, object], out_dir: Path) -> None:
    if out_dir.name != RULESET_ID:
        raise BuildError(f"refusing to write outside a {RULESET_ID} package directory: {out_dir}")
    for sub in ("documents", "generated"):
        target = out_dir / sub
        if target.exists():
            shutil.rmtree(target)
    for name, value in sorted(files.items()):
        path = out_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else encode(value), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source-text", required=True, type=Path, help="pdftotext -layout output of the PDF")
    parser.add_argument("--pdf", type=Path, default=DEFAULT_PDF, help="official PDF to verify (sha256 pin)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT, help="package directory (srd-5.2.1-en)")
    parser.add_argument("--check", action="store_true", help="fail if the checked-in package differs")
    parser.add_argument("--require-complete", action="store_true", help="fail unless every coverage check passes")
    args = parser.parse_args(argv)
    try:
        source_bytes = args.source_text.read_bytes()
        pdf_sha = hashlib.sha256(args.pdf.read_bytes()).hexdigest() if args.pdf and args.pdf.is_file() else None
        if pdf_sha is not None and pdf_sha != PDF_SHA256:
            raise BuildError(f"PDF sha256 {pdf_sha} does not match the pinned official file {PDF_SHA256}")
        files, coverage = build(source_bytes.decode("utf-8"), source_bytes, pdf_sha)
        if args.check:
            stale = [name for name, value in sorted(files.items())
                     if not (args.out / name).is_file()
                     or (args.out / name).read_text(encoding="utf-8") != (value if isinstance(value, str)
                                                                          else encode(value))]
            if stale:
                parser.exit(1, "English SRD package is stale: " + ", ".join(stale[:20]) + "\n")
            print("English SRD package is current.")
        else:
            write(files, args.out)
            print(f"wrote {len(files)} files to {args.out}")
        print(json.dumps({"complete": coverage["complete"], "entityCounts": coverage["entityCounts"],
                          "sourceLines": coverage["sourceLines"], "checks": {
                              key: {k: v for k, v in value.items() if k != "missing"} if "missing" in value else value
                              for key, value in coverage["checks"].items()}}, ensure_ascii=False, indent=2))
        if args.require_complete and not coverage["complete"]:
            parser.exit(2, "coverage incomplete; see generated/build-report.json\n")
        return 0
    except (BuildError, OSError, UnicodeDecodeError) as exc:
        parser.exit(1, f"English SRD build failed: {exc}\n")


if __name__ == "__main__":
    sys.exit(main())
