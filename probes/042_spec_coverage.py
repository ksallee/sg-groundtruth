"""Q: does the site publish its own endpoint list, and which of them does the corpus cover?

`GET /spec.{format}` returns an OpenAPI v3 document for the deployment answering the call. That makes
the endpoint queue measurable instead of guessed: every operation the site advertises, minus every
`endpoint:` a card in `corpus/endpoints/` is named by.

The spec is the authority for a site, not the published documentation. The two disagree, and this
probe prints where. Read-only.
"""
import json
import re
from collections import defaultdict

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

# The corpus spells a path segment for what varies. The spec names the parameter.
SUBST = [
    (r"\{entity\}", "<type>"),
    (r"\{record_id\}", "<id>"),
    (r"\{field(?:_name)?\}", "<field>"),
    (r"\{([a-z_]+)\}", r"<\1>"),
]


def canon(path):
    for pat, rep in SUBST:
        path = re.sub(pat, rep, path)
    return path


r = c.get("/spec.json")
rows.append(f"GET /spec.json -> {r.status_code} {r.headers.get('Content-Type')} {len(r.content)} bytes")
y = c.get("/spec.yaml")
rows.append(f"GET /spec.yaml -> {y.status_code} {y.headers.get('Content-Type')} {len(y.content)} bytes")
bad = c.get("/spec.xml")
rows.append(f"GET /spec.xml  -> {bad.status_code}  {bad.text[:120]}")
rows.append(f"GET /spec      -> {c.get('/spec').status_code}  (the suffix is not optional)")

spec = r.json()
info = spec.get("info", {})
rows.append(f"\nopenapi {spec.get('openapi')}  title {info.get('title')!r}  version {info.get('version')!r}")
rows.append(f"servers {json.dumps(spec.get('servers'))[:80]}")

ops = sorted({(m.upper(), canon(p)) for p, v in spec["paths"].items()
              for m in v if m.lower() in ("get", "post", "put", "patch", "delete")},
             key=lambda x: (x[1], x[0]))
rows.append(f"{len(spec['paths'])} paths, {len(ops)} operations")

cards = {}
for f in sorted((_lib.ROOT / "corpus" / "endpoints").glob("*.md")):
    m = re.search(r"^endpoint:\s*(\S.*?)\s*$", f.read_text(), re.M)
    if m:
        cards[m.group(1)] = f.stem

# A card writes a schema name as `<Type>`, because that is what the URL segment holds there.
def covered(meth, path):
    for key in (f"{meth} {path}", f"{meth} {path}".replace("/schema/<type>", "/schema/<Type>")):
        if key in cards:
            return True
    return False

missing = [(m, p) for m, p in ops if not covered(m, p)]
rows.append(f"\ncovered {len(ops) - len(missing)} of {len(ops)}; {len(missing)} with no card\n")

family = defaultdict(list)
for m, p in missing:
    seg = p.strip("/").split("/")
    key = seg[0] if seg[0] != "entity" else ("entity/" + (seg[-1] if seg[-1].startswith("_") else seg[-1]))
    family[key].append(f"{m} {p}")
for k in sorted(family):
    rows.append(f"  {k}")
    for line in sorted(family[k]):
        rows.append(f"    {line}")

# A card the spec does not list is not automatically wrong: two of them are the presigned storage
# steps, which are not routes on this API at all.
extra = sorted(k for k in cards if not any(covered(m, p) and f"{m} {p}".startswith(k.split()[0]) for m, p in ops)
               and k not in {f"{m} {p}" for m, p in ops}
               and k.replace("/schema/<Type>", "/schema/<type>") not in {f"{m} {p}" for m, p in ops})
rows.append(f"\ncards with no operation in the spec: {extra}")

_lib.emit("042_spec_coverage", "\n".join(rows), env)
