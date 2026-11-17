"""Q: does a dotted read or filter reach a custom field through an entity field, on a custom entity
and on a built-in one, and across two hops?

sg-onset lists takes with their lens and camera details in one call. Probes 016 and 059 measured
dotted paths through stock fields; this sends them at site-added (`sg_`) fields: a custom field on a
custom entity reached through a custom entity field on Slate, a custom field on Slate reached from a
Version, and the two chained. Every path is sent as a projection on `GET`, on `_search`, and as a
filter.

The entity field is the first one on Slate whose `valid_types` is a single enabled custom slot, and
the target the first `sg_` text field on that slot. Both are site fields; the finding names them by
shape only.

Writes in the sandbox, behind `--write`: one custom row, one Slate, one Version, `zzprobe_138_*`,
deleted on exit.

    python probes/138_dotted_custom_field.py --write
"""
import json

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 138 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:500]
    except ValueError:
        return repr(r.text[:300])


slate_f = c.get("/schema/Slate/fields").json()["data"]
LINK, CE = None, None
for k, v in sorted(slate_f.items()):
    vt = v["properties"].get("valid_types", {}).get("value") or []
    if k.startswith("sg_") and v["data_type"]["value"] == "entity" and len(vt) == 1 and vt[0].startswith("CustomEntity"):
        LINK, CE = k, vt[0]
        break
if not LINK:
    raise SystemExit("no sg_ entity field on Slate to a single custom slot on this site")
ce_f = c.get(f"/schema/{CE}/fields").json()["data"]
TARGET = sorted(k for k, v in ce_f.items() if k.startswith("sg_") and v["data_type"]["value"] == "text")[0]
SLATE_TEXT = sorted(k for k, v in slate_f.items() if k.startswith("sg_") and v["data_type"]["value"] == "text"
                    and v["editable"]["value"])[0]
SLUG = f"custom_entity{CE[12:]}s"
out(f"Slate.<link> is an sg_ entity field to one custom slot; <target> an sg_ text field on it; "
    f"<slate_text> an sg_ text field on Slate")

ONE = f"{LINK}.{CE}.{TARGET}"
VAL, SVAL = "zzprobe_138_target", "zzprobe_138_slate"
with _lib.Created(c) as made:
    ce = made.add(SLUG, c.post(f"/entity/{SLUG}", json={"project": P, "code": "zzprobe_138", TARGET: VAL}).json()["data"]["id"])
    sl = made.add("slates", c.post("/entity/slates", json={"project": P, "code": "zzprobe_138",
                                                           LINK: {"type": CE, "id": ce}, SLATE_TEXT: SVAL}).json()["data"]["id"])
    v = made.add("versions", c.post("/entity/versions", json={"project": P, "code": "zzprobe_138",
                                                              "entity": {"type": "Slate", "id": sl}}).json()["data"]["id"])
    cases = [
        ("Slate", "slates", sl, ONE, VAL, "Slate.<link>.<slot>.<target>"),
        ("Version", "versions", v, f"entity.Slate.{SLATE_TEXT}", SVAL, "Version.entity.Slate.<slate_text>"),
        ("Version", "versions", v, f"entity.Slate.{ONE}", VAL, "Version.entity.Slate.<link>.<slot>.<target>"),
        ("Version", "versions", v, f"entity.Slate.{LINK}", None, "Version.entity.Slate.<link> (the entity itself)"),
    ]
    for t, slug, rid, path, want, label in cases:
        out(f"\n===== {label}")
        g = c.get(f"/entity/{slug}/{rid}", params={"fields": path})
        ga = g.json()["data"] if g.ok else {}
        got = (ga.get("attributes") or {}).get(path, (ga.get("relationships") or {}).get(path, "<absent>"))
        out(f"  GET ?fields= -> {g.status_code} {json.dumps(got)[:200] if g.ok else errs(g)}")
        s = c.post(f"/entity/{slug}/_search", headers=ARR, json={
            "filters": [["id", "is", rid]], "fields": [path]})
        sa = s.json()["data"][0] if s.ok and s.json()["data"] else {}
        sgot = (sa.get("attributes") or {}).get(path, (sa.get("relationships") or {}).get(path, "<absent>"))
        out(f"  _search fields -> {s.status_code} {json.dumps(sgot)[:200] if s.ok else errs(s)}")
        if want:
            for op, val in (("is", want), ("is", "zzprobe_138_nomatch"), ("starts_with", "zzprobe_138")):
                f = c.post(f"/entity/{slug}/_search", headers=ARR, json={
                    "filters": [["project", "is", P], [path, op, val]], "fields": ["id"]})
                out(f"  filter {op} {val!r} -> {f.status_code} "
                    + (f"{len(f.json()['data'])} rows" if f.ok else errs(f)))
            f = c.get(f"/entity/{slug}", params={f"filter[{path}]": want, "filter[project.Project.id]": SB,
                                                 "fields": "id"})
            out(f"  GET ?filter[path]= -> {f.status_code} " + (f"{len(f.json()['data'])} rows" if f.ok else errs(f)))
    _lib.emit("138_dotted_custom_field", "\n".join(rows), env)
