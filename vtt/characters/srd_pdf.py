"""Printable A4 character sheet for SRD characters (reportlab). Headers always print in the Roll Drauf violet."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib.utils import ImageReader

from vtt.characters import srd_inventory, srd_manage, srd_party
from vtt.rules_content.creator_rules import load_creator_data

VIOLET = colors.HexColor("#4b235a")
PARCHMENT = colors.HexColor("#fbf5e4")
RULE = colors.HexColor("#c9b99a")
INK = colors.HexColor("#2f1638")
ORDER = ("str", "dex", "con", "int", "wis", "cha")
ABILITY_LABELS = {"str": "Stärke", "dex": "Geschicklichkeit", "con": "Konstitution", "int": "Intelligenz", "wis": "Weisheit", "cha": "Charisma"}
IDENTITY_SHORT = (("pronouns", "Pronomen"), ("age", "Alter"), ("height", "Größe"), ("weight", "Gewicht"), ("eyes", "Augen"), ("hair", "Haare"), ("skin", "Haut"), ("faith", "Glaube"), ("alignment", "Gesinnung"))
IDENTITY_LONG = (("appearance", "Aussehen"), ("traits", "Persönlichkeitsmerkmale"), ("ideals", "Ideale"), ("bonds", "Bindungen"), ("flaws", "Makel"), ("backstory", "Hintergrundgeschichte"), ("notes", "Notizen"))
PROFICIENCY = {"proficient": "geübt", "expertise": "Expertise"}

BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=9, leading=12, textColor=INK)
SMALL = ParagraphStyle("small", parent=BODY, fontSize=7.5, leading=9.5, textColor=colors.HexColor("#6e5745"))
CELL = ParagraphStyle("cell", parent=BODY, fontSize=8.5, leading=10.5)
HEAD = ParagraphStyle("head", parent=BODY, fontName="Helvetica-Bold", fontSize=10.5, leading=13, textColor=colors.white)
TH = ParagraphStyle("th", parent=BODY, fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=colors.white, alignment=1)
BIG = ParagraphStyle("big", parent=BODY, fontName="Helvetica-Bold", fontSize=15, leading=18, alignment=1)
TITLE = ParagraphStyle("title", parent=BODY, fontName="Helvetica-Bold", fontSize=21, leading=25, textColor=colors.white)
SUB = ParagraphStyle("sub", parent=BODY, fontSize=10, leading=13, textColor=colors.HexColor("#efe3f4"))
WIDTH = A4[0] - 30 * mm


def _t(value):
    text = "" if value is None else str(value)
    text = text.encode("cp1252", "replace").decode("cp1252")
    return escape(text).replace("\n", "<br/>")


def _signed(value):
    return f"{int(value):+d}"


def _section(title):
    table = Table([[Paragraph(_t(title), HEAD)]], colWidths=[WIDTH])
    table.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), VIOLET), ("LEFTPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    return table


def _grid(rows, widths, header=True, align_center=False):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    style = [("GRID", (0, 0), (-1, -1), 0.4, RULE), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("BACKGROUND", (0, 1 if header else 0), (-1, -1), colors.white)]
    if header:
        style.append(("BACKGROUND", (0, 0), (-1, 0), VIOLET))
    if align_center:
        style.append(("ALIGN", (0, 0), (-1, -1), "CENTER"))
    table.setStyle(TableStyle(style))
    return table


def _avatar(char):
    if not char.avatar_storage_key:
        return None
    try:
        from vtt.storage import get_storage_adapter

        content = get_storage_adapter().download(char.avatar_storage_key)
        reader = ImageReader(BytesIO(content))
        width, height = reader.getSize()
        box = 26 * mm
        scale = min(box / width, box / height)
        return Image(BytesIO(content), width=width * scale, height=height * scale)
    except Exception:
        return None


def sheet_content(char, *, private):
    """Plain data for the PDF: the shared numbers plus identity, item texts and companions."""
    view = srd_party.shared_view(char)
    data = load_creator_data()
    cat = srd_inventory.catalog(data)
    items = [srd_inventory.item_view(row, cat) for row in srd_inventory.items_of(char)]
    state = ((char.character_data or {}).get("srd") or {}).get("state") or {}
    identity = state.get("identity") if isinstance(state.get("identity"), dict) else {}
    view["items"] = items
    view["identity"] = {key: identity.get(key) for key, _ in IDENTITY_SHORT + (IDENTITY_LONG if private else ()) if identity.get(key)}
    view["companions"] = srd_manage.companions(char)
    view["classNames"] = {c["classKey"]: c["name"] for c in data["classes"]}
    view["coinNames"] = {code: data["equipment"]["coins"][code]["name"] for code in srd_inventory.COIN_ORDER}
    return view


def _header(view, avatar):
    classes = " / ".join(f"{c['name']} {c['level']}" for c in view["classes"])
    sub = " · ".join(part for part in (view.get("species"), classes, view.get("background")) if part)
    left = [Paragraph(_t(view["name"] or "Unbenannter Charakter"), TITLE), Paragraph(_t(sub), SUB)]
    cells = [[left, avatar or ""]] if avatar else [[left]]
    widths = [WIDTH - 32 * mm, 32 * mm] if avatar else [WIDTH]
    table = Table(cells, colWidths=widths)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), VIOLET), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8), ("ALIGN", (1, 0), (1, 0), "CENTER"),
    ]))
    return table


def _vitals(view):
    hp = view["hitPoints"]
    labels = ["Trefferpunkte", "Rüstungsklasse", "Initiative", "Bewegung", "Übungsbonus", "Passive Wahrnehmung"]
    values = [f"{hp['current']} / {hp['max']}", view["armorClass"], _signed(view["initiative"]), f"{view['speedMeters']} m".replace(".", ","), _signed(view["proficiencyBonus"]), view["passivePerception"]]
    return _grid([[Paragraph(_t(l), TH) for l in labels], [Paragraph(_t(v), BIG) for v in values]], [WIDTH / 6] * 6)


def _abilities(view):
    heads = [Paragraph(_t(ABILITY_LABELS[k]), TH) for k in ORDER]
    mods = [Paragraph(f"{_signed(view['abilities'][k]['modifier'])}<br/><font size=8>Wert {view['abilities'][k]['score']}</font>", BIG) for k in ORDER]
    saves = [Paragraph(_t(f"Rettungswurf {_signed(view['saves'][k]['bonus'])}" + (" (geübt)" if view["saves"][k]["proficient"] else "")), SMALL) for k in ORDER]
    return _grid([heads, mods, saves], [WIDTH / 6] * 6, align_center=True)


def _skills(view):
    rows = [Paragraph(_t(f"{s['name']}: {_signed(s['bonus'])}" + (f" ({PROFICIENCY[s['proficiency']]})" if s["proficiency"] in PROFICIENCY else "")),
                      ParagraphStyle("sk", parent=CELL, fontName="Helvetica-Bold" if s["proficiency"] in PROFICIENCY else "Helvetica")) for s in view["skills"].values()]
    columns = 3
    rows += [""] * (-len(rows) % columns)
    table = Table([rows[i:i + columns] for i in range(0, len(rows), columns)], colWidths=[WIDTH / columns] * columns)
    table.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    return table


def _spells(view):
    flow = []
    casting = view["spellcasting"]["classes"]
    if casting:
        lines = [f"{view['classNames'].get(key, key)}: Zauber-SG {info['saveDc']}, Zauberangriff {_signed(info['attackBonus'])}" for key, info in casting.items()]
        flow.append(Paragraph(_t(" · ".join(lines)), BODY))
    slots = view["spellcasting"]["slots"]
    if any(slots):
        flow.append(Paragraph(_t("Zauberplätze: " + ", ".join(f"Grad {i + 1}: {n}" for i, n in enumerate(slots) if n)), BODY))
    by_level = {}
    for spell in view["spells"]:
        by_level.setdefault(spell["level"], []).append(spell["name"])
    for level in sorted(by_level):
        label = "Zaubertricks" if level == 0 else f"Grad {level}"
        flow.append(Paragraph(f"<b>{_t(label)}:</b> {_t(', '.join(sorted(by_level[level])))}", BODY))
    return flow


def _gear(view):
    rows = [[Paragraph(h, TH) for h in ("Gegenstand", "Anzahl", "Gewicht", "Hinweis")]]
    for item in view["items"]:
        note = []
        if item["equipped"]:
            note.append("angelegt")
        if item.get("rarity"):
            note.append(f"{item['rarity']}{', Einstimmung' if item.get('attunement') else ''}")
        if item.get("handedOut"):
            note.append("von der Spielleitung")
        rows.append([Paragraph(_t(item["name"]), CELL), Paragraph(str(item["quantity"]), CELL), Paragraph(_t(f"{item['totalKg']:g} kg".replace(".", ",")), CELL), Paragraph(_t(", ".join(note)), CELL)])
    return _grid(rows, [WIDTH * 0.46, WIDTH * 0.12, WIDTH * 0.16, WIDTH * 0.26])


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(VIOLET)
    canvas.setLineWidth(0.6)
    canvas.line(15 * mm, 12 * mm, A4[0] - 15 * mm, 12 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#6e5745"))
    canvas.drawString(15 * mm, 8 * mm, "Roll Drauf VTT · Regelwerk: Systemreferenzdokument 5.2.1 (Deutsch), CC BY 4.0")
    canvas.drawRightString(A4[0] - 15 * mm, 8 * mm, f"Seite {doc.page}")
    canvas.restoreState()


def render_pdf(char, *, private, compress=True):
    view = sheet_content(char, private=private)
    story = [_header(view, _avatar(char)), Spacer(1, 4 * mm), _vitals(view), Spacer(1, 3 * mm), _abilities(view), Spacer(1, 3 * mm),
             KeepTogether([_section("Fertigkeiten"), Spacer(1, 1.5 * mm), _skills(view)])]
    spell_flow = _spells(view)
    if spell_flow:
        story += [Spacer(1, 3 * mm), KeepTogether([_section("Zauber")] + [Spacer(1, 1.5 * mm)] + spell_flow[:1]), *spell_flow[1:]]
    if view["feats"]:
        story += [Spacer(1, 3 * mm), _section("Talente"), Spacer(1, 1.5 * mm), Paragraph(_t(", ".join(view["feats"])), BODY)]
    story += [Spacer(1, 3 * mm), _section("Ausrüstung"), Spacer(1, 1.5 * mm)]
    story.append(_gear(view) if view["items"] else Paragraph("Keine Gegenstände.", BODY))
    coins = ", ".join(f"{v} {view['coinNames'][k]}" for k, v in view["coins"].items() if v)
    story += [Spacer(1, 1.5 * mm), Paragraph(_t("Münzen: " + (coins or "keine")), BODY)]
    descriptions = [i for i in view["items"] if i.get("description") and i["kind"] == "magic"]
    for item in descriptions:
        story += [Spacer(1, 2 * mm), Paragraph(f"<b>{_t(item['name'])}</b>", BODY), Paragraph(_t(item["description"]), SMALL), Paragraph(_t(item.get("source") or ""), SMALL)]
    if view["companions"]:
        story += [Spacer(1, 3 * mm), _section("Begleiter"), Spacer(1, 1.5 * mm)]
        for companion in view["companions"]:
            facts = ", ".join(x for x in (companion.get("kind"), f"TP {companion['hpCurrent']}/{companion['hpMax']}", f"RK {companion['ac']}", companion.get("speed")) if x)
            story.append(Paragraph(f"<b>{_t(companion['name'])}</b> ({_t(facts)})", BODY))
            for field in ("attacks", "notes"):
                if companion.get(field):
                    story.append(Paragraph(_t(companion[field]), SMALL))
    labels = dict(IDENTITY_SHORT + IDENTITY_LONG)
    if view["identity"]:
        story += [Spacer(1, 3 * mm), _section("Persönliches"), Spacer(1, 1.5 * mm)]
        short = [f"{labels[k]}: {v}" for k, v in view["identity"].items() if k in dict(IDENTITY_SHORT)]
        if short:
            story.append(Paragraph(_t(" · ".join(short)), BODY))
        for key, label in IDENTITY_LONG:
            if view["identity"].get(key):
                story += [Spacer(1, 1.5 * mm), Paragraph(f"<b>{_t(label)}</b>", BODY), Paragraph(_t(view["identity"][key]), BODY)]
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=12 * mm, bottomMargin=18 * mm,
                            title=f"Charakterbogen {view['name'] or ''}".strip(), author="Roll Drauf VTT", pageCompression=1 if compress else 0)
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()
