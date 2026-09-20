"""Stamp a preview build in a disposable CI checkout; reject ambiguous versions."""

import argparse
import json
import re
import subprocess
from pathlib import Path

from packaging.version import Version

parser = argparse.ArgumentParser()
parser.add_argument("version")
args = parser.parse_args()
version = args.version
if not re.fullmatch(
    r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)-(alpha|beta|rc)\.(0|[1-9][0-9]*)", version
):
    parser.error("Use a preview SemVer such as 0.17.3-alpha.1 (no leading v)")
python_version = str(Version(version))
root = Path(__file__).resolve().parents[2]
for name in ("desktop/package.json", "desktop/src-tauri/tauri.conf.json"):
    path = root / name
    data = json.loads(path.read_text())
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
path = root / "desktop/src-tauri/Cargo.toml"
text = path.read_text()
text, count = re.subn(r'^version = "[^"]+"', f'version = "{version}"', text, count=1, flags=re.M)
assert count == 1
path.write_text(text, encoding="utf-8")
(root / "static/version.json").write_text(json.dumps({"version": version}) + "\n")
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
(root / "dist").mkdir(exist_ok=True)
(root / "dist/build-metadata.json").write_text(
    json.dumps(
        {
            "repository": "kittipatkampa/stemdeck",
            "commit": sha,
            "version": version,
            "pythonPackageVersion": python_version,
            "platform": "windows-x64",
            "variant": "cpu",
            "desktopAcceptance": "pending",
            "signed": False,
        },
        indent=2,
    )
    + "\n"
)
print(f"Preview {version}, Python package {python_version}, commit {sha}")
