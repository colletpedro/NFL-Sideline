"""Read-only proof: protected trees and public output are unchanged by the demo."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[3]
BASE = "f174af8d3bdca4f72f7b97d9eebb1cbb3889ecf0"
PROTECTED = [
    "web-ui/src", "web-ui/public", "web-ui/local-editorial", "web-ui/build",
    "web-ui/scripts", "web-ui/index.html", "web-ui/vite.config.ts",
    "web-ui/vite.editorial.config.ts", "web-ui/vercel.json", "web-ui/package-lock.json",
    "core-api", "etl-pipeline", "supabase", ".github", "Spec.md",
    "docs/static-snapshot-contract.md",
]
changed = subprocess.check_output(
    ["git", "diff", "--name-only", BASE, "--", *PROTECTED], cwd=ROOT, text=True,
).splitlines()
assert not changed, f"Protected paths changed: {changed}"
untracked = subprocess.check_output(
    ["git", "ls-files", "--others", "--exclude-standard", "--", *PROTECTED], cwd=ROOT, text=True,
).splitlines()
assert not untracked, f"Untracked files added to protected paths: {untracked}"
assets = ROOT / "web-ui/dist/assets"
assert assets.is_dir(), "Run the public build first"
hashes = {}
for file in assets.iterdir():
    if file.suffix in (".js", ".css"):
        wire = file.read_text()
        for marker in ("broadcast-experience", "dallas-new-england", "O passe abre o caminho", "Archivo-Variable", "RobotoCondensed-Variable"):
            assert marker not in wire, f"Experimental marker in public build: {marker}"
        hashes[file.suffix] = hashlib.sha256(file.read_bytes()).hexdigest()
assert hashes == {
    ".js": "73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5",
    ".css": "2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d",
}, "Public JS/CSS differ from the approved pilot base"
print(json.dumps({"base": BASE, "protectedChanges": changed, "protectedUntracked": untracked, "publicHashes": hashes}, indent=2))
