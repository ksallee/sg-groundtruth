"""Q: what does a `password` field do over REST, and does a read ever return credential material?

Read-only, permanently. A `password` field holds the credential of a real account, so this probe never
sends a value to one under any flag: there is no sandbox account to lock out and no safe test value. The
write half of the card is recorded as "not attempted", with what the schema claims about `editable`.

No value is ever printed. `shape()` reports type, length and repetition, which is enough to tell a mask
from a hash from a cleartext string without putting either in the corpus or in a terminal buffer.

The schema sweep walks every entity type. That is the call probe 002 says never to loop, and it costs
~330ms a type here: acceptable once, for a census, not in a client.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []


def errs(r):
    """The whole errors[] object, source included. A sliced 400 loses the part worth having."""
    return json.dumps(r.json().get("errors"), indent=1)


def shape(v):
    """Describe a value without disclosing it."""
    if v is None:
        return "null"
    if not isinstance(v, str):
        return f"non-string {type(v).__name__}, withheld"
    if v == "":
        return "empty string"
    chars = set(v)
    if len(chars) == 1:
        return f"str len={len(v)}, single repeated char {v[0]!r} (mask)"
    cls = [n for n, f in (("alpha", str.isalpha), ("digit", str.isdigit))
           if any(f(ch) for ch in v)]
    if len(chars) < len(v) and all(ch.isalnum() for ch in v):
        cls.append("alnum only")
    return (f"str len={len(v)}, {len(chars)} distinct chars, {'+'.join(cls)}"
            f" -- VALUE WITHHELD, credential material")


def slug_for(t):
    """/entity/<slug>. No mapping is published, so try the plural forms and keep the one that answers."""
    cands = [t.lower() + "s", t.lower()[:-1] + "ies" if t.lower().endswith("y") else t.lower(), t]
    for s in dict.fromkeys(cands):
        r = c.get(f"/entity/{s}", params={"page[size]": 1, "fields": "id"})
        if r.ok:
            return s
    return None


# ------------------------------------------------------------------ census
t0 = time.time()
types = sorted(c.get("/schema").json()["data"])
found = {}
for t in types:
    r = c.get(f"/schema/{t}/fields")
    if r.ok:
        d = r.json()["data"]
        p = {f: v for f, v in d.items() if v["data_type"]["value"] == "password"}
        if p:
            found[t] = (p, d)
rows.append(f"=== census: password across all {len(types)} entity types ({time.time() - t0:.0f}s)")
rows.append(f"  {sum(len(p) for p, _ in found.values())} fields on {len(found)} types")
for t, (p, d) in sorted(found.items()):
    for f, v in sorted(p.items()):
        _lib.note_names(v["name"]["value"])
        rows.append(f"  {t}.{f}  name={v['name']['value']!r}  editable={v['editable']['value']}  "
                    f"of {len(d)} fields on the type")

# ------------------------------------------------------------- schema shape
rows.append("\n=== schema: GET /schema/<Type>/fields/<field>, every key, in full")
for t, (p, _) in sorted(found.items()):
    for f in sorted(p):
        r = c.get(f"/schema/{t}/fields/{f}")
        rows.append(f"  --- {t}.{f} -> {r.status_code}")
        for k, v in r.json()["data"].items():
            rows.append(f"      {k:<24} {json.dumps(v)}")

# --------------------------------------------------------------------- read
rows.append("\n=== read: is the key returned, and what shape (values never printed)")
targets = {}
for t, (p, d) in sorted(found.items()):
    s = slug_for(t)
    rows.append(f"  --- {t} -> /entity/{s}")
    if not s:
        rows.append("      no listing endpoint answered; skipped")
        continue
    fields = sorted(p) + ["id"] + (["code"] if "code" in d else [])
    params = {"page[size]": 3, "fields": ",".join(fields + ["sg_not_a_real_field"])}
    if "project" in d:
        params["filter[project.Project.id]"] = PROJECT
    r = c.get(f"/entity/{s}", params=params)
    rows.append(f"      GET /entity/{s}?fields={params['fields']} -> {r.status_code}")
    if not r.ok:
        rows.append(f"      {errs(r)}")
        continue
    data = r.json()["data"]
    rows.append(f"      {len(data)} rows"
                f"{' (project-filtered)' if 'project' in d else ' (site-wide, no project field)'}")
    for row in data:
        a = row["attributes"]
        targets.setdefault(t, (s, row["id"]))
        rows.append(f"      row {row['id']}: keys={sorted(a)}  relationships={sorted(row['relationships'])}")
        for f in sorted(p):
            rows.append(f"        {f}: present={f in a}  {shape(a.get(f))}")
        rows.append(f"        sg_not_a_real_field present={'sg_not_a_real_field' in a} (probe 004)")

rows.append("\n=== read: is the mask constant, or does its length track the credential")
for t, (s, _) in sorted(targets.items()):
    f = sorted(found[t][0])[0]
    d = c.get(f"/entity/{s}", params={"fields": f, "page[size]": 500}).json()["data"]
    seen = {row["attributes"].get(f) for row in d}
    rows.append(f"  {t}: {len(d)} rows, {len(seen)} distinct values, "
                f"lengths {sorted({len(v) if isinstance(v, str) else -1 for v in seen})}, "
                f"nulls {sum(1 for v in seen if v is None)}")
    rows.append(f"  {t}: every row identical: {len(seen) == 1}  "
                f"{shape(next(iter(seen)))}")

rows.append("\n=== read: single row by id, and fields=* , same withholding")
for t, (s, rid) in sorted(targets.items()):
    p = sorted(found[t][0])
    for label, params in (("named", {"fields": ",".join(p)}), ("star", {"fields": "*"})):
        r = c.get(f"/entity/{s}/{rid}", params=params)
        a = r.json()["data"]["attributes"] if r.ok else {}
        rows.append(f"  {t}/{rid} fields={label:<6} -> {r.status_code}  "
                    + "  ".join(f"{f}: present={f in a} {shape(a.get(f))}" for f in p))

# ------------------------------------------------------- operators, filter
rows.append("\n=== filter: does the API enumerate relations for this type (probe 017)")
for t, (s, _) in sorted(targets.items()):
    for f in sorted(found[t][0]):
        r = c.post(f"/entity/{s}/_search", headers=ARR,
                   json={"filters": [[f, "definitely_not_an_operator", None]],
                         "fields": ["id"], "page": {"size": 1}})
        rows.append(f"  --- {t}.{f} bogus operator -> {r.status_code}")
        rows.append("  " + errs(r))

rows.append("\n=== filter: can the field be filtered at all")
for t, (s, _) in sorted(targets.items()):
    for f in sorted(found[t][0]):
        for label, filt in (("is null", [f, "is", None]),
                            ("is_not null", [f, "is_not", None]),
                            ("is <string>", [f, "is", "zzprobe_not_a_password"]),
                            ("contains <str>", [f, "contains", "zzprobe"])):
            r = c.post(f"/entity/{s}/_search", headers=ARR,
                       json={"filters": [filt], "fields": ["id"], "page": {"size": 1}})
            out = f"200, {len(r.json()['data'])} rows" if r.ok else \
                f"{r.status_code} {errs(r)}".replace("\n", " ")
            rows.append(f"  {t}.{f} {label:<16} -> {out}")
        r = c.get(f"/entity/{s}", params={f"filter[{f}]": "zzprobe_not_a_password", "fields": "id"})
        out = f"200, {len(r.json()['data'])} rows" if r.ok else \
            f"{r.status_code} {errs(r)}".replace("\n", " ")
        rows.append(f"  {t}.{f} GET flat filter[] -> {out}")

# --------------------------------------------------------------------- sort
rows.append("\n=== sort: accepted, ignored, or refused")
for t, (s, _) in sorted(targets.items()):
    for f in sorted(found[t][0]):
        for label, sort in ((f"_search {f}", f), (f"_search -{f}", f"-{f}")):
            r = c.post(f"/entity/{s}/_search", headers=ARR,
                       json={"filters": [], "fields": ["id"], "sort": sort, "page": {"size": 5}})
            out = f"200, ids {[x['id'] for x in r.json()['data']]}" if r.ok else \
                f"{r.status_code} {errs(r)}".replace("\n", " ")
            rows.append(f"  {t} {label:<22} -> {out}")
        r = c.get(f"/entity/{s}", params={"sort": f, "fields": "id", "page[size]": 5})
        out = f"200, ids {[x['id'] for x in r.json()['data']]}" if r.ok else \
            f"{r.status_code} {errs(r)}".replace("\n", " ")
        rows.append(f"  {t} GET sort={f:<16} -> {out}")
        for ctl in ("id", "-id"):
            r = c.get(f"/entity/{s}", params={"sort": ctl, "fields": "id", "page[size]": 5})
            rows.append(f"  {t} GET sort={ctl} (control) -> "
                        f"{'200, ids ' + str([x['id'] for x in r.json()['data']]) if r.ok else r.status_code}")

# ------------------------------------------------------- dotted path bypass
rows.append("\n=== dotted path: can the mask be read or filtered through a link (probe 016, 017)")
DOT = "created_by.HumanUser.password_proxy"
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "page[size]": 2,
                                      "fields": f"code,{DOT}"})
rows.append(f"  GET /entity/versions?fields=code,{DOT} -> {r.status_code}")
for row in (r.json()["data"] if r.ok else []):
    _lib.note_from(row)
    rows.append(f"    attributes keys={sorted(row['attributes'])}  "
                f"{DOT} present={DOT in row['attributes']} "
                f"{shape(row['attributes'].get(DOT))}")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [[DOT, "is", "zzprobe_not_a_password"]], "fields": ["id"],
                 "page": {"size": 1}})
rows.append(f"  _search filter [{DOT!r}, 'is', <string>] -> {r.status_code}")
rows.append("  " + (f"200, {len(r.json()['data'])} rows" if r.ok else errs(r)))

# -------------------------------------------------------------------- write
rows.append("\n=== write: not attempted, at any flag")
rows.append("  A password field holds the credential of a real account on a live site. Writing one "
            "locks out the person or script that owns it, and there is no sandbox account to spend. "
            "No POST, PUT or clear is sent by this probe, with or without --write.")
for t, (p, _) in sorted(found.items()):
    for f, v in sorted(p.items()):
        rows.append(f"  schema claim: {t}.{f} editable={v['editable']['value']} "
                    f"(editable of editable={v['editable'].get('editable')})")

actual = "\n".join(rows)
_lib.emit("field_types/password", actual, env)
