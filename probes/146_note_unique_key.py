"""Q: can a `unique: true` text field be created on Note, does it refuse a duplicate, and does `Note.meta`
set on create and filtered with `contains` work as the lookup key instead?

sg-onset writes one Note per Shot at sync and must find it again by a client UUID to update it in
place. Probe 127 measured a unique text field on Version, probe 136 on a custom entity; Note is a
stock type with its own create rules (probe 069), so it is measured again here. `field_types/jsonb`
found `Note.meta` create-only and filterable with `contains`; this runs it as the lookup the app
would make, under the person's identity, next to the unique field.

Steps, as the script and as the person (`sudo_as_login`, probe 027), in the sandbox:

1. `POST /schema/Note/fields` text, `unique: true`, named `zzprobe 146 key`
2. Note A with key K; Note B with K, with K uppercased, with K padded; the same as the person
3. `PUT` Note B's key to K while A holds it
4. Note C with `meta: {"onset_uuid": K2, "shot": ...}`; `contains` lookups by K2, by K2 uppercased,
   by a key C does not hold, and the same under the person
5. With `--second-project <name or id>`: Note D with K in that project. Skipped otherwise, since
   probes write only into the sandbox (probe 136 stopped here for the same reason)

Writes behind `--write`: the Notes, deleted on exit, and the field, retired on exit (its name stays
taken until the Trash page is emptied, see `docs/quirks.md`).

    python probes/146_note_unique_key.py --write [--second-project <name or id>]
"""
import sys
import uuid

import _lib
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 146 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
LOGIN = (env.get("FPT_USER_LOGIN") or "").strip()
if not LOGIN:
    raise SystemExit("set FPT_USER_LOGIN in .env.local: the person this probe writes as")
person = FPT.from_env(env, sudo_as_login=LOGIN)
SECOND = sys.argv[sys.argv.index("--second-project") + 1] if "--second-project" in sys.argv else None
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def said(r):
    if r.ok:
        return str(r.status_code)
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} code {e.get('code')} {e.get('title')!r}"
    except (ValueError, KeyError, IndexError):
        return f"{r.status_code} {r.text[:300]}"


def find(who, filters):
    r = who.post("/entity/notes/_search", headers=ARR, json={
        "filters": [["project", "is", P]] + filters, "fields": ["id"], "page": {"size": 20}})
    return [x["id"] for x in r.json()["data"]] if r.ok else said(r)


field = None
try:
    with _lib.Created(c) as made:
        r = c.post("/schema/Note/fields", json={"data_type": "text", "properties": [
            {"property_name": "name", "value": "zzprobe 146 key"}, {"property_name": "unique", "value": True}]})
        out(f"POST /schema/Note/fields text unique -> {said(r)}")
        if r.ok:
            field = r.json()["links"]["self"].rsplit("/", 1)[-1]
            u = c.get(f"/schema/Note/fields/{field}").json()["data"]
            out(f"  {field}: unique {u.get('unique')}")

            K = str(uuid.uuid4())

            def note(who, label, **extra):
                r = who.post("/entity/notes", json={"project": P, "subject": f"zzprobe_146 {label}", **extra})
                if r.status_code == 201:
                    made.add("notes", r.json()["data"]["id"])
                out(f"  {label} -> {said(r)}")
                return r.json()["data"]["id"] if r.status_code == 201 else None

            out("\n===== the unique field")
            a = note(c, "A, script, K", **{field: K})
            note(c, "B, script, K", **{field: K})
            note(c, "B, script, K uppercased", **{field: K.upper()})
            note(c, "B, script, ' ' + K", **{field: " " + K})
            note(person, "B, person, K", **{field: K})
            b = note(person, "B, person, a new key", **{field: str(uuid.uuid4())})
            if b:
                r = person.put(f"/entity/notes/{b}", json={field: K})
                out(f"  PUT B's key to K while A holds it, as the person -> {said(r)}")
            out(f"  lookup [{field!r}, 'is', K] as the person -> {find(person, [[field, 'is', K]])} (A is {a})")
            out(f"  lookup with K uppercased -> {find(person, [[field, 'is', K.upper()]])}")

            if SECOND:
                sp = _lib.resolve_project(c, SECOND)
                r = c.post("/entity/notes", json={"project": {"type": "Project", "id": sp},
                                                  "subject": "zzprobe_146 D, second project", field: K})
                if r.status_code == 201:
                    made.add("notes", r.json()["data"]["id"])
                out(f"  D, script, K, in a second project -> {said(r)}")
            else:
                out("  D in a second project: not run, pass --second-project <name or id>")

        out("\n===== Note.meta as the key")
        K2 = str(uuid.uuid4())
        meta = {"onset_uuid": K2, "kind": "onset_sync"}
        r = person.post("/entity/notes", json={"project": P, "subject": "zzprobe_146 C, meta", "meta": meta})
        cid = made.add("notes", r.json()["data"]["id"]) if r.status_code == 201 else None
        out(f"  C, person, meta {{onset_uuid, kind}} -> {said(r)}")
        for who, w in ((person, "person"), (c, "script")):
            out(f"  as the {w}: contains {{onset_uuid: K2}} -> {find(who, [['meta', 'contains', {'onset_uuid': K2}]])} (C is {cid})")
        out(f"  contains {{onset_uuid: K2 uppercased}} -> {find(person, [['meta', 'contains', {'onset_uuid': K2.upper()}]])}")
        out(f"  contains {{onset_uuid: K2, kind: other}} -> {find(person, [['meta', 'contains', {'onset_uuid': K2, 'kind': 'other'}]])}")
        out(f"  is {{onset_uuid: K2}} (not the whole value) -> {find(person, [['meta', 'is', {'onset_uuid': K2}]])}")
        r = person.post("/entity/notes", json={"project": P, "subject": "zzprobe_146 C2, same meta", "meta": meta})
        if r.status_code == 201:
            made.add("notes", r.json()["data"]["id"])
        out(f"  C2 with the same meta -> {said(r)}; contains K2 now -> {len(find(person, [['meta', 'contains', {'onset_uuid': K2}]]))} rows")
        if cid:
            r = person.put(f"/entity/notes/{cid}", json={"content": "zzprobe_146 updated"})
            out(f"  PUT C content, as the person -> {said(r)}; meta still finds it -> "
                f"{cid in find(person, [['meta', 'contains', {'onset_uuid': K2}]])}")
        _lib.emit("146_note_unique_key", "\n".join(rows), env)
finally:
    if field:
        r = c.delete(f"/schema/Note/fields/{field}")
        print(f"  retired /schema/Note/fields/{field} -> {r.status_code}")
