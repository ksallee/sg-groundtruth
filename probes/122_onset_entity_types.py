"""Q: are the built-in on-set types (Slate, Camera, MocapTake, ShootDay, Scene, Element) there, what
does each take to create, and how do they link to Shot and Version?

`Version.entity` names Slate, Camera, MocapTake and ShootDay in its `valid_types` (entity_types/Version)
and nothing in the corpus had read one of them. An on-set capture app (sg-onset) wants them as its
record types, so this measures, per type: whether `/schema` lists it, the REST slug, the fields probe
056 would call stock (`visible.editable` false), the create contract, and every link field between the
type and Shot or Version, read from both ends.

It also re-runs the read half of probe 114 for item 2 of issue 100: can a custom entity slot be
enabled or renamed through the API. Nothing sent can change a real slot. The rename is addressed only
at a type that does not exist, as 114 did for activation.

Read-only by default. `--write` creates throwaway rows named `zzprobe_122_*` in the sandbox project and
deletes them before it exits.

    python probes/122_onset_entity_types.py [--write]
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
TYPES = ("Slate", "Camera", "MocapTake", "ShootDay", "Scene", "Element")
SLUGS = {"Slate": ("slates", "slate"), "Camera": ("cameras", "camera"),
         "MocapTake": ("mocap_takes", "mocaptakes", "MocapTake"),
         "ShootDay": ("shoot_days", "shootdays", "ShootDay"), "Scene": ("scenes", "scene"),
         "Element": ("elements", "element", "Element")}
rows = []


def out(s=""):
    rows.append(str(s))


def head(t):
    out(f"\n===== {t}")


def errs(r):
    """The whole errors[] object. The 400 is the documentation (probe 017)."""
    try:
        j = r.json()
    except ValueError:
        return r.text[:300]
    return json.dumps(j.get("errors", j))


# ---------------------------------------------------------------- presence
head("GET /schema: which of the six are listed")
schema = c.get("/schema").json()["data"]
present = []
for t in TYPES:
    v = schema.get(t)
    if v:
        present.append(t)
        out(f"  {t:<10} listed  name={v['name']['value']!r} visible={v['visible']}")
    else:
        conn = sorted(k for k in schema if t in k and k != t)
        out(f"  {t:<10} absent  connection types naming it that /schema does list: {conn}")
        r = c.get(f"/schema/{t}/fields")
        out(f"    GET /schema/{t}/fields -> {r.status_code} {errs(r)}")
        r = c.get(f"/schema/{t}")
        out(f"    GET /schema/{t} -> {r.status_code} {errs(r)}")

head("REST slug: which spellings resolve, and the site-wide row count")
for t in TYPES:
    for slug in SLUGS[t]:
        r = c.get(f"/entity/{slug}", params={"page[size]": 500, "fields": "id"})
        out(f"  GET /entity/{slug:<12} -> {r.status_code}"
            + (f"  rows={len(r.json()['data'])}" if r.ok else f"  {errs(r)}"))

# ---------------------------------------------------------------- fields
fields = {t: c.get(f"/schema/{t}/fields").json()["data"] for t in present}
head("fields: stock by probe 056 (visible.editable false) against the site's own")
for t in present:
    d = fields[t]
    stock = sorted(f for f, v in d.items() if not v["visible"]["editable"])
    site = sorted(f for f, v in d.items() if v["visible"]["editable"])
    out(f"  {t}: {len(d)} fields, {len(stock)} stock, {len(site)} the site's")
    out(f"    stock: {', '.join(stock)}")
    for f in ("code", "project", "image", "filmstrip_image", "attachments", "sg_status_list"):
        v = d.get(f)
        out(f"    {f:<16} " + ("absent" if v is None else
                              f"{v['data_type']['value']:<12} editable={v['editable']['value']} "
                              f"mandatory={v['mandatory']['value']} name={v['name']['value']!r}"))
    st = d.get("sg_status_list")
    if st:
        p = st["properties"]
        out(f"    status default={p['default_value']['value']!r} valid={p['valid_values']['value']}")

head("link fields between the six and Shot or Version, read from both ends")
for t in present:
    for f, v in sorted(fields[t].items()):
        vt = v["properties"].get("valid_types", {}).get("value") or []
        if f != "image_source_entity" and v["data_type"]["value"] in ("entity", "multi_entity") \
                and ({"Shot", "Version"} & set(vt)):
            out(f"  {t}.{f:<22} {v['data_type']['value']:<12} stock={not v['visible']['editable']!s:<5} "
                f"{vt} name={v['name']['value']!r}")
for ent in ("Shot", "Version", "Note", "Attachment", "Task"):
    for f, v in sorted(c.get(f"/schema/{ent}/fields").json()["data"].items()):
        vt = v["properties"].get("valid_types", {}).get("value") or []
        hit = [x for x in TYPES if x in vt]
        if hit and f != "image_source_entity":
            out(f"  {ent}.{f:<22} {v['data_type']['value']:<12} stock={not v['visible']['editable']!s:<5} "
                f"names {hit} of {len(vt)} valid_types")

# ---------------------------------------------------------------- item 2: custom entity slots
head("custom entity slots: enable or rename by API (probe 114, re-run)")
on = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())
off = [f"CustomEntity{n:02d}" for n in range(1, 51) if f"CustomEntity{n:02d}" not in schema]
out(f"  enabled slots: {len(on)}; absent from /schema: {len(off)}")
for label, method, path, body in (
        ("an enabled slot, read", "GET", f"/preferences/custom_entity/{on[0]}/configuration", None),
        ("a stock on-set type, read", "GET", "/preferences/custom_entity/Slate/configuration", None),
        ("rename, a type that does not exist", "PUT",
         "/preferences/custom_entity/NotAnEntityType/configuration", {"display_name": "zzprobe_122"}),
        ("enable, a type that does not exist", "PUT",
         "/preferences/custom_entity/NotAnEntityType/activation", {"enabled": True}),
        ("enable, an absent slot, no keys", "PUT", f"/preferences/custom_entity/{off[-1]}/activation",
         {})):
    r = c.request(method, path, json=body) if body is not None else c.request(method, path)
    out(f"  [{label}] {method} {path.replace(on[0], '<enabled slot>').replace(off[-1], '<absent slot>')}"
        f" {json.dumps(body) if body is not None else ''} -> {r.status_code} {errs(r)}")
r = c.get("/preferences", params={"prefs": "*"})
keys = sorted((r.json().get("data") or {}).keys())
out(f"  GET /preferences?prefs=* -> {r.status_code}, {len(keys)} keys; naming an entity or a slot: "
    f"{[k for k in keys if 'entit' in k or 'custom' in k]}")

_lib.emit("122_onset_entity_types", "\n".join(rows), env)
if not _lib.writes_allowed():
    raise SystemExit("\nread-only half done; --write runs the creates in the sandbox")

# ---------------------------------------------------------------- write half
rows.clear()
SB = _lib.sandbox_id(c, env)
PROJ = {"type": "Project", "id": SB}
creatable = [t for t in present if t != "Element"]
with _lib.Created(c) as made:
    head("create contract, sandbox project")
    one = {}
    for t in creatable:
        slug = SLUGS[t][0]
        for label, body in (("{}", {}), ("code only", {"code": f"zzprobe_122_{t}"}),
                            ("project only", {"project": PROJ}),
                            ("project and code", {"project": PROJ, "code": f"zzprobe_122_{t}"})):
            r = c.post(f"/entity/{slug}", json=body)
            if r.status_code == 201:
                d = r.json()["data"]
                made.add(slug, d["id"])
                one.setdefault(t, d["id"])
                a = d["attributes"]
                out(f"  {t:<10} {label:<17} -> 201  code={a.get('code')!r} "
                    f"status={a.get('sg_status_list')!r}")
            else:
                out(f"  {t:<10} {label:<17} -> {r.status_code} {errs(r)}")

    head("Version.entity set to each type, then the type's own fields read back")
    vids = {}
    for t in creatable:
        r = c.post("/entity/versions", json={"project": PROJ, "code": f"zzprobe_122_on_{t}",
                                             "entity": {"type": t, "id": one[t]}})
        if r.status_code != 201:
            out(f"  Version entity={t} -> {r.status_code} {errs(r)}")
            continue
        vids[t] = made.add("versions", r.json()["data"]["id"])
        back = c.get(f"/entity/versions/{vids[t]}", params={"fields": "entity"}).json()["data"]
        ent = back["relationships"]["entity"]["data"]
        out(f"  Version entity={t} -> 201, reads back {ent and ent['type']}")
        mv = [f for f, v in fields[t].items() if v["data_type"]["value"] == "multi_entity"
              and "Version" in (v["properties"].get("valid_types", {}).get("value") or [])]
        if mv:
            got = c.get(f"/entity/{SLUGS[t][0]}/{one[t]}", params={"fields": ",".join(mv)}).json()
            for f in mv:
                held = [x["id"] for x in (got["data"]["relationships"].get(f, {}).get("data") or [])]
                out(f"    {t}.{f} after it: holds the Version: {vids[t] in held} ({len(held)} rows)")

    head("Shot to Scene: Shot.sg_scene set, Scene.shots read back, and the other way")
    shot = made.add("shots", c.post("/entity/shots", json={"project": PROJ, "code": "zzprobe_122_sh"})
                    .json()["data"]["id"])
    if "Scene" in one:
        r = c.put(f"/entity/shots/{shot}", json={"sg_scene": {"type": "Scene", "id": one["Scene"]}})
        sc = c.get(f"/entity/scenes/{one['Scene']}", params={"fields": "shots"}).json()["data"]
        held = [x["id"] for x in sc["relationships"]["shots"]["data"] or []]
        out(f"  PUT Shot.sg_scene -> {r.status_code}; Scene.shots holds the Shot: {shot in held}")
        r = c.put(f"/entity/shots/{shot}", json={"sg_scene": None})
        r = c.put(f"/entity/scenes/{one['Scene']}",
                  json={"shots": [{"type": "Shot", "id": shot}]})
        sh = c.get(f"/entity/shots/{shot}", params={"fields": "sg_scene"}).json()["data"]
        out(f"  PUT Scene.shots -> {r.status_code}; Shot.sg_scene reads "
            f"{json.dumps(sh['relationships']['sg_scene']['data'])}")
    for t in ("Slate", "Camera", "MocapTake", "ShootDay"):
        if t in one:
            r = c.put(f"/entity/shots/{shot}", json={"sg_scene": {"type": t, "id": one[t]}})
            out(f"  PUT Shot.sg_scene = a {t} (valid_types is [Scene]) -> {r.status_code}"
                + ("" if r.ok else f" {errs(r)}"))
    c.put(f"/entity/shots/{shot}", json={"sg_scene": None})

    head("Note.note_links naming each type, the stock way to hang text on a Slate")
    for t in creatable:
        r = c.post("/entity/notes", json={"project": PROJ, "subject": "zzprobe_122",
                                          "content": "zzprobe_122",
                                          "note_links": [{"type": t, "id": one[t]}]})
        if r.status_code == 201:
            made.add("notes", r.json()["data"]["id"])
        out(f"  Note note_links=[{t}] -> {r.status_code}" + ("" if r.ok else f" {errs(r)}"))

    _lib.emit("122_onset_entity_types (write)", "\n".join(rows), env)
