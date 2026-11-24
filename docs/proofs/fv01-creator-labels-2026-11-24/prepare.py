"""Build a committed source overlay on the checked running image; never replace inherited artwork.

Use the existing release_committed_vtt.py schema/activate commands afterwards.
The verification scope is shipped source plus changed JSON, not unchanged image assets.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


REPO = Path(__file__).resolve().parents[3]
BASE_SOURCE = "207c8e9fc8a465168c23d5528836ae3c95f3a619"
BASE_IMAGE = "sha256:384ab8657919735f893eaa2dad1e249c5ead23ad03108494778103ec1851146c"


def output(args, **kwargs):
    return subprocess.check_output(args, cwd=REPO, **kwargs)


def inspect(name):
    return json.loads(output(["docker", "inspect", name]))[0]


def save(directory, record):
    (directory / "release.json").write_text(json.dumps(record, indent=2) + "\n")


def source_hashes(extra_paths, image=None):
    code = '''import hashlib,json,sys
from pathlib import Path
r=Path('/app'); extra=json.load(sys.stdin)
paths={p for p in (r/'vtt').rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix in {'.py','.js','.css','.html'}}
paths.update(r/p for p in ['app.py','requirements.txt',*extra] if (r/p).is_file())
print(json.dumps({str(p.relative_to(r)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}))
'''
    command = (["docker", "run", "--rm", "-i", "--network", "none", "--entrypoint", "python", image]
               if image else ["docker", "exec", "-i", "roll-drauf-vtt-app-1", "python"])
    return json.loads(output(command + ["-c", code], input=json.dumps(extra_paths).encode()))


def main():
    assert not output(["git", "status", "--porcelain", "--", "vtt", "app.py", "requirements.txt"]).strip(), "Commit app changes first"
    app = inspect("roll-drauf-vtt-app-1")
    assert app["Image"] == BASE_IMAGE, "Running image changed; reconcile before release"
    assert app["Config"]["Labels"]["org.opencontainers.image.revision"] == BASE_SOURCE
    commit = output(["git", "rev-parse", "HEAD"], text=True).strip()
    changed = output(["git", "diff", "--name-only", BASE_SOURCE, commit, "--", "vtt", "app.py", "requirements.txt"], text=True).splitlines()
    assert changed and all(Path(REPO, path).is_file() for path in changed), "Deletions need a separate release design"
    baseline = source_hashes(changed)
    assert all(hashlib.sha256(output(["git", "show", f"{BASE_SOURCE}:{path}"])).hexdigest() == digest
               for path, digest in baseline.items()), "Running source drifted from its recorded commit"
    directory = Path("/srv/migration/2026-11-24/fv01-creator-labels") / commit[:9]
    directory.mkdir(parents=True, exist_ok=True)
    directory.chmod(0o700)
    assert not (directory / "release.json").exists(), "Resume from the existing release record"
    prior = "roll-drauf-vtt-app:fv01-creator-labels-rollback-384ab8657919"
    subprocess.run(["docker", "tag", BASE_IMAGE, prior], check=True)
    image = f"roll-drauf-vtt-app:fv01-creator-labels-20261124-{commit[:9]}"
    manifest = {}
    for path in changed:
        source = REPO / path
        target = directory / "build/files" / path
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        manifest[path] = hashlib.sha256(source.read_bytes()).hexdigest()
    (directory / "build/Dockerfile").write_text(
        f'FROM {prior}\nCOPY files/ /app/\nLABEL org.opencontainers.image.revision="{commit}"\n'
        f'LABEL de.roll-drauf.feedback-program.base-image="{BASE_IMAGE}"\n')
    compose_files = app["Config"]["Labels"]["com.docker.compose.project.config_files"].split(",")
    assert len(compose_files) == 2
    shutil.copy2(compose_files[1], directory / "previous.override.yml")
    before = {}
    for container in output(["docker", "ps", "-q"], text=True).splitlines():
        item = inspect(container)
        if item["Name"].startswith("/roll-drauf-vtt-") and item["Name"] != "/roll-drauf-vtt-app-1":
            before[item["Name"]] = {"id": item["Id"], "started_at": item["State"]["StartedAt"]}
    record = {"commit": commit, "base_source": BASE_SOURCE, "running_revision_label": BASE_SOURCE,
              "image": image, "base_image_id": BASE_IMAGE, "prior_image": prior, "overlay_manifest": manifest,
              "compose_project": app["Config"]["Labels"]["com.docker.compose.project"],
              "compose_files": compose_files, "other_services_before": before,
              "prepared_at": datetime.now(timezone.utc).isoformat(),
              "verification_scope": "all shipped Python/JS/CSS/HTML, app.py, requirements.txt and changed JSON; unchanged artwork inherited from the checked image",
              "baseline_source_verification": {"checked": len(baseline), "mismatches": []}}
    save(directory, record)
    subprocess.run(["docker", "build", "--network", "none", "-t", image, str(directory / "build")], check=True)
    actual = source_hashes(changed, image)
    expected = {path: hashlib.sha256((REPO / path).read_bytes()).hexdigest() for path in actual}
    wrong = [path for path in actual if actual[path] != expected[path]]
    assert not wrong and all(actual.get(path) == digest for path, digest in manifest.items())
    with (directory / "factory-check.log").open("w") as log:
        subprocess.run(["docker", "run", "--rm", "--network", "none", "--entrypoint", "python", image,
                        "-c", 'import warnings;warnings.filterwarnings("ignore");from vtt import create_app;create_app("testing");print("Factory OK")'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    record["image_id"] = inspect(image)["Id"]
    record["built_source_verification"] = {"checked": len(actual), "mismatches": wrong}
    save(directory, record)
    print(json.dumps({"release_directory": str(directory), "image": image, "verified_source_files": len(actual)}))


if __name__ == "__main__":
    main()
