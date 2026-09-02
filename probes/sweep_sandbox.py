"""List, and with --write delete, rows probes left in the sandbox project.

A probe should delete what it creates (`_lib.Created`). This is the backstop for the ones that did not,
and the check that the sandbox is a clean measuring ground before a run.
"""
import sys

import _lib

PREFIXES = ("zzprobe", "sbx_")
TYPES = (("Version", "versions", "code"), ("Shot", "shots", "code"),
         ("Task", "tasks", "content"), ("Sequence", "sequences", "code"),
         ("Asset", "assets", "code"), ("Playlist", "playlists", "code"))

env = _lib.load_env()
c = _lib.client()
sandbox = _lib.sandbox_id(c, env)
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}

found = []
for name, slug, field in TYPES:
    r = c.post(f"/entity/{slug}/_search", headers=ARR,
               json={"filters": [["project.Project.id", "is", sandbox]],
                     "fields": [field], "page": {"size": 500}})
    if not r.ok:
        print(f"{name}: {r.status_code} {r.text[:120]}")
        continue
    for d in r.json().get("data", []):
        label = str(d["attributes"].get(field) or "")
        if label.lower().startswith(PREFIXES):
            found.append((slug, d["id"], f"{name} {label}"))

if not found:
    print("sandbox clean — no probe rows")
    sys.exit(0)

for slug, i, label in found:
    print(f"  {label}  /entity/{slug}/{i}")
print(f"{len(found)} probe rows in the sandbox")

if not _lib.writes_allowed():
    print("re-run with --write to delete them")
    sys.exit(0)

for slug, i, label in found:
    r = c.delete(f"/entity/{slug}/{i}")
    print(f"  {r.status_code}  {label}")
