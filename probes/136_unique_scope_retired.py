"""Q: does a `unique: true` text field's uniqueness span projects, does a deleted (retired) row keep
its value reserved, and what happens when a row is revived into a value another row now holds?

Probe 127 found a `unique: true` text field refuses a second create with the same value. sg-onset
keys rows on a client UUID and deletes and restores rows, so the reach of the check decides whether
a lookup by that key can miss. Probes only write into the sandbox project, so "another project" is
measured with the one other place a project-scoped row can sit: a row with no `project`. A second
writable project would settle it fully.

Steps, on the first enabled custom slot with a field `sg_zzprobe_136_key` created `unique: true`:

  1. A holds K in the sandbox. B with K and no project.
  2. A deleted. C created with K. C deleted, D created with K, then A revived while D holds K.
  3. A's value read after the revive; then E created with K.

Writes in the sandbox, behind `--write`. Rows `zzprobe_136_*` deleted on exit; the field retired.

    python probes/136_unique_scope_retired.py --write
"""
import json
import uuid

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 136 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
SLUG = f"custom_entity{CE[12:]}s"
FIELD = "sg_zzprobe_136_key"
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:700]
    except ValueError:
        return repr(r.text[:300])


field_made = False
with _lib.Created(c) as made:
    try:
        r = c.post(f"/schema/{CE}/fields", json={"data_type": "text", "properties": [
            {"property_name": "name", "value": "zzprobe 136 key"}, {"property_name": "unique", "value": True}]})
        out(f"POST /schema/<custom slot>/fields text unique -> {r.status_code} "
            + (r.json()["links"]["self"].rsplit("/", 1)[-1] if r.ok else errs(r)))
        field_made = r.status_code == 201
        K = str(uuid.uuid4())

        def create(label, project=P, value=K):
            body = {"code": f"zzprobe_136_{label}", FIELD: value}
            if project is not None:
                body["project"] = project
            r = c.post(f"/entity/{SLUG}", json=body)
            out(f"  create {label} {'in the sandbox' if project else 'with no project'} -> {r.status_code} {'' if r.ok else errs(r)}")
            return made.add(SLUG, r.json()["data"]["id"]) if r.status_code == 201 else None

        def holders():
            q = c.post(f"/entity/{SLUG}/_search", headers=ARR, json={
                "filters": [[FIELD, "is", K]], "fields": ["code"]}).json()["data"]
            return [x["attributes"]["code"] for x in q]

        def delete(rid, label):
            r = c.delete(f"/entity/{SLUG}/{rid}")
            out(f"  delete {label} -> {r.status_code}")
            made.rows.remove((SLUG, rid))

        out("\n===== 1. across projects")
        a = create("A")
        b = create("B", project=None)
        if b is None:
            r = c.post(f"/entity/{SLUG}", json={"code": "zzprobe_136_noproj"})
            out(f"  control, no project and no key -> {r.status_code} {'' if r.ok else errs(r)}")
            if r.status_code == 201:
                made.add(SLUG, r.json()["data"]["id"])
        out(f"  rows holding K: {holders()}")

        out("\n===== 2. a deleted row's value")
        if b:
            delete(b, "B")
        delete(a, "A")
        retired = c.get(f"/entity/{SLUG}", params={
            "filter[id]": a, "fields": FIELD, "options[return_only]": "retired"})
        out(f"  GET options[return_only]=retired for A -> {retired.status_code} "
            + (json.dumps([x['attributes'] for x in retired.json()['data']]) if retired.ok else errs(retired)))
        cc = create("C")
        out(f"  rows holding K: {holders()}")
        if cc:
            delete(cc, "C")
        d = create("D")

        out("\n===== 3. revive A while D holds K")
        r = c.post(f"/entity/{SLUG}/{a}", params={"revive": "true"})
        out(f"  POST /entity/<slot>/{{A}}?revive=true -> {r.status_code} {'' if r.ok else errs(r)}")
        if r.ok:
            made.add(SLUG, a)
            got = c.get(f"/entity/{SLUG}/{a}", params={"fields": FIELD}).json()["data"]["attributes"][FIELD]
            out(f"  A reads {FIELD} == K: {got == K} ({'null' if got is None else 'set'})")
        out(f"  rows holding K: {holders()}")
        if d:
            delete(d, "D")
        if r.ok:
            delete(a, "A")
        cc = c.post(f"/entity/{SLUG}/{cc}", params={"revive": "true"}) if cc else None
        out(f"  revive C with no live row holding K -> {cc.status_code if cc is not None else '-'}")
        if cc is not None and cc.ok:
            made.add(SLUG, int(cc.json()["data"]["id"]))
        e = create("E")
        out(f"  rows holding K: {holders()}")
    finally:
        _lib.emit("136_unique_scope_retired", "\n".join(rows), env)

if field_made:
    r = c.delete(f"/schema/{CE}/fields/{FIELD}")
    print(f"  retired /schema/<custom slot>/fields/{FIELD} -> {r.status_code}")
