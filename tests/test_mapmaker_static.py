"""Static contract checks for the Kartenwerkstatt prototype (no browser needed)."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "vtt" / "static" / "mapmaker"
PACK = APP / "assets" / "kenney-cartography"
JS_FILES = sorted((APP / "js").glob("*.js"))


def test_app_files_and_entry_stub_exist():
    for name in ("index.html", "mapmaker.css", "ATTRIBUTIONS.md"):
        assert (APP / name).is_file(), name
    modules = {path.name for path in JS_FILES}
    assert {"app.js", "document.js", "history.js", "render.js", "brush.js", "tools.js", "stamps.js", "starter.js", "storage.js", "ui.js"} <= modules
    stub = (ROOT / "vtt" / "templates" / "mapmaker.html").read_text(encoding="utf-8")
    assert 'content="0; url=/static/mapmaker/index.html"' in stub
    assert 'href="/static/mapmaker/index.html"' in stub


def test_index_uses_only_relative_local_resources():
    html = (APP / "index.html").read_text(encoding="utf-8")
    refs = re.findall(r'(?:src|href)="([^"]+)"', html)
    assert refs, "expected script/style references"
    for ref in refs:
        assert not re.match(r"^(?:[a-z]+:)?//", ref), ref
        assert not ref.startswith("/"), f"{ref} would break the preview server"
        assert (APP / ref).exists(), ref
    assert '<script type="module" src="js/app.js"></script>' in html


def test_javascript_never_builds_html_from_strings_or_evals():
    forbidden = re.compile(r"\.innerHTML|\.outerHTML|insertAdjacentHTML|document\.write|\beval\s*\(|new Function\b")
    for path in JS_FILES:
        source = path.read_text(encoding="utf-8")
        assert not forbidden.search(source), path.name
        urls = [url for url in re.findall(r"https?://[^\s\"'`)]+", source) if url != "http://www.w3.org/2000/svg"]
        assert not urls, (path.name, urls)


def test_images_never_use_blob_urls_as_sources():
    # CSP img-src is 'self' data: https: — blob: image sources would be blocked.
    for path in JS_FILES:
        source = path.read_text(encoding="utf-8")
        for match in re.finditer(r"createObjectURL", source):
            assert path.name == "storage.js", f"{path.name} creates object URLs"
        assert not re.search(r"\.src\s*=\s*URL\.createObjectURL", source)


def test_stylesheet_fonts_resolve_relative_to_static():
    css = (APP / "mapmaker.css").read_text(encoding="utf-8")
    urls = re.findall(r"url\(\"?([^\")]+)\"?\)", css)
    assert urls
    for url in urls:
        assert url.startswith("../fonts/"), url
        assert (APP / url).resolve().is_file(), url


def test_curated_manifest_matches_files_and_runtime_rules():
    manifest = json.loads((PACK / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["license"] == "CC0-1.0"
    assert (PACK / "License.txt").is_file()
    stamps = manifest["stamps"]
    assert len(stamps) >= 30
    ids = set()
    for stamp in stamps:
        assert re.fullmatch(r"kenney:[a-z0-9_-]{1,40}", stamp["id"]), stamp["id"]
        assert re.fullmatch(r"[a-z0-9_]{1,40}\.png", stamp["file"]), stamp["file"]
        assert (PACK / stamp["file"]).is_file(), stamp["file"]
        assert stamp["id"] not in ids
        ids.add(stamp["id"])
    starter = (APP / "js" / "starter.js").read_text(encoding="utf-8")
    used = set(re.findall(r'"(kenney:[a-z0-9_-]+)"', starter))
    assert used and used <= ids, used - ids
    assert any(texture["id"] == "kenney:parchment" for texture in manifest["textures"])


def test_attributions_cover_assets_fonts_and_the_excluded_texture():
    text = (APP / "ATTRIBUTIONS.md").read_text(encoding="utf-8")
    assert "CC0" in text and "Kenney" in text
    assert "Open Font License" in text
    assert "background-old-paper.jpg" in text and "CC BY-SA" in text
    for path in JS_FILES + [APP / "mapmaker.css", APP / "index.html"]:
        assert "background-old-paper" not in path.read_text(encoding="utf-8"), path.name


def test_artist_catalogue_has_complete_integrity_and_local_license_evidence():
    import hashlib

    assets = APP / "assets"
    catalog = json.loads((assets / "packs.json").read_text())
    assert len(catalog["packs"]) >= 19
    all_ids = set()
    total = 0
    for pack in catalog["packs"]:
        assert re.fullmatch(r"[a-z0-9][a-z0-9-]{0,50}", pack["id"])
        assert pack["manifest"] == f'{pack["id"]}/manifest.json'
        folder = assets / pack["id"]
        manifest = json.loads((assets / pack["manifest"]).read_text())
        assert manifest["license"] in {"CC0-1.0", "CC-BY-3.0", "CC-BY-4.0", "OGA-BY-3.0"}
        assert manifest["author"] and manifest["source"].startswith("https://")
        assert manifest["license"].split("-")[0] in (folder / "License.txt").read_text()
        expected_files = set()
        for kind in ("stamps", "textures"):
            for entry in manifest[kind]:
                assert entry["id"] not in all_ids
                all_ids.add(entry["id"])
                assert re.fullmatch(r"[a-z0-9_]{1,40}\.png", entry["file"])
                content = (folder / entry["file"]).read_bytes()
                assert hashlib.sha256(content).hexdigest() == entry["sha256"]
                expected_files.add(entry["file"])
                if pack["id"].startswith("kma-"):
                    assert re.fullmatch(r"kma:[a-z0-9_-]{1,40}", entry["id"])
                    assert 0 < entry["w"] <= 384 and 0 < entry["h"] <= 384
                    assert re.fullmatch(r"[a-f0-9]{64}", entry["originalSha256"])
        assert {p.name for p in folder.glob("*.png")} == expected_files
        total += len(manifest["stamps"])
        if pack["id"] != "kenney-cartography":
            assert hashlib.sha256((folder / "License.txt").read_bytes()).hexdigest() == manifest["licenseEvidenceSha256"]
            assert manifest["provenance"] and manifest["provenanceUrl"].startswith("https://")
            assert manifest["retrievedAt"] == "2026-11-08"
    assert total >= 6000
    assert "kenney:castle" in all_ids
    credits = (APP / "credits.html").read_text()
    assert "K. M. Alexander" in credits and "Rob Tuytel" in credits and "Rico Cilliers" in credits
    assert 'href="assets/inventory.csv"' in credits
    assert 'href="credits.html"' in (APP / "index.html").read_text()
