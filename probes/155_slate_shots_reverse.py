"""Q: a custom multi_entity field on Slate with `valid_types: ["Shot"]`: what reverse field does the
server add on Shot, and does a link written from either end read back from the other?

sg-onset links a Slate to the Shots it covers. Probe 142 measured the reverse field of a multi_entity
field between two custom slots as `<source slug>_<field>_<source slug>s`; Slate is a stock type with
a display name of its own, so the rule is checked here. The field is named `sg_zzprobe_155_shots`
(the litter prefix, `docs/quirks.md`) so that `sg_shots` stays free for the app.

Steps: diff Shot's schema around `POST /schema/Slate/fields`; then a Slate linked to Shot S1 on
create, S2 added in a `_batch` update with the mode in the body (probe 154), and S3 linked from the
Shot side through the reverse field; every link read from both ends.

Writes behind `--write`: one Slate and three Shots in the sandbox, deleted on exit; the field
retired on exit, which retires the reverse field with it (probe 142). Both names stay taken until
the Trash page is emptied.

    python probes/155_slate_shots_reverse.py --write
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 155 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
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


def linked(slug, rid, field):
    d = c.get(f"/entity/{slug}/{rid}", params={"fields": field}).json()["data"]["relationships"].get(field, {}).get("data")
    return [NAME.get((x["type"], x["id"]), x["id"]) for x in d or []]


before = set(c.get("/schema/Shot/fields").json()["data"])
field, reverse = None, None
try:
    r = c.post("/schema/Slate/fields", json={"data_type": "multi_entity", "properties": [
        {"property_name": "name", "value": "zzprobe 155 shots"},
        {"property_name": "valid_types", "value": ["Shot"]}]})
    out(f"POST /schema/Slate/fields multi_entity, valid_types [Shot] -> {said(r)}")
    if r.ok:
        field = r.json()["links"]["self"].rsplit("/", 1)[-1]
        f = c.get(f"/schema/Slate/fields/{field}").json()["data"]
        out(f"  forward Slate.{field}: name {f['name']['value']!r}, valid_types {f['properties']['valid_types']['value']}")
        new = sorted(set(c.get("/schema/Shot/fields").json()["data"]) - before)
        for n in new:
            g = c.get(f"/schema/Shot/fields/{n}").json()["data"]
            out(f"  new on Shot: {n}  data_type {g['data_type']['value']}, name {g['name']['value']!r}, "
                f"valid_types {g['properties'].get('valid_types', {}).get('value')}, "
                f"editable {g['editable']['value']}, visible {g['visible']['value']}")
        reverse = new[0] if len(new) == 1 else None

        NAME = {}
        with _lib.Created(c) as made:
            S = {}
            for n in ("S1", "S2", "S3"):
                sid = made.add("shots", c.post("/entity/shots", json={"project": P, "code": f"zzprobe_155_{n}"}).json()["data"]["id"])
                S[n] = {"type": "Shot", "id": sid}
                NAME[("Shot", sid)] = n
            r = c.post("/entity/slates", json={"project": P, "code": "zzprobe_155_slate", field: [S["S1"]]})
            out(f"\nPOST /entity/slates {{{field}: [S1]}} -> {said(r)}")
            sl = made.add("slates", r.json()["data"]["id"])
            NAME[("Slate", sl)] = "the slate"
            out(f"  Slate.{field} {linked('slates', sl, field)}; S1.{reverse} {linked('shots', S['S1']['id'], reverse)}")
            r = c.post("/entity/_batch", json={"requests": [{"request_type": "update", "entity": "Slate", "record_id": sl,
                "data": {field: {"multi_entity_update_mode": "add", "value": [S["S2"]]}}}]})
            out(f"_batch update, add [S2] -> {said(r)}; Slate.{field} {linked('slates', sl, field)}; "
                f"S2.{reverse} {linked('shots', S['S2']['id'], reverse)}")
            if reverse:
                r = c.put(f"/entity/shots/{S['S3']['id']}", json={reverse: [{"type": "Slate", "id": sl}]})
                out(f"PUT S3.{reverse} = [the slate] -> {said(r)}; Slate.{field} {linked('slates', sl, field)}")
                r = c.post("/entity/shots/_search", headers={"Content-Type": "application/vnd+shotgun.api3_array+json"},
                           json={"filters": [[reverse, "is", {"type": "Slate", "id": sl}]], "fields": ["code"]})
                out(f"Shots filtered [{reverse!r}, 'is', the slate] -> {sorted(NAME.get(('Shot', x['id'])) for x in r.json()['data'])}")
        _lib.emit("155_slate_shots_reverse", "\n".join(rows), env)
finally:
    if field:
        r = c.delete(f"/schema/Slate/fields/{field}")
        print(f"  retired /schema/Slate/fields/{field} -> {r.status_code}")
        if reverse:
            g = c.get(f"/schema/Shot/fields/{reverse}")
            print(f"  GET /schema/Shot/fields/{reverse} after -> {g.status_code}")
