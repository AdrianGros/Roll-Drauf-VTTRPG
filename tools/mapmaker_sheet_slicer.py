#!/usr/bin/env python3
"""Split artist tilesheets into placeable mapmaker stamps.

Two steps keep image recognition reviewable instead of authoritative:

  detect PACK   Analyse a sheet named by tools/mapmaker_slices/PACK.json (or by
                --sheet/--grid for a first draft). Grid sheets (grid-alpha-v1):
                cells are classified by their alpha channel; neighbouring cells
                whose artwork continues across the shared edge are grouped into
                one object. Gridless sheets (components-v1, --grid 0): connected
                artwork is found pixel by pixel and nearby parts are joined.
                Writes a draft profile and a numbered contact sheet for review.
  build PACK    Compile the reviewed profile into normal PNG stamps in the
                pack's manifest (additive IDs, original pixels, no resampling)
                and rebuild palette, inventory and credits. Packs that already
                ship one image per motif use singles-v1: the review names and
                classifies those originals and hides exact duplicates.

The reviewed profile is the source of truth for a build; detection only
proposes it. Nothing is generated: every output pixel is copied from the sheet.
"""
import argparse, hashlib, io, json, re, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mapmaker_catalog import ASSETS, rebuild  # noqa: E402

PROFILES = Path(__file__).resolve().parent / 'mapmaker_slices'
DETECTOR = 'grid-alpha-v1'
ALPHA_MIN = 16      # pixels at or below are treated as background
ALPHA_SOLID = 250   # a cell whose every pixel reaches this is a full tile


def sha(data): return hashlib.sha256(data).hexdigest()


def write_json(path, value, compact=False):
    text = json.dumps(value, ensure_ascii=False, separators=(',', ':')) if compact else json.dumps(value, ensure_ascii=False, indent=1)
    path.write_text(text + '\n', encoding='utf-8')


def load_sheet(pack, original_path, expected_sha=None, color_key=None):
    manifest = json.loads((ASSETS / pack / 'manifest.json').read_text())
    entry = next((s for s in manifest['stamps'] if s.get('originalPath') == original_path and 'slice' not in s), None)
    if entry is None: raise SystemExit(f'{pack}: sheet {original_path!r} is not in the manifest')
    data = (ASSETS / pack / entry['file']).read_bytes()
    # sha256 pins the stored raster (for SVG sources the reviewed rasterisation, otherwise the original PNG).
    if sha(data) != entry['sha256'] or (expected_sha and sha(data) != expected_sha):
        raise SystemExit(f'{pack}: sheet {original_path!r} does not match its pinned hash')
    img = Image.open(io.BytesIO(data)); img.load(); img = img.convert('RGBA')
    if color_key:
        key = tuple(int(color_key[i:i + 2], 16) for i in (1, 3, 5))
        raw = img.tobytes()
        img = Image.frombytes('RGBA', img.size, b''.join(b'\0\0\0\0' if tuple(raw[i:i + 3]) == key else raw[i:i + 4] for i in range(0, len(raw), 4)))
    return entry, sha(data), img


class Grid:
    def __init__(self, img, g):
        self.w, self.h = g['w'], g['h']
        self.mx, self.my = g.get('marginX', g.get('margin', 0)), g.get('marginY', g.get('margin', 0))
        self.sx, self.sy = g.get('spacingX', g.get('spacing', 0)), g.get('spacingY', g.get('spacing', 0))
        self.cols = (img.width - 2 * self.mx + self.sx) // (self.w + self.sx)
        self.rows = (img.height - 2 * self.my + self.sy) // (self.h + self.sy)
        if self.cols < 1 or self.rows < 1: raise SystemExit('Grid does not fit the sheet')

    def box(self, r, c):
        x, y = self.mx + c * (self.w + self.sx), self.my + r * (self.h + self.sy)
        return (x, y, x + self.w, y + self.h)


def alpha_cells(img, grid):
    """Per cell: RGBA crop and state empty / full / partial."""
    cells = {}
    for r in range(grid.rows):
        for c in range(grid.cols):
            part = img.crop(grid.box(r, c))
            lo, hi = part.getchannel('A').getextrema()
            state = 'empty' if hi <= ALPHA_MIN else 'full' if lo >= ALPHA_SOLID else 'partial'
            cells[r, c] = dict(state=state, image=part)
    return cells


def outline_colours(img):
    """Dominant colour of pixels bordering transparency, if the art uses outlines.

    Pixel art such as Kenney's draws a dark outline around every object. Two
    objects that merely touch meet outline to outline; a shape cut by the cell
    edge (a tree crown above its trunk) shows fill colour on both sides.
    """
    px, (w, h) = img.load(), img.size
    counts = {}
    for y in range(h):
        for x in range(w):
            p = px[x, y]
            if p[3] > ALPHA_MIN and any(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] <= ALPHA_MIN
                                        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                counts[p[:3]] = counts.get(p[:3], 0) + 1
    if not counts: return None
    top, n = max(counts.items(), key=lambda kv: kv[1])
    return top if n >= 0.35 * sum(counts.values()) else None


def is_outline(p, outline):
    return outline is not None and sum(abs(a - b) for a, b in zip(p[:3], outline)) <= 24


def contact(a, b, horizontal, outline):
    """Edge positions where artwork continues across the shared edge."""
    w, h = a.size
    if horizontal: left = [a.getpixel((w - 1, y)) for y in range(h)]; right = [b.getpixel((0, y)) for y in range(h)]
    else: left = [a.getpixel((x, h - 1)) for x in range(w)]; right = [b.getpixel((x, 0)) for x in range(w)]
    solid = lambda p: p[3] > ALPHA_MIN
    if outline is not None:
        return sum(1 for p, q in zip(left, right) if solid(p) and solid(q) and not is_outline(p, outline) and not is_outline(q, outline))
    n = len(left)
    return sum(1 for i in range(n) if solid(left[i]) and any(solid(right[j]) for j in (i - 1, i, i + 1) if 0 <= j < n))


def detect_groups(cells, grid, outline=None):
    """Group cells whose artwork continues across an edge.

    Partial cells join when a shape is cut by their shared edge. A partial cell
    that only touches a group but lies inside the group's bounding box joins
    too (the corner trees of a forest patch). Full (opaque) cells are terrain
    or wall tiles and stay single unless an object surrounds them on three
    sides, as with the solid centre of a large tree crown.
    """
    parent = {k: k for k in cells}

    def find(k):
        while parent[k] != k: parent[k] = parent[parent[k]]; k = parent[k]
        return k

    cut, touch = {}, {}
    for (r, c), cell in cells.items():
        for dr, dc in ((0, 1), (1, 0)):
            other = (r + dr, c + dc)
            if other in cells and cell['state'] != 'empty' and cells[other]['state'] != 'empty':
                if n := contact(cell['image'], cells[other]['image'], dc == 1, outline): cut[(r, c), other] = cut[other, (r, c)] = n
                if contact(cell['image'], cells[other]['image'], dc == 1, None): touch[(r, c), other] = touch[other, (r, c)] = True
    for (a, b) in cut:
        if cells[a]['state'] == cells[b]['state'] == 'partial': parent[find(a)] = find(b)

    def members():
        groups = {}
        for k in cells: groups.setdefault(find(k), []).append(k)
        return groups

    changed = True
    while changed:
        changed = False
        groups = members()
        loose = [k for k, cell in cells.items() if cell['state'] == 'partial' and len(groups[find(k)]) == 1]
        for root, group in groups.items():
            if len(group) < 2: continue
            rows, cols, inside = [r for r, _ in group], [c for _, c in group], set(group)
            for k in loose:
                if find(k) != k or not (min(rows) <= k[0] <= max(rows) and min(cols) <= k[1] <= max(cols)): continue
                if any((k, m) in touch for m in inside):
                    parent[k] = root; changed = True
        groups = members()
        for k, cell in cells.items():
            if cell['state'] != 'full' or len(groups[find(k)]) > 1: continue
            votes = {}
            for dr, dc in ((0, 1), (1, 0), (0, -1), (-1, 0)):
                o = (k[0] + dr, k[1] + dc)
                if (k, o) in touch and cells[o]['state'] == 'partial': votes[find(o)] = votes.get(find(o), 0) + 1
            best = max(votes.items(), key=lambda kv: kv[1], default=(None, 0))
            if best[1] >= 3: parent[k] = best[0]; changed = True
    return sorted((sorted(v) for v in members().values() if cells[v[0]]['state'] != 'empty'), key=lambda v: v[0])


def cell_index(grid, r, c): return r * grid.cols + c


def fmt_cells(cells): return ' '.join(f'{r},{c}' for r, c in cells)


def parse_cells(text):
    if isinstance(text, dict):  # {"rect": [col, row, w, h]}
        c0, r0, w, h = text['rect']
        return [(r, c) for r in range(r0, r0 + h) for c in range(c0, c0 + w)]
    return sorted(tuple(int(v) for v in part.split(',')) for part in text.split())


def members_of(spec, cells):
    """Composite members: listed cells must hold art; a {"rect": …} skips its empty cells."""
    members = parse_cells(spec)
    if isinstance(spec, dict): members = [k for k in members if k in cells and cells[k]['state'] != 'empty']
    return members


def compose(img, grid, members):
    """Copy member cells onto one canvas at their grid offsets; gutters are skipped."""
    r0, c0 = min(r for r, _ in members), min(c for _, c in members)
    r1, c1 = max(r for r, _ in members), max(c for _, c in members)
    out = Image.new('RGBA', ((c1 - c0 + 1) * grid.w, (r1 - r0 + 1) * grid.h), (0, 0, 0, 0))
    for r, c in members: out.paste(img.crop(grid.box(r, c)), ((c - c0) * grid.w, (r - r0) * grid.h))
    return out


def parse_rows(rows):
    """Recipe rows such as ["4,0 4,1 4,2", "- 7,1 -"]; '-' leaves a cell empty."""
    return [[None if t == '-' else tuple(int(v) for v in t.split(',')) for t in row.split()] for row in rows]


def compose_rows(img, grid, layout):
    """Arrange original cells like a tile stamp: same pixels, new neighbours."""
    out = Image.new('RGBA', (max(map(len, layout)) * grid.w, len(layout) * grid.h), (0, 0, 0, 0))
    for y, row in enumerate(layout):
        for x, k in enumerate(row):
            if k: out.alpha_composite(img.crop(grid.box(*k)), (x * grid.w, y * grid.h))
    return out


def visible_rgba(img):
    """RGBA bytes with fully transparent pixels normalised, for identity comparison only."""
    raw = img.tobytes()
    return b''.join(raw[i:i + 4] if raw[i + 3] else b'\0\0\0\0' for i in range(0, len(raw), 4))


COMPONENTS = 'components-v1'


def runs_group(runs):
    x0, y0 = min(r[1] for r in runs), min(r[0] for r in runs)
    x1, y1 = max(r[2] for r in runs), max(r[0] for r in runs) + 1
    return dict(box=(x0, y0, x1 - x0, y1 - y0), area=sum(r[2] - r[1] for r in runs), runs=runs)


def split_grid(group, cw, ch):
    """Reviewed override for a packed block: cut it along the sheet's own cw×ch cells."""
    cells = {}
    for ry, x0, x1 in group['runs']:
        x = x0
        while x < x1:
            edge = min(x1, (x // cw + 1) * cw)
            cells.setdefault((ry // ch, x // cw), []).append((ry, x, edge)); x = edge
    return [runs_group(runs) for _, runs in sorted(cells.items())]


def components(img, gap, min_area, split=None, grid_splits=None):
    """Connected artwork without a grid; parts whose pixels lie within `gap` px join.

    Proximity is measured on pixels, not boxes: staggered isometric blocks have
    overlapping boxes but separate artwork. Returns groups sorted top-left first,
    {box: (x, y, w, h), area, runs: [(y, x0, x1)]}, and separately the specks
    smaller than `min_area` pixels.
    """
    w, h = img.size
    mask = img.getchannel('A').point(lambda a: 255 if a > ALPHA_MIN else 0)
    grown = mask.filter(ImageFilter.MaxFilter(2 * (gap // 2) + 1)) if gap > 1 else mask
    solid = re.compile(rb'[^\x00]+')
    pixels, near = mask.tobytes(), grown.tobytes()
    parent, prev, rows = [], [], []

    def find(a):
        while parent[a] != a: parent[a] = parent[parent[a]]; a = parent[a]
        return a

    for y in range(h):
        current = []
        for m in solid.finditer(near[y * w:(y + 1) * w]):
            x0, x1 = m.span()
            label = len(parent); parent.append(label)
            for p0, p1, other in prev:  # 8-neighbourhood between rows
                if p0 <= x1 and p1 >= x0: parent[find(label)] = find(other)
            current.append((x0, x1, label))
        rows.append(current); prev = current
    comps = {}
    for y in range(h):
        grown_runs = rows[y]
        for m in solid.finditer(pixels[y * w:(y + 1) * w]):
            x0, x1 = m.span()
            label = next(label for g0, g1, label in grown_runs if g0 <= x0 and x1 <= g1)
            c = comps.setdefault(find(label), dict(x0=x0, y0=y, x1=x1, y1=y + 1, area=0, runs=[]))
            c['x0'], c['x1'], c['y1'] = min(c['x0'], x0), max(c['x1'], x1), y + 1
            c['area'] += x1 - x0; c['runs'].append((y, x0, x1))
    out = [dict(box=(c['x0'], c['y0'], c['x1'] - c['x0'], c['y1'] - c['y0']), area=c['area'], runs=c['runs']) for c in comps.values()]
    if grid_splits:  # keyed by the box found before any split
        out = [part for g in out for part in (split_grid(g, *grid_splits[box_key(g['box'])]) if box_key(g['box']) in grid_splits else [g])]
    if split: out = [part for g in out for part in split_valleys(g, split['ratio'], split['minSize'])]
    out.sort(key=lambda g: (g['box'][1], g['box'][0]))
    return [g for g in out if g['area'] >= min_area], [g for g in out if g['area'] < min_area]


def split_valleys(group, ratio=0.12, min_size=20):
    """Split artwork that only touches its neighbour (tree crowns in a packed row).

    Projection profiles, as in text segmentation: count opaque pixels per
    column (then per row) and cut at the deepest valley whose count is at most
    `ratio` of the peak, keeping at least `min_size` px on both sides. Parts are
    split recursively. Opt-in per reviewed sheet; a cut never adds pixels.
    """
    x, y, w, h = group['box']
    for axis in (0, 1):
        size = w if axis == 0 else h
        counts = [0] * size
        for ry, x0, x1 in group['runs']:
            if axis == 0:
                for cx in range(x0 - x, x1 - x): counts[cx] += 1
            else:
                counts[ry - y] += x1 - x0
        peak = max(counts) or 1
        best = None
        for i in range(min_size, size - min_size):
            if counts[i] <= ratio * peak and (best is None or counts[i] < counts[best]): best = i
        if best is None: continue
        cut = (x if axis == 0 else y) + best
        first, second = [], []
        for ry, x0, x1 in group['runs']:
            if axis == 1: (first if ry < cut else second).append((ry, x0, x1))
            else:
                if x0 < cut: first.append((ry, x0, min(x1, cut)))
                if x1 > cut: second.append((ry, max(x0, cut), x1))
        return [part for runs in (first, second) if runs for part in split_valleys(runs_group(runs), ratio, min_size)]
    return [group]


def component_image(img, group):
    """The group's own pixels inside its box; neighbouring artwork in the box stays transparent."""
    x, y, w, h = group['box']
    mask = Image.new('L', (w, h), 0)
    for ry, x0, x1 in group['runs']: mask.paste(255, (x0 - x, ry - y, x1 - x, ry - y + 1))
    return Image.composite(img.crop((x, y, x + w, y + h)), Image.new('RGBA', (w, h), (0, 0, 0, 0)), mask)


def box_key(box): return ','.join(str(v) for v in box)


def contact_sheet(img, grid, units, path, scale=None):
    scale = scale or max(1, min(6, 1600 // max(img.width, img.height)))
    board = Image.new('RGBA', (img.width * scale, img.height * scale), (255, 0, 255, 255))
    board.alpha_composite(img.resize(board.size, Image.NEAREST))
    draw = ImageDraw.Draw(board)
    palette = [(255, 220, 0), (0, 230, 255), (255, 80, 80), (120, 255, 120), (255, 255, 255), (255, 140, 0)]
    for i, unit in enumerate(units):
        colour = palette[i % len(palette)]
        for r, c in unit:
            x0, y0, x1, y1 = grid.box(r, c)
            draw.rectangle((x0 * scale, y0 * scale, x1 * scale - 1, y1 * scale - 1), outline=colour + (255,), width=1)
        r, c = unit[0]
        x0, y0, _, _ = grid.box(r, c)
        draw.rectangle((x0 * scale + 1, y0 * scale + 1, x0 * scale + 22, y0 * scale + 11), fill=(0, 0, 0, 200))
        draw.text((x0 * scale + 2, y0 * scale), str(i), fill=colour + (255,))
    board.convert('RGB').save(path)


def cmd_detect(args):
    profile_path = PROFILES / f'{args.pack}.json'
    profile = json.loads(profile_path.read_text()) if profile_path.exists() and not args.sheet else None
    sheet = profile['sheet']['path'] if profile else args.sheet
    g = profile['grid'] if profile else dict(zip(('w', 'h'), map(int, args.grid.split('x'))), margin=args.margin, spacing=args.spacing)
    key = profile.get('colorKey') if profile else args.color_key
    entry, digest, img = load_sheet(args.pack, sheet, color_key=key)
    out = Path(args.out); out.mkdir(parents=True, exist_ok=True)
    if (profile and profile['detector'] == COMPONENTS) or (not profile and g['w'] == 0):
        return detect_components(args, profile, sheet, digest, img, out)
    grid = Grid(img, g)
    cells = alpha_cells(img, grid)
    outline = outline_colours(img)
    groups = detect_groups(cells, grid, outline)
    contact_sheet(img, grid, groups, out / f'{args.pack}-detected.png')
    states = {s: sum(c['state'] == s for c in cells.values()) for s in ('empty', 'full', 'partial')}
    multi = [u for u in groups if len(u) > 1]
    report = dict(pack=args.pack, detector=DETECTOR, sheet=dict(path=sheet, sha256=digest, w=img.width, h=img.height),
                  grid=g, cols=grid.cols, rows=grid.rows, outline=outline, cells=states, units=len(groups), multiCellUnits=len(multi),
                  groups=[dict(n=i, cells=fmt_cells(u), states=sorted({cells[k]['state'] for k in u})) for i, u in enumerate(groups)])
    write_json(out / f'{args.pack}-detected.json', report)
    if profile:
        reviewed = [members_of(u['cells'], cells) for u in profile['composites'] if 'cells' in u]
        detected = [u for u in multi]
        missing = [fmt_cells(u) for u in detected if u not in reviewed]
        extra = [fmt_cells(u) for u in reviewed if u not in detected]
        print(json.dumps(dict(detectedMulti=len(detected), reviewedDetected=len(reviewed), notReviewed=missing, notDetected=extra), ensure_ascii=False, indent=1))
    else:
        draft = dict(schemaVersion=1, pack=args.pack, detector=DETECTOR, sheet=dict(path=sheet, sha256=digest), grid=g, colorKey=key,
                     singles=None, review=dict(status='draft'),
                     cells={fmt_cells([k]): dict(label=f'Kachel {k[0]},{k[1]}', group='Gelände & Tiles') for k in sorted(cells) if cells[k]['state'] != 'empty'},
                     composites=[dict(cells=fmt_cells(u), label=f'Objekt {i}', group='Objekte & Ausstattung', hideParts=len(u) <= 2) for i, u in enumerate(groups) if len(u) > 1])
        write_json(out / f'{args.pack}-draft.json', draft)
    print(f'{args.pack}: {grid.cols}x{grid.rows} cells {states}, {len(groups)} units, {len(multi)} multi-cell -> {out}')


def detect_components(args, profile, sheet, digest, img, out):
    params = profile['params'] if profile else dict(gap=args.gap, minArea=args.min_area)
    groups, specks = components(img, params['gap'], params['minArea'])
    scale = max(1, min(3, 1800 // max(img.size)))
    board = Image.new('RGBA', (img.width * scale, img.height * scale), (255, 0, 255, 255))
    board.alpha_composite(img.resize(board.size, Image.NEAREST))
    draw = ImageDraw.Draw(board)
    for i, g in enumerate(groups):
        x, y, w, h = (v * scale for v in g['box'])
        draw.rectangle((x, y, x + w - 1, y + h - 1), outline=(255, 220, 0, 255), width=2)
        draw.rectangle((x + 1, y + 1, x + 26, y + 12), fill=(0, 0, 0, 220)); draw.text((x + 3, y + 1), str(i), fill=(255, 220, 0, 255))
    board.convert('RGB').save(out / f'{args.pack}-detected.png')
    report = dict(pack=args.pack, detector=COMPONENTS, sheet=dict(path=sheet, sha256=digest, w=img.width, h=img.height), params=params,
                  units=len(groups), specks=len(specks), groups=[dict(n=i, box=box_key(g['box']), area=g['area']) for i, g in enumerate(groups)])
    write_json(out / f'{args.pack}-detected.json', report)
    if profile:
        keys = {box_key(g['box']) for g in groups}
        print(json.dumps(dict(detected=len(keys), notReviewed=sorted(keys - set(profile['objects'])), notDetected=sorted(set(profile['objects']) - keys)), indent=1))
    else:
        write_json(out / f'{args.pack}-draft.json', dict(schemaVersion=1, pack=args.pack, detector=COMPONENTS, sheet=dict(path=sheet, sha256=digest),
                   params=params, review=dict(status='draft'), objects={box_key(g['box']): dict(label=f'Objekt {i}', group='Objekte & Ausstattung') for i, g in enumerate(groups)}))
    print(f'{args.pack}: {len(groups)} objects, {len(specks)} specks below {params["minArea"]} px -> {out}')


def slice_id(pack, digest, layout):
    identity = f'slice-v1|{digest}|{layout}'
    return f'color:{pack}_{sha(identity.encode())[:16]}'


def grid_units(profile, img, cells, grid):
    """Reviewed grid profile → units (composites first, then cells) and excluded cells."""
    units, excluded, parts_of_objects = [], [], set()
    for unit in profile['composites']:
        if 'rows' in unit:
            layout = parse_rows(unit['rows'])
            members = sorted({k for row in layout for k in row if k})
            part, text = compose_rows(img, grid, layout), '/'.join(unit['rows'])
        else:
            members = members_of(unit['cells'], cells)
            part, text = compose(img, grid, members), fmt_cells(members)
        if not members or any(k not in cells or cells[k]['state'] == 'empty' for k in members): raise SystemExit(f'{unit["label"]}: empty or missing cell')
        units.append(dict(image=part, layout=text, label=unit['label'], group=unit['group'], kind=unit.get('kind', 'object')))
        if unit.get('hideParts'): parts_of_objects.update(members)
    specs = {parse_cells(key)[0]: spec for key, spec in profile.get('cells', {}).items()}
    for region in profile.get('regions', []):
        inside = [k for k in parse_cells(region) if k in cells and cells[k]['state'] != 'empty' and k not in specs]
        for n, k in enumerate(inside, 1):
            specs[k] = dict(region, label=region['label'] if len(inside) == 1 else f'{region["label"]} {n}', region=True)
    for k, spec in specs.items():
        key = fmt_cells([k])
        if k not in cells or cells[k]['state'] == 'empty': raise SystemExit(f'Cell {key} is empty')
        kind = spec.get('kind', 'tile')
        if kind == 'exclude':
            excluded.append(dict(cells=key, reason=spec['reason'])); continue
        hide = k in parts_of_objects or spec.get('hidden', False)
        units.append(dict(image=cells[k]['image'], layout=key, label=spec['label'], group=spec['group'], kind=kind, single=k,
                          hidden=hide, tile=not hide and kind == 'tile' and grid.w == grid.h))
    missing = [k for k, c in sorted(cells.items()) if c['state'] != 'empty' and k not in specs]
    if missing: raise SystemExit(f'Cells not accounted for in the profile: {fmt_cells(missing)}')
    return units, excluded


def component_units(profile, img):
    """Reviewed gridless profile → one unit per detected object (no tiles: artwork has no grid)."""
    params = profile['params']
    groups, specks = components(img, params['gap'], params['minArea'], params.get('split'), params.get('gridSplits'))
    found = {box_key(g['box']): g for g in groups}
    if set(found) != set(profile['objects']):
        raise SystemExit(f'Detection no longer matches the review: {sorted(set(found) ^ set(profile["objects"]))}')
    units, excluded = [], [dict(box=box_key(g['box']), reason=f'Splitter unter {params["minArea"]} Pixeln') for g in specks]
    for key, spec in profile['objects'].items():
        if spec.get('kind') == 'exclude':
            excluded.append(dict(box=key, reason=spec['reason'])); continue
        units.append(dict(image=component_image(img, found[key]), layout=f'box:{key}', label=spec['label'], group=spec['group'],
                          kind=spec.get('kind', 'object')))
    return units, excluded


SINGLES = 'singles-v1'


def build_singles(args, profile, folder, manifest, coverage, rel):
    """Name and classify a pack's original single images; no new ids, no new pixels."""
    singles, hidden = profile['singles'], profile.get('hidden', {})
    seen, order = set(), {g: n for n, g in enumerate(profile.get('groupOrder', []))}
    for s in manifest['stamps']:
        path = s['originalPath']
        s.pop('hidden', None); s.pop('tile', None)
        if path in singles:
            spec = singles[path]
            s['label'], s['group'] = spec['label'], spec['group']
            if spec.get('kind') == 'tile' and s['w'] == s['h']: s['tile'] = True
        elif path in hidden:
            s['hidden'] = True
        elif s.get('sheet') or s['group'] == 'Referenzen & Szenen':
            s['group'] = 'Referenzen & Szenen'
        else:
            raise SystemExit(f'{path}: not accounted for in the profile')
        seen.add(path)
    unknown = sorted((set(singles) | set(hidden)) - seen)
    if unknown: raise SystemExit(f'Profile names files the pack does not have: {unknown[:5]}')
    rank = {'object': 0, 'tile': 1}
    manifest['stamps'].sort(key=lambda s: (bool(s.get('hidden')), order.get(s['group'], len(order)),
                                           rank.get(singles.get(s['originalPath'], {}).get('kind'), 2)))
    manifest['sliceProfiles'] = [rel]
    coverage['slices'] = dict(profile=rel, detector=SINGLES, review=profile['review'], produced=[],
                              named=len(singles), hidden=[dict(path=k, reason=v) for k, v in sorted(hidden.items())])
    write_json(folder / 'manifest.json', manifest, compact=True)
    write_json(folder / 'coverage.json', coverage, compact=True)
    tiles = sum(bool(s.get('tile')) for s in manifest['stamps'])
    print(f'{args.pack}: {len(singles)} originals named, {tiles} grid tiles, {len(hidden)} duplicates hidden')
    if not args.no_catalog: rebuild()


def cmd_build(args):
    profile = json.loads((PROFILES / f'{args.pack}.json').read_text())
    if profile.get('schemaVersion') != 1 or profile.get('pack') != args.pack: raise SystemExit('Unsupported slice profile')
    if profile.get('review', {}).get('status') != 'reviewed': raise SystemExit('Profile has not been reviewed')
    folder = ASSETS / args.pack
    if profile['detector'] == SINGLES:
        rel = (PROFILES / f'{args.pack}.json').relative_to(PROFILES.parents[1]).as_posix()
        return build_singles(args, profile, folder, json.loads((folder / 'manifest.json').read_text()),
                             json.loads((folder / 'coverage.json').read_text()), rel)
    manifest = json.loads((folder / 'manifest.json').read_text())
    coverage = json.loads((folder / 'coverage.json').read_text())
    # A profile describes one sheet, or several under "sheets" (each with its own detector).
    units, excluded, sheets = [], [], []
    for spec in profile.get('sheets', [profile]):
        entry, digest, img = load_sheet(args.pack, spec['sheet']['path'], spec['sheet']['sha256'], spec.get('colorKey'))
        if spec['detector'] == COMPONENTS:
            grid, (found, dropped) = None, component_units(spec, img)
        else:
            grid = Grid(img, spec['grid'])
            found, dropped = grid_units(spec, img, alpha_cells(img, grid), grid)
        for unit in found: unit.update(sheet=spec['sheet']['path'], digest=digest, grid=grid)
        if 'sheets' in profile:
            for record in dropped: record['sheet'] = spec['sheet']['path']
        units += found; excluded += dropped
        sheets.append(dict(path=spec['sheet']['path'], sha256=digest, detector=spec['detector'], units=len(found)))
    by_path = {s['originalPath']: s for s in manifest['stamps'] if 'slice' not in s}
    previous = {s['id']: s for s in manifest['stamps'] if 'slice' in s}
    rel = (PROFILES / f'{args.pack}.json').relative_to(PROFILES.parents[1]).as_posix()
    hidden, labelled, produced, records, rank, tiles = set(), {}, [], [], {}, set()
    tile_files, duplicates = set(), 0

    def single_for(k, part, grid):
        """Original single image with the same visible pixels, if the pack ships one."""
        if not profile.get('singles'): return None
        original = by_path.get(profile['singles'].format(index=k[0] * grid.cols + k[1]))
        if original is None: raise SystemExit(f'Missing original single for cell {fmt_cells([k])}')
        with Image.open(folder / original['file']) as single:
            if visible_rgba(single.convert('RGBA')) != visible_rgba(part): raise SystemExit(f'Single for {fmt_cells([k])} differs from the sheet cell')
        return original

    for unit in units:
        part, layout, kind, single, grid = unit['image'], unit['layout'], unit['kind'], unit.get('single'), unit['grid']
        # Within a category: assembled objects, then single objects, then building parts and tiles.
        order = 0 if single is None else 1 if kind == 'object' else 2
        if single and (original := single_for(single, part, grid)):
            asset, file = original['id'], original['file']
            labelled[asset] = (unit['label'], unit['group'])
        else:
            buf = io.BytesIO(); part.save(buf, 'PNG', optimize=False); png = buf.getvalue()
            file = sha(png)[:32] + '.png'
            if not (folder / file).exists(): (folder / file).write_bytes(png)
            asset = slice_id(args.pack, unit['digest'], layout)
            if any(p['id'] == asset for p in produced): raise SystemExit(f'Duplicate slice {unit["sheet"]} {layout}')
            produced.append(dict(id=asset, file=file, label=unit['label'], group=unit['group'], search=f'{unit["label"]} {unit["sheet"]}',
                                 w=part.width, h=part.height, defaultSize=min(256, max(16, part.width, part.height)), sha256=sha(png),
                                 originalPath=unit['sheet'], originalSha256=unit['digest'], sheet=False, grid=grid.w if grid else 1,
                                 pixelArt=manifest.get('pixelArt', False),
                                 slice=dict(profile=rel, detector=(COMPONENTS if grid is None else DETECTOR) if 'sheets' in profile else profile['detector'],
                                            kind=kind, layout=layout)))
            records.append(dict(asset=asset, kind=kind, layout=layout, file=file, **({'sheet': unit['sheet']} if 'sheets' in profile else {})))
        rank[asset] = order
        if unit.get('hidden'): hidden.add(asset)
        elif unit.get('tile') and file in tile_files:  # identical pixels are offered once; the id still resolves
            hidden.add(asset); duplicates += 1
        elif unit.get('tile'):
            tile_files.add(file); tiles.add(asset)  # painted on the tile grid, not stamped

    new_ids = {p['id'] for p in produced}
    sliced = {sheet['path'] for sheet in sheets}
    originals = []
    for s in manifest['stamps']:
        if 'slice' in s: continue
        if s['id'] in labelled: s['label'], s['group'] = labelled[s['id']]
        # A sliced sheet moves to references; other sheets of a multi-sheet pack keep their place.
        if s.get('sheet') and ('sheets' not in profile or s['originalPath'] in sliced): s['group'] = 'Referenzen & Szenen'
        s.pop('hidden', None); s.pop('tile', None)
        if s['id'] in hidden: s['hidden'] = True
        if s['id'] in tiles: s['tile'] = True
        originals.append(s)
    for p in produced:
        if p['id'] in hidden: p['hidden'] = True
        if p['id'] in tiles: p['tile'] = True
    # Published slice IDs stay resolvable for saved maps even when a later review drops them.
    retired = [dict(previous[i], hidden=True) for i in previous if i not in new_ids]
    order = {g: n for n, g in enumerate(profile.get('groupOrder', []))}
    everything = originals + produced
    visible = sorted((s for s in everything if not s.get('hidden')), key=lambda s: (order.get(s['group'], len(order)), rank.get(s['id'], 3)))
    manifest['stamps'] = visible + [s for s in everything if s.get('hidden')] + retired
    manifest['sliceProfiles'] = [rel]
    source = dict(detector='per-sheet', sheets=sheets) if 'sheets' in profile else dict(detector=profile['detector'], sheet=profile['sheet'])
    coverage['slices'] = dict(profile=rel, **source, review=profile['review'],
                              produced=records + [dict(asset=s['id'], kind=s['slice']['kind'], layout=s['slice']['layout'], file=s['file'], retired=True) for s in retired])
    if excluded: coverage['slices']['excluded'] = excluded
    write_json(folder / 'manifest.json', manifest, compact=True)
    write_json(folder / 'coverage.json', coverage, compact=True)
    shown = sum(not s.get('hidden') for s in manifest['stamps'])
    print(f'{args.pack}: {len(produced)} new slice stamps, {len(labelled)} originals relabelled, {len(hidden)} parts hidden, '
          f'{len(tiles)} grid tiles ({duplicates} duplicates hidden), {len(excluded)} excluded, {shown} visible')
    if not args.no_catalog: rebuild()


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('detect'); d.add_argument('pack'); d.add_argument('--out', required=True)
    d.add_argument('--sheet'); d.add_argument('--grid', default='16x16'); d.add_argument('--margin', type=int, default=0)
    d.add_argument('--spacing', type=int, default=0); d.add_argument('--color-key')
    d.add_argument('--gap', type=int, default=6); d.add_argument('--min-area', type=int, default=64)
    b = sub.add_parser('build'); b.add_argument('pack'); b.add_argument('--no-catalog', action='store_true')
    a = ap.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,50}', a.pack): raise SystemExit('Invalid pack id')
    cmd_detect(a) if a.cmd == 'detect' else cmd_build(a)
