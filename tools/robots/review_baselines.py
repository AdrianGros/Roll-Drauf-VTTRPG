"""Baseline review for the strict journey's screenshots (Regelwerk §6:
only a human blesses baselines — this tool makes that review humanly
possible at 160 screenshots per acceptance run).

Field research behind the shape (ROBOT_FLEET_AND_RULEBOOK §8.2): mass
(re)baselining is the real cost center of visual testing, so review
happens as one generated contact-sheet page grouped by checkpoint —
not as 160 individual file opens — and promotion is an explicit,
note-carrying command whose result gets committed to git.  Nothing here
runs automatically; auto-accepting diffs is how teams bless a broken UI.

Usage:
  python -m tools.robots.review_baselines --run RUNDIR
      Generate RUNDIR/baseline_review.html (open it in a browser).
  python -m tools.robots.review_baselines --run RUNDIR --promote \
      --note "warum diese Optik gewollt ist" [--only 'dm-chromium-*']
      Copy reviewed screenshots into the baseline directory and record
      provenance in baseline_manifest.json.  Refuses to overwrite a
      differing existing baseline without --force.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import html
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageChops

from tools.robots.report import REPO

BASELINE_DIR = REPO / "tools" / "robots" / "snapshots" / "strict_journey"

# Longest-suffix parse of {role}-{browser}-{viewport}-{checkpoint}.png:
# viewport and checkpoint both contain hyphens, so match known checkpoints.
CHECKPOINTS = (
    "login-initial", "login-ready", "login-recovery", "login-submitted",
    "dashboard-redirect", "dashboard-settled", "dashboard-keyboard",
    "logout-return",
)


def _parse(name: str) -> dict | None:
    stem = name[:-4] if name.endswith(".png") else name
    for checkpoint in CHECKPOINTS:
        if stem.endswith(f"-{checkpoint}"):
            head = stem[: -(len(checkpoint) + 1)]
            parts = head.split("-", 2)
            if len(parts) == 3:
                return {"role": parts[0], "browser": parts[1],
                        "viewport": parts[2], "checkpoint": checkpoint}
    return None


def _diff(baseline: Path, actual: Path, out: Path) -> int:
    """Write a diff image, return the count of differing pixels."""
    with Image.open(baseline) as base_img, Image.open(actual) as act_img:
        if base_img.size != act_img.size:
            return -1
        delta = ImageChops.difference(base_img.convert("RGB"),
                                      act_img.convert("RGB"))
        bbox = delta.getbbox()
        if bbox is None:
            return 0
        histogram = delta.convert("L").point(lambda p: 255 if p else 0)
        out.parent.mkdir(parents=True, exist_ok=True)
        histogram.save(out)
        return int(sum(histogram.point(bool).getdata()))


def _build_review(run_dir: Path, baseline_dir: Path) -> Path:
    screenshots = sorted((run_dir / "screenshots").glob("*.png"))
    rows: dict[str, list[dict]] = {}
    counts = {"new": 0, "changed": 0, "unchanged": 0, "unparsed": 0}
    for shot in screenshots:
        meta = _parse(shot.name)
        if meta is None:
            counts["unparsed"] += 1
            continue
        baseline = baseline_dir / shot.name
        entry = {"shot": shot, "meta": meta, "baseline": None,
                 "diff": None, "pixels": None}
        if baseline.exists():
            diff_path = run_dir / "review_diffs" / shot.name
            pixels = _diff(baseline, shot, diff_path)
            entry["baseline"] = baseline
            entry["pixels"] = pixels
            if pixels == 0:
                counts["unchanged"] += 1
            else:
                counts["changed"] += 1
                entry["diff"] = diff_path if pixels > 0 else None
        else:
            counts["new"] += 1
        rows.setdefault(meta["checkpoint"], []).append(entry)

    parts = [
        "<meta charset='utf-8'><title>Baseline-Review</title>",
        "<style>body{font-family:system-ui;margin:1.5rem;background:#f5f0e6;color:#222}"
        "h2{border-bottom:2px solid #b09b6b;padding-bottom:.2rem}"
        ".grid{display:flex;flex-wrap:wrap;gap:1rem}"
        ".cell{background:#fff;border:1px solid #cbb;padding:.5rem;max-width:340px}"
        ".cell img{max-width:320px;display:block;border:1px solid #ddd}"
        ".badge{font-weight:bold;padding:0 .4rem;border-radius:.3rem;color:#fff}"
        ".new{background:#2c6e49}.changed{background:#b3261e}.same{background:#888}"
        "figcaption{font-size:.8rem;margin-top:.25rem}</style>",
        f"<h1>Baseline-Review — {html.escape(run_dir.name)}</h1>",
        f"<p>Neu: <b>{counts['new']}</b> · Geändert: <b>{counts['changed']}</b>"
        f" · Unverändert: <b>{counts['unchanged']}</b>"
        f" · Nicht zuordenbar: {counts['unparsed']}</p>",
        "<p>Freigabe nach Review (Regelwerk §6, nur durch einen Menschen):<br>"
        "<code>python -m tools.robots.review_baselines --run "
        f"{html.escape(str(run_dir))} --promote --note '…'</code>"
        " — danach Baselines committen.</p>",
    ]
    for checkpoint in CHECKPOINTS:
        entries = rows.get(checkpoint)
        if not entries:
            continue
        parts.append(f"<h2>{checkpoint}</h2><div class='grid'>")
        for entry in sorted(entries, key=lambda e: (
                e["meta"]["browser"], e["meta"]["viewport"], e["meta"]["role"])):
            meta = entry["meta"]
            rel = entry["shot"].relative_to(run_dir)
            if entry["baseline"] is None:
                badge = "<span class='badge new'>NEU</span>"
            elif entry["pixels"] == 0:
                badge = "<span class='badge same'>unverändert</span>"
            else:
                pixels = ("Größe abweichend" if entry["pixels"] == -1
                          else f"{entry['pixels']} px")
                badge = f"<span class='badge changed'>GEÄNDERT ({pixels})</span>"
            caption = (f"{badge} {meta['role']} · {meta['browser']} · "
                       f"{meta['viewport']}")
            parts.append(
                f"<figure class='cell'><img loading='lazy' src='{rel}'>"
                f"<figcaption>{caption}</figcaption>")
            if entry["diff"] is not None:
                diff_rel = entry["diff"].relative_to(run_dir)
                parts.append(f"<img loading='lazy' src='{diff_rel}'>"
                             f"<figcaption>Diff-Maske</figcaption>")
            parts.append("</figure>")
        parts.append("</div>")

    out = run_dir / "baseline_review.html"
    out.write_text("\n".join(parts), encoding="utf-8")
    return out


def _promote(run_dir: Path, baseline_dir: Path, *, note: str, only: str,
             force: bool) -> int:
    baseline_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = baseline_dir / "baseline_manifest.json"
    manifest = (json.loads(manifest_path.read_text(encoding="utf-8"))
                if manifest_path.exists() else {})
    promoted = skipped = 0
    for shot in sorted((run_dir / "screenshots").glob("*.png")):
        if _parse(shot.name) is None or not fnmatch.fnmatch(shot.name, only):
            continue
        digest = hashlib.sha256(shot.read_bytes()).hexdigest()[:16]
        target = baseline_dir / shot.name
        if target.exists():
            existing = hashlib.sha256(target.read_bytes()).hexdigest()[:16]
            if existing == digest:
                continue
            if not force:
                print(f"  ÜBERSPRUNGEN (Baseline weicht ab, --force nötig): "
                      f"{shot.name}")
                skipped += 1
                continue
        shutil.copy2(shot, target)
        manifest[shot.name] = {
            "sha256_16": digest,
            "from_run": run_dir.name,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "note": note,
        }
        promoted += 1
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True),
        encoding="utf-8")
    print(f"review_baselines: {promoted} Baselines übernommen, "
          f"{skipped} übersprungen → {baseline_dir.relative_to(REPO)} "
          f"(jetzt committen)")
    return 0 if skipped == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tools.robots.review_baselines")
    parser.add_argument("--run", type=Path, required=True,
                        help="Lauf-Verzeichnis mit screenshots/")
    parser.add_argument("--baseline-dir", type=Path, default=BASELINE_DIR)
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--note", default="",
                        help="Pflicht bei --promote: warum diese Optik gewollt ist")
    parser.add_argument("--only", default="*",
                        help="fnmatch-Filter auf Dateinamen bei --promote")
    parser.add_argument("--force", action="store_true",
                        help="abweichende bestehende Baseline überschreiben")
    args = parser.parse_args(argv)

    if not (args.run / "screenshots").is_dir():
        print(f"Kein screenshots/-Verzeichnis in {args.run}", file=sys.stderr)
        return 2
    if args.promote:
        if not args.note.strip():
            print("--promote verlangt --note (Gate D: Baseline-Änderungen "
                  "sind begründet).", file=sys.stderr)
            return 2
        return _promote(args.run, args.baseline_dir, note=args.note,
                        only=args.only, force=args.force)
    out = _build_review(args.run, args.baseline_dir)
    print(f"review_baselines: Review-Seite geschrieben → {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
