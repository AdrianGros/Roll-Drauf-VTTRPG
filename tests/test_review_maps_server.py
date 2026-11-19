"""W02 review contract: project-bound own PNG images, path names and label families.

Exercises vtt/mapmaker_document.py directly, the personal library API and the
Atlas bundle (the same validator), including old documents without `assets`.
"""
import base64
import copy
import hashlib
import io
import os

import pytest
from PIL import Image

from vtt import atlas_domain
from vtt.mapmaker_document import (InvalidDocument, MAX_CUSTOM_ASSET_BYTES, MAX_CUSTOM_TOTAL_BYTES,
                                   normalize_document)
from tests.test_mapmaker_library import API, library, used  # noqa: F401


def png_bytes(size=(16, 16), color=(200, 30, 40, 255), noise=False):
    image = Image.frombytes('RGBA', size, os.urandom(size[0] * size[1] * 4)) if noise else Image.new('RGBA', size, color)
    out = io.BytesIO()
    image.save(out, format='PNG')
    return out.getvalue()


def asset(data=None, **extra):
    data = data if data is not None else png_bytes()
    with Image.open(io.BytesIO(data)) as image:
        width, height = image.size
    entry = {'id': 'custom:' + hashlib.sha256(data).hexdigest(), 'label': 'Wachturm',
             'png': 'data:image/png;base64,' + base64.b64encode(data).decode(),
             'width': width, 'height': height, 'style': 'pixel', 'perspective': 'side',
             'source': 'Eigene Zeichnung', 'license': 'CC0 1.0'}
    entry.update(extra)
    return entry


def document(assets=None, stamp=None, symbol=None, tile=None, path=None, label=None):
    stamps = [stamp] if stamp else []
    labels = [label or {'id': 'l1', 'x': 40, 'y': 50, 'text': 'Hafen', 'style': 'town', 'size': 30}]
    if symbol:
        labels[0].update(place={'kind': 'harbor', 'lore': ''}, symbol={'asset': symbol, 'size': 40})
    doc = {'format': 'rd-mapmaker', 'version': 1, 'size': {'w': 256, 'h': 256}, 'meta': {'title': 'Eigene Bilder'}, 'sea': {},
           'layers': [
               {'id': 's', 'kind': 'stamps', 'name': 'Symbole', 'items': stamps},
               {'id': 'w', 'kind': 'paths', 'name': 'Wege', 'items': [path or {
                   'id': 'p1', 'x': 10, 'y': 10, 'material': 'road', 'width': 6, 'points': [{'x': 0, 'y': 0}, {'x': 30, 'y': 5}]}]},
               {'id': 't', 'kind': 'labels', 'name': 'Orte', 'items': labels},
           ]}
    if tile:
        doc['layers'].append({'id': 'k', 'kind': 'tiles', 'name': 'Kacheln', 'grid': {'size': 32}, 'palette': [tile], 'cells': [0, 0, 0]})
    if assets is not None:
        doc['assets'] = assets
    return doc


def test_old_documents_without_assets_keep_their_exact_normal_form():
    old = document()
    normalized, data = normalize_document(old)
    assert 'assets' not in normalized and b'"assets"' not in data
    assert normalize_document(document(assets=[]))[0] == normalized
    path = normalized['layers'][1]['items'][0]
    label = normalized['layers'][2]['items'][0]
    assert 'name' not in path and 'font' not in label
    assert normalize_document(normalized)[0] == normalized


def test_own_image_is_embedded_with_bounded_metadata_and_resolves_everywhere():
    entry = asset(label='  Wachturm\x07 ', source='x' * 300, license='y' * 200)
    stamp = {'id': 'st1', 'asset': entry['id'], 'x': 20, 'y': 30, 'size': 40, 'crop': {'x': 2, 'y': 2, 'w': 14, 'h': 14}}
    normalized, _ = normalize_document(document([entry], stamp=stamp, symbol=entry['id'], tile=entry['id']))
    (own,) = normalized['assets']
    assert own['id'] == entry['id'] and own['png'] == entry['png']
    assert own['label'] == 'Wachturm' and len(own['source']) == 200 and len(own['license']) == 120
    assert (own['width'], own['height'], own['style'], own['perspective']) == (16, 16, 'pixel', 'side')
    assert normalized['layers'][0]['items'][0]['crop'] == {'x': 2, 'y': 2, 'w': 14, 'h': 14}
    assert normalized['layers'][2]['items'][0]['symbol']['asset'] == entry['id']
    assert normalized['layers'][3]['palette'] == [entry['id']]
    # Idempotent: a stored project normalizes to itself (library reload, Atlas copy).
    assert normalize_document(normalized)[0] == normalized
    # Unknown or absent optional fields use the documented defaults.
    plain = asset()
    for key in ('style', 'perspective', 'source', 'license', 'label'):
        plain.pop(key)
    (own,) = normalize_document(document([plain]))[0]['assets']
    assert (own['style'], own['perspective'], own['source'], own['license'], own['label']) == ('other', 'top', '', '', 'Eigenes Bild')


def jpeg_as_png_entry():
    out = io.BytesIO()
    Image.new('RGB', (16, 16), (1, 2, 3)).save(out, format='JPEG')
    data = out.getvalue()
    return asset(png_bytes(), id='custom:' + hashlib.sha256(data).hexdigest(), png='data:image/png;base64,' + base64.b64encode(data).decode())


def apng_entry():
    out = io.BytesIO()
    frames = [Image.new('RGBA', (16, 16), color) for color in ((255, 0, 0, 255), (0, 255, 0, 255))]
    frames[0].save(out, format='PNG', save_all=True, append_images=frames[1:])
    return asset(out.getvalue())


@pytest.mark.parametrize('broken', [
    lambda: asset(id='custom:' + '0' * 64),                       # id must be the SHA-256 of the bytes
    lambda: asset(id='kenney:castle'),
    lambda: asset(width=17),                                       # declared size must match the PNG
    lambda: asset(height=0),
    lambda: asset(png_bytes((2049, 4))),                           # at most 2048 per side
    lambda: asset(png='https://example.invalid/tower.png'),        # no URLs
    lambda: asset(png='data:image/svg+xml;base64,' + base64.b64encode(b'<svg onload="x()"/>').decode()),
    lambda: asset(png='data:image/png;base64,***'),
    jpeg_as_png_entry,                                             # decoded content must be PNG
    apng_entry,                                                    # single frame only
    lambda: asset(style='gif'),
    lambda: asset(perspective=3),
    lambda: asset(label=['Turm']),
    lambda: 'custom:abc',
])
def test_invalid_own_images_are_rejected(broken):
    with pytest.raises(InvalidDocument):
        normalize_document(document([broken()]))


def test_own_image_references_resolve_only_against_this_document():
    entry = asset()
    other = asset(png_bytes(color=(0, 0, 255, 255)))
    stamp = {'id': 'st1', 'asset': other['id'], 'x': 20, 'y': 30, 'size': 40}
    with pytest.raises(InvalidDocument):
        normalize_document(document([entry], stamp=stamp))       # image of another project
    with pytest.raises(InvalidDocument):
        normalize_document(document([entry, copy.deepcopy(entry)]))  # duplicate entry
    with pytest.raises(InvalidDocument):
        normalize_document(document([entry], stamp={'id': 'st1', 'asset': entry['id'], 'x': 1, 'y': 1, 'size': 40,
                                                    'crop': {'x': 8, 'y': 0, 'w': 9, 'h': 4}}))  # crop beyond 16 px
    with pytest.raises(InvalidDocument):
        normalize_document(document(None, symbol=entry['id']))
    with pytest.raises(InvalidDocument):
        normalize_document(document(None, tile=entry['id']))


def test_count_byte_and_pixel_budgets():
    with pytest.raises(InvalidDocument):
        normalize_document(document([asset(png_bytes(color=(i, 0, 0, 255))) for i in range(33)]))
    normalize_document(document([asset(png_bytes(color=(i, 0, 0, 255))) for i in range(32)]))
    noisy = [png_bytes((1000, 1000), noise=True) for _ in range(4)]
    assert all(len(data) <= MAX_CUSTOM_ASSET_BYTES for data in noisy)
    assert sum(len(data) for data in noisy[:3]) <= MAX_CUSTOM_TOTAL_BYTES < sum(len(data) for data in noisy)
    normalize_document(document([asset(data) for data in noisy[:3]]))
    with pytest.raises(InvalidDocument):
        normalize_document(document([asset(data) for data in noisy]))      # more than 12 MiB together
    with pytest.raises(InvalidDocument):
        normalize_document(document([asset(png_bytes((1100, 1000), noise=True))]))  # more than 4 MiB alone
    big = [asset(png_bytes((2048, 2048), color=(i, 9, 9, 255))) for i in range(2)]
    with pytest.raises(InvalidDocument):
        normalize_document(document(big))                                  # more than 8 million pixels
    normalize_document(document([big[0], asset(png_bytes((2048, 1800)))]))


def test_path_names_and_label_families_are_bounded_and_optional():
    path = {'id': 'p1', 'x': 10, 'y': 10, 'material': 'river', 'width': 6, 'name': '  Silberlauf ' + 'x' * 100,
            'points': [{'x': 0, 'y': 0}, {'x': 30, 'y': 5}]}
    label = {'id': 'l1', 'x': 40, 'y': 50, 'text': 'Hafen', 'style': 'city', 'size': 30, 'font': 'literata'}
    normalized, _ = normalize_document(document(path=path, label=label))
    assert normalized['layers'][1]['items'][0]['name'] == ('Silberlauf ' + 'x' * 100)[:80]
    assert normalized['layers'][2]['items'][0]['font'] == 'literata'
    assert 'name' not in normalize_document(document(path=dict(path, name='   ')))[0]['layers'][1]['items'][0]
    for bad in ({**label, 'font': 'comic'}, {**label, 'font': 7}):
        with pytest.raises(InvalidDocument):
            normalize_document(document(label=bad))
    with pytest.raises(InvalidDocument):
        normalize_document(document(path=dict(path, name=['x'])))


def test_library_roundtrip_keeps_own_images_and_counts_them_in_quota(library):
    _, users, clients, _ = library
    client, headers = clients[0]
    entry = asset()
    doc = document([entry], stamp={'id': 'st1', 'asset': entry['id'], 'x': 20, 'y': 30, 'size': 40})
    response = client.post(API, json={'document': doc}, headers=headers)
    assert response.status_code == 201, response.get_json()
    project = response.get_json()['project']
    assert used(users[0]) == project['sizeBytes'] == len(normalize_document(doc)[1])
    saved = client.get(API + '/' + project['id'], headers=headers).get_json()['document']
    assert saved == normalize_document(doc)[0] and saved['assets'][0]['png'] == entry['png']
    tampered = copy.deepcopy(saved)
    tampered['assets'][0]['id'] = 'custom:' + 'f' * 64
    rejected = client.put(API + '/' + project['id'], json={'document': tampered, 'revision': project['revision']}, headers=headers)
    assert rejected.status_code == 400 and rejected.get_json()['code'] == 'invalid_document'
    # A foreign account never reads the embedded image.
    other, other_headers = clients[1]
    assert other.get(API + '/' + project['id'], headers=other_headers).status_code == 404


def test_atlas_bundle_preserves_own_images_through_the_same_validator():
    entry = asset()
    doc = document([entry], stamp={'id': 'st1', 'asset': entry['id'], 'x': 20, 'y': 30, 'size': 40})
    picture = io.BytesIO()
    Image.new('RGBA', (256, 256), (10, 20, 30, 255)).save(picture, format='PNG')
    bundle = atlas_domain.bundle({'document': doc, 'credits': 'Wachturm – Lizenz: CC0 1.0',
                                  'png': 'data:image/png;base64,' + base64.b64encode(picture.getvalue()).decode()})
    assert bundle['document']['assets'][0]['id'] == entry['id']
    broken = copy.deepcopy(doc)
    broken['assets'][0]['width'] = 15
    with pytest.raises(atlas_domain.AtlasError):
        atlas_domain.bundle({'document': broken, 'credits': '', 'png': 'data:image/png;base64,' + base64.b64encode(picture.getvalue()).decode()})
