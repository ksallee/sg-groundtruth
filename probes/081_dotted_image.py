"""Q: does a dotted `entity.Shot.image` return a presigned URL the way `image` does on the Shot itself?

A page of Tasks or Versions shows its parent's thumbnail through a dotted column. If the dotted read
returns the same URL, the runner needs no second call per row. Sample project, read only.
"""
import collections
import json
import re

import _lib
import _pages as P

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
F = [["project", "is", {"type": "Project", "id": PROJECT}]]
rows = []


def kind(v):
    if v is None:
        return "null"
    if isinstance(v, str) and v.startswith("http"):
        host = re.sub(r"^https://([^/]+)/.*$", r"\1", v)
        signed = "signed" if re.search(r"(Signature|X-Amz-Signature|Expires)=", v) else "unsigned"
        return f"url {signed} {'s3' if 'amazonaws' in host else 'site' if env.get('FPT_API_SITE_URL', '').split('//')[-1] in host else 'other'}"
    return f"{type(v).__name__} {str(v)[:40]}"


shots = P.search(c, "shots", F + [["image", "is_not", None]], ["image"], size=100)
all_shots = {s["id"]: s["attributes"]["image"] for s in P.search(c, "shots", F, ["image"], size=500)}
by_id = {i: v for i, v in all_shots.items() if v}
rows.append(f"=== {len(all_shots)} Shots in the project; filter image is_not null matches {len(shots)}; "
            f"image read on those: {dict(collections.Counter(kind(v) for v in (s['attributes']['image'] for s in shots)))}")
r = c.post("/entity/shots/_summarize", headers=P.ARR,
           json={"filters": F + [["image", "is", None]], "summary_fields": [{"field": "id", "type": "count"}]})
rows.append(f"  filter image is null matches {r.json()['data']['summaries']['id']}")

for slug, path in (("tasks", "entity.Shot.image"), ("versions", "entity.Shot.image")):
    got = P.search(c, slug, F + [["entity", "type_is", "Shot"]], ["entity", path], size=500)
    linked = [x for x in got if (P.rel(x, "entity") or {}).get("id") in by_id]
    rows.append(f"\n=== {slug}?fields={path}: {len(got)} rows on a Shot, {len(linked)} on a Shot whose image reads a URL")
    if not got:
        continue
    where = collections.Counter("attributes" if path in x["attributes"] else
                                "relationships" if path in x["relationships"] else "absent" for x in got)
    rows.append(f"  returned under: {dict(where)}")
    kinds = collections.Counter(kind(x["attributes"].get(path)) for x in linked)
    rows.append(f"  value kinds where the Shot has an image: {dict(kinds)}")
    same = collections.Counter()
    for x in linked:
        v, own = x["attributes"].get(path), by_id[P.rel(x, "entity")["id"]]
        strip = lambda u: (u or "").split("?")[0]
        same["identical string" if v == own else "same object, different signature" if strip(v) == strip(own)
             else "different"] += 1
    rows.append(f"  against the Shot's own image: {dict(same)}")
    miss = [x for x in got if (P.rel(x, "entity") or {}).get("id") not in by_id]
    rows.append(f"  where the Shot's own image reads null ({len(miss)} rows): "
                f"{dict(collections.Counter(kind(x['attributes'].get(path)) for x in miss))}")
    if linked:
        u = next((x["attributes"][path] for x in linked if x["attributes"].get(path)), "")
        own = by_id[P.rel(next(x for x in linked if x["attributes"].get(path)), "entity")["id"]] if u else ""
        rows.append(f"  URL path equal to the Shot's own: {u.split('?')[0] == own.split('?')[0]}; "
                    f"query keys {sorted(k.split('=')[0] for k in u.split('?')[-1].split('&'))[:10]}")

rows.append("\n=== filter and sort on the dotted image")
for label, filt in (("is_not null", [["entity.Shot.image", "is_not", None]]),
                    ("is null", [["entity.Shot.image", "is", None]])):
    r = c.post("/entity/tasks/_summarize", headers=P.ARR,
               json={"filters": F + [["entity", "type_is", "Shot"]] + filt,
                     "summary_fields": [{"field": "id", "type": "count"}]})
    rows.append(f"  tasks, entity.Shot.image {label} -> {r.status_code} "
                f"{r.json()['data']['summaries'] if r.ok else json.dumps(r.json()['errors'][0])}")

rows.append("\n=== one row by id, and the image field's own sub-resource")
if by_id:
    sid = next(iter(by_id))
    t = P.search(c, "tasks", F + [["entity", "is", {"type": "Shot", "id": sid}]], ["id"], size=1)
    if t:
        r = c.get(f"/entity/tasks/{t[0]['id']}", params={"fields": "entity.Shot.image"})
        rows.append(f"  GET /entity/tasks/<id>?fields=entity.Shot.image -> {r.status_code} "
                    f"{kind(r.json()['data']['attributes'].get('entity.Shot.image'))}")
    r = c.get(f"/entity/shots/{sid}/image", allow_redirects=False)
    rows.append(f"  GET /entity/shots/<id>/image -> {r.status_code} {r.headers.get('Content-Type')} "
                f"{kind(r.headers.get('Location')) if r.is_redirect else r.text[:120]}")

_lib.emit("081_dotted_image", "\n".join(rows), env)
