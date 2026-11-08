#!/usr/bin/env python3
"""Reproduce the reviewed, hash-pinned offline CC0 collection. Requires Pillow.

Run: python3 tools/import_mapmaker_assets.py --cache /tmp/mapmaker-assets-20261108
No image generation, model inference, archive execution or website crawling.
"""
import argparse
import csv
import hashlib
import html
import io
import json
import re
import urllib.request
import zipfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'vtt/static/mapmaker/assets'
APP = ASSETS.parent


def sha(data):
    return hashlib.sha256(data).hexdigest()


def read_source(cache, name, url, expected):
    path = cache / name
    if not path.exists():
        req = urllib.request.Request(url, headers={'User-Agent': 'RollDrauf-Kartenwerkstatt/1.0 (offline CC0 asset import)'})
        with urllib.request.urlopen(req, timeout=60) as response:
            data = response.read(150_000_001)
        if len(data) > 150_000_000:
            raise ValueError('Source exceeds size limit')
        if sha(data) != expected:
            raise ValueError(f'Source hash mismatch: {name}')
        path.write_bytes(data)
    data = path.read_bytes()
    if sha(data) != expected:
        raise ValueError(f'Source hash mismatch: {name}')
    return data


def category(path):
    text = path.lower()
    if re.search(r'cartouche|map element|marker|horn|crown|scale|unit|people|war|weird|compass|cross|border', text):
        return 'Dekoration & Zeichen'
    if re.search(r'flora|forest|tree|scrub|orchard|vineyard|wilds|palm|plant', text):
        return 'Wälder & Pflanzen'
    if re.search(r'field|farm|garden|cultivat|agricult', text):
        return 'Felder & Gärten'
    if re.search(r'mountain|hill|landform|rock|cave|cliff', text):
        return 'Gebirge & Felsen'
    if re.search(r'lake|wave|water|boat|ship|anchor|river|sea', text):
        return 'Gewässer & Küsten'
    if re.search(r'city|cities|town|village|hamlet|settlement', text):
        return 'Siedlungen'
    return 'Gebäude & Bauwerke'


WORDS = {
    'mountain range': 'Bergkette', 'mountain ranges': 'Bergketten', 'mountain spur': 'Bergausläufer',
    'mountain cluster': 'Berggruppe', 'hill groups': 'Hügelgruppe', 'hill range': 'Hügelkette',
    'grouped mountains': 'Berggruppe', 'individual mountains': 'Einzelberg',
    'individual trees': 'Einzelbaum', 'pairs of trees': 'Baumpaar', 'grouped trees': 'Baumgruppe',
    'small house': 'Kleines Haus', 'large city': 'Großstadt', 'walled city': 'Ummauerte Stadt',
    'elevated city': 'Höhenstadt', 'market towns': 'Marktstadt', 'towns and cities': 'Stadt',
    'small town': 'Kleinstadt', 'large town': 'Große Stadt', 'town': 'Stadt', 'towns': 'Stadt',
    'mountain': 'Berg', 'mountains': 'Berge', 'hills': 'Hügel', 'hill': 'Hügel',
    'forest': 'Wald', 'forests': 'Wälder', 'trees': 'Bäume', 'tree': 'Baum', 'scrub': 'Buschwerk',
    'field': 'Feld', 'fields': 'Felder', 'garden': 'Garten', 'farm': 'Hof', 'house': 'Haus',
    'building': 'Gebäude', 'buildings': 'Gebäude', 'village': 'Dorf', 'villages': 'Dörfer',
    'city': 'Stadt', 'cities': 'Städte', 'lake': 'See', 'lakes': 'Seen', 'waves': 'Wellen',
    'bridge': 'Brücke', 'ruins': 'Ruine', 'fort': 'Festung', 'castle': 'Burg', 'church': 'Kirche',
    'chapel': 'Kapelle', 'well': 'Brunnen', 'fountain': 'Springbrunnen', 'barn': 'Scheune',
    'inn': 'Gasthaus', 'cave': 'Höhle', 'caves': 'Höhlen', 'monastery': 'Kloster',
    'monasteries': 'Klöster', 'windmill': 'Windmühle', 'monument': 'Denkmal', 'gate': 'Tor',
    'wall': 'Mauer', 'fence': 'Zaun', 'boat': 'Boot', 'boats': 'Boote', 'anchorage': 'Ankerplatz',
    'gravestone': 'Grabstein', 'marked gravestone': 'Beschrifteter Grabstein', 'cross': 'Kreuz',
}
WORD_RE = re.compile(r'\b(' + '|'.join(re.escape(k) for k in sorted(WORDS, key=len, reverse=True)) + r')\b', re.I)


def label(path):
    stem = Path(path).stem
    stem = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', stem).replace('_', ' ')
    return WORD_RE.sub(lambda m: WORDS[m.group().lower()], stem)[:100]


def write_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cache', type=Path, required=True)
    args = parser.parse_args()
    args.cache.mkdir(parents=True, exist_ok=True)
    lock = json.loads((ASSETS / 'source-lock.json').read_text())
    catalog = [{'id': 'kenney-cartography', 'name': 'Kenney · Cartography', 'manifest': 'kenney-cartography/manifest.json'}]
    manifests = [json.loads((ASSETS / catalog[0]['manifest']).read_text())]
    report = []
    for source in lock['packs']:
        dest = ASSETS / source['id']
        dest.mkdir(exist_ok=True)
        manifest = {k: v for k, v in source.items() if k not in ('textures', 'kind', 'slug')}
        manifest.update(schemaVersion=1, pack=source['name'], stamps=[], textures=[])
        excluded = []
        if source['kind'] == 'stamps':
            archive = read_source(args.cache, source['slug'] + '.zip', source['downloadUrl'], source['archiveSha256'])
            seen = set()
            with zipfile.ZipFile(io.BytesIO(archive)) as z:
                names = sorted(n for n in z.namelist() if not n.startswith('__MACOSX/') and not Path(n).name.startswith('.'))
                readmes = [z.read(n) for n in names if n.lower().endswith('.txt')]
                license_bytes = b'\n\n'.join(readmes)
                if b'CC0' not in license_bytes:
                    raise ValueError(f'CC0 evidence missing: {source["id"]}')
                (dest / 'License.txt').write_bytes(license_bytes)
                for original in names:
                    if not original.lower().endswith('.png'):
                        continue
                    if z.getinfo(original).file_size > 30_000_000:
                        raise ValueError('Image source exceeds size limit')
                    data = z.read(original)
                    with Image.open(io.BytesIO(data)) as im:
                        im = im.convert('RGBA')
                        bounds = im.getchannel('A').getbbox()
                        if not bounds:
                            excluded.append({'originalFile': original, 'reason': 'empty alpha'})
                            continue
                        im = im.crop(bounds)
                        im.thumbnail((384, 384), Image.Resampling.LANCZOS)
                        output = io.BytesIO()
                        im.save(output, format='PNG', optimize=True)
                        prepared = output.getvalue()
                        digest = sha(prepared)
                        if digest in seen:
                            excluded.append({'originalFile': original, 'reason': 'identical prepared pixels'})
                            continue
                        seen.add(digest)
                        relative = '/'.join(original.split('/')[1:])
                        key = source['slug'].replace('-', '_') + '_' + sha(relative.encode())[:16]
                        filename = key + '.png'
                        (dest / filename).write_bytes(prepared)
                        manifest['stamps'].append(dict(id='kma:' + key, file=filename, label=label(original), group=category(relative), search=relative, w=im.width, h=im.height, defaultSize=100, originalFile=original, originalSha256=sha(data), sha256=digest))
        else:
            (dest / 'License.txt').write_text('Poly Haven assets: CC0 1.0 Universal.\nLicense: https://creativecommons.org/publicdomain/zero/1.0/\nOriginal grant, including redistribution: https://polyhaven.com/license\nArtist names and original hashes: manifest.json.\nGenerative AI excluded by https://polyhaven.com/contribute\nAll textures are freely available from Poly Haven; this project is not endorsed by Poly Haven.\n')
            for entry in source['textures']:
                data = read_source(args.cache, entry['file'], entry['downloadUrl'], entry['originalSha256'])
                with Image.open(io.BytesIO(data)) as im:
                    im = im.convert('RGB').resize((256, 256), Image.Resampling.LANCZOS)
                    filename = entry['id'] + '.png'
                    output = io.BytesIO()
                    im.save(output, format='PNG', optimize=True)
                prepared = output.getvalue()
                (dest / filename).write_bytes(prepared)
                manifest['textures'].append({**entry, 'file': filename, 'w': 256, 'h': 256, 'purpose': 'material', 'sha256': sha(prepared)})
        manifest['licenseEvidenceSha256'] = sha((dest / 'License.txt').read_bytes())
        write_json(dest / 'manifest.json', manifest)
        write_json(dest / 'import-report.json', {'excluded': excluded, 'acceptedStamps': len(manifest['stamps']), 'acceptedTextures': len(manifest['textures'])})
        catalog.append({'id': source['id'], 'name': source['name'], 'manifest': source['id'] + '/manifest.json'})
        manifests.append(manifest)
        report.append({'pack': source['id'], 'stamps': len(manifest['stamps']), 'textures': len(manifest['textures']), 'excluded': len(excluded)})
        print(report[-1], flush=True)
    write_json(ASSETS / 'packs.json', {'schemaVersion': 1, 'packs': catalog})
    write_json(ASSETS / 'import-report.json', report)
    rows = []
    for pack, manifest in zip(catalog, manifests):
        for kind in ('stamps', 'textures'):
            for entry in manifest[kind]:
                rows.append({'pack': pack['id'], 'kind': kind, 'id': entry['id'], 'label': entry.get('label', entry['id']), 'category': entry.get('group', 'Material' if entry.get('purpose') == 'material' else 'Pergament'), 'file': pack['id'] + '/' + entry['file'], 'author': entry.get('author', manifest['author']), 'license': manifest['license'], 'sha256': entry['sha256'], 'source': entry.get('source', manifest['source'])})
    with (ASSETS / 'inventory.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys(), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (ROOT / 'docs/research/MAPMAKER_INVENTORY_AFTER_2026-11-08.csv').write_bytes((ASSETS / 'inventory.csv').read_bytes())
    esc = html.escape
    sections = []
    for pack, m in zip(catalog, manifests):
        authors = sorted({a.strip() for e in m['stamps'] + m['textures'] for a in e.get('author', m['author']).split(',')})
        proof = m.get('provenance', 'Kenney Cartography Pack 1.0, 2020; Originalgrafiken des Künstlers.')
        details = ''
        if pack['id'] == 'polyhaven-terrain':
            details = '<ul>' + ''.join(f'<li><a href="{esc(e["source"], quote=True)}">{esc(e["label"])}</a> – {esc(e["author"])}</li>' for e in m['textures']) + '</ul>'
        sections.append(f'<article><h2>{esc(pack["name"])}</h2><p>Von {esc("; ".join(authors))} · {len(m["stamps"])} Stempel · {len(m["textures"])} Texturen</p><p>{esc(proof)}</p>{details}<p><a href="{esc(m["source"], quote=True)}">Künstler und Originalpaket</a> · <a href="{esc(m["licenseUrl"], quote=True)}">CC0 1.0</a> · <a href="assets/{pack["id"]}/License.txt">Original- und Lizenzhinweise</a> · <a href="assets/{pack["id"]}/manifest.json">Herkunft je Datei</a></p></article>')
    credits = '''<!doctype html>
<html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Künstler &amp; Credits – Kartenwerkstatt</title><link rel="stylesheet" href="mapmaker.css"><link rel="stylesheet" href="credits.css"><link rel="icon" href="../icons/icon-maps-compass.svg"></head>
<body class="mm-credits-page"><main class="mm-credits"><a href="index.html">← Zur Kartenwerkstatt</a><h1>Künstler &amp; Credits</h1>
<p>Diese Kartenwerkstatt wächst durch die Arbeit von Künstlerinnen, Künstlern und historischen Kartografen. Danke, dass ihr eure Werke mit anderen teilt.</p>
<p>Alle unten aufgeführten Bildpakete sind unter <strong>CC0 1.0</strong> kostenlos nutzbar, auch kommerziell und in exportierten Karten. Sie sind frei bei den verlinkten Quellen erhältlich. Wir nennen die Urheber freiwillig. Die Aufnahme bedeutet keine Partnerschaft oder Empfehlung durch die Künstler.</p>
<p>Es wurden keine KI-generierten Bilder aufgenommen. Historische Kartenmotive und fotografierte Oberflächen werden nur technisch zugeschnitten und verkleinert; keine generative Bearbeitung.</p>
<p><a href="assets/inventory.csv" download>Vollständiges Asset-Inventar (CSV)</a> · <a href="assets/source-lock.json">Quellen, Originaldateihashes und Herkunft</a></p>
''' + '\n'.join(sections) + '''
<article><h2>Schriften und Projektinhalte</h2><p>Cinzel – Natanael Gama; Literata – TypeTogether; Bad Script – Roman Shchyukin. Lokal eingebundene Schriften unter der <a href="https://openfontlicense.org/open-font-license-official-text/">SIL Open Font License 1.1</a>.</p><p>Die sechs einfachen Canvas-Symbole, prozeduralen Geländematerialien, Meereswellen und die Startkarte „Die Silbermark“ sind Projektinhalte. Sie sind keine heruntergeladenen Künstler-Bildpakete.</p></article>
<p>Quellen und Lizenzen geprüft am 08.11.2026. <a href="index.html">Zurück zur Kartenwerkstatt</a></p></main></body></html>
'''
    (APP / 'credits.html').write_text(credits, encoding='utf-8')
    print('Inventory rows:', len(rows))


if __name__ == '__main__':
    main()
