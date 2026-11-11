"""Q: what does `POST /schema/<Type>/fields` answer a caller who is not an administrator, and which
permission groups may create fields?

Every field create in this corpus was made by the script, an API Admin. sg-onset may create its own
fields when a person signs in, so it needs the refusal a lower level gets. The person is the script
acting as them through `sudo_as_login` (probe 027): one active HumanUser per permission group that
has `can_impersonate_this_user` on. A group with no such person is reported as not measured.

Each caller sends the same create, a text field on the custom slot probe 123 wrote rows to, named
`zzprobe 132 <group>` so a create that lands is named `sg_zzprobe_132_<group>` and retired at once.
Before it, the caller's view of `GET /schema/permission_groups` and of its own group's rights on
that type, which is what `/spec.json` offers for "may I".

Read-only half: the permission listings. `--write` sends the creates. Run 2026-11-11 with Admin and
Artist; a rerun after a site admin turns impersonation on for a Manager and a Vendor names them, so
`sg_zzprobe_132_admin` is not spent again as `_admin_1` (probe 019):

    python probes/132_field_create_rights.py [--write] [--only Manager,Vendor] [--target]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
from sg_groundtruth.client import FPT  # noqa: E402

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:400]
    return json.dumps(j.get("errors", j))[:900]


schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
out(f"type: the first enabled custom slot, written <custom slot> below")

users = c.post("/entity/human_users/_search", headers=ARR, json={
    "filters": [["sg_status_list", "is", "act"], ["can_impersonate_this_user", "is", True]],
    "fields": ["login", "permission_rule_set"], "page": {"size": 200}}).json()["data"]
by_group = {}
for u in users:
    g = (u["relationships"]["permission_rule_set"]["data"] or {}).get("name")
    by_group.setdefault(g, u["attributes"]["login"])
sets = c.get("/entity/permission_rule_sets", params={"fields": "code,display_name,entity_type",
                                                     "page[size]": 100}).json()["data"]
human_sets = sorted(s["attributes"]["display_name"] for s in sets if s["attributes"]["entity_type"] == "HumanUser")
out(f"HumanUser permission groups on the site: {human_sets}")
out(f"groups with an active, impersonatable person: {sorted(by_group)}")
out(f"groups not measurable here: {sorted(set(human_sets) - set(by_group))}")

callers = [("script (API Admin)", c)] + [
    (g, FPT.from_env(env, sudo_as_login=login)) for g, login in sorted(by_group.items())]
for _, login in by_group.items():
    _lib.note_names(login)

out("\n===== what each caller can read about its own rights")
for label, cl in callers:
    r = cl.get("/schema/permission_groups", params={"permission_rule_set_entity_type": "HumanUser"})
    mine = r.json().get("data") if r.ok else errs(r)
    out(f"  {label}: GET /schema/permission_groups?…=HumanUser -> {r.status_code} "
        f"{[g.get('code') for g in mine] if isinstance(mine, list) else mine}")
    r2 = cl.get("/schema/permission_groups")
    own = r2.json().get("data") if r2.ok else []
    out(f"    GET /schema/permission_groups -> {r2.status_code} {[g.get('code') for g in own]}")
    for g in own[:1]:
        r3 = cl.get(f"/schema/permission_groups/{g['code']}/entity_types/{CE}")
        out(f"    GET …/{g['code']}/entity_types/<custom slot> -> {r3.status_code} "
            + (json.dumps(r3.json().get("data"))[:700] if r3.ok else errs(r3)))

admin = dict(callers).get("Admin")
if admin:
    out("\n===== every group's rights, as the Admin person reads them (probe 143 uses this table)")
    groups = [g["code"] for g in admin.get("/schema/permission_groups").json()["data"]]
    types = [t for t in sorted(schema) if t.startswith("CustomEntity") and t[12:].isdigit()] + ["Attachment"]
    out("  group                    type            read create update retire delete  update exceptions")
    for g in groups:
        for t in types:
            r = admin.get(f"/schema/permission_groups/{g}/entity_types/{t}")
            if not r.ok:
                out(f"  {g:<24} {t:<15} -> {r.status_code} {errs(r)}")
                continue
            a = r.json()["data"]["actions"]
            label = t if t == "Attachment" else f"<slot {t[12:]}>"
            out(f"  {g:<24} {label:<15} " + " ".join(f"{(a.get(k) or {}).get('access', '-')[:7]:<6}"
                                                   for k in ("read", "create", "update", "retire", "delete"))
                + f"  {json.dumps((a.get('update') or {}).get('field_exceptions'))}")
    r = admin.get(f"/schema/permission_groups/{groups[0]}/entity_types/{CE}/fields")
    out(f"\n  GET …/entity_types/<custom slot>/fields -> {r.status_code}, data keys "
        f"{sorted(r.json().get('data', {}))[:8] if r.ok else errs(r)}")
    r = admin.get("/schema/permission_groups/artist/entity_types/DisplayColumn")
    out(f"  GET …/artist/entity_types/DisplayColumn (the field definition type, probe 120) -> {r.status_code} "
        + (json.dumps(r.json()["data"].get("actions")) if r.ok else errs(r)))

_lib.emit("132_field_create_rights", "\n".join(rows), env)
if not _lib.writes_allowed():
    raise SystemExit("\nread-only half done; --write sends the creates")

rows.clear()
made = []
out("===== POST /schema/<custom slot>/fields, a text field, as each person")
try:
    only = sys.argv[sys.argv.index("--only") + 1].split(",") if "--only" in sys.argv else None
    for label, cl in ([] if "--target" in sys.argv else callers[1:]):
        if only and label not in only:
            continue
        tag = "".join(ch for ch in label.lower() if ch.isalnum())
        name = f"sg_zzprobe_132_{tag}"
        body = {"data_type": "text", "properties": [
            {"property_name": "name", "value": f"zzprobe 132 {tag}"}]}
        r = cl.post(f"/schema/{CE}/fields", json=body)
        out(f"  {label}: -> {r.status_code} {errs(r) if not r.ok else r.json()['links']['self'].rsplit('/', 1)[-1]}")
        if r.status_code == 201:
            made.append(r.json()["links"]["self"].rsplit("/", 1)[-1])
        # the other schema writes, on a name no field holds, so nothing can land
        r = cl.put(f"/schema/{CE}/fields/sg_zzprobe_132_absent", json={"properties": [
            {"property_name": "description", "value": "x"}]})
        out(f"    PUT an absent field -> {r.status_code} {errs(r)}")
        r = cl.delete(f"/schema/{CE}/fields/sg_zzprobe_132_absent")
        out(f"    DELETE an absent field -> {r.status_code} {errs(r)}")
        r = cl.post(f"/schema/{CE}/fields/sg_zzprobe_132_absent", json={"revive": True})
        out(f"    revive an absent field -> {r.status_code} {errs(r)}")
    # A PUT, DELETE and revive the Artist sends at a live field. The script's own, so a write that
    # lands touches nothing of the site's. Run 2026-11-11 after the creates above: a second create of
    # `zzprobe 132 admin` would spend `sg_zzprobe_132_admin_1` (probe 019), so the creates and this
    # section are separate runs: `--target` runs this one alone.
    if "--target" in sys.argv:
        out("\n===== a live field the script made, written by the Artist")
        r = c.post(f"/schema/{CE}/fields", json={"data_type": "text", "properties": [
            {"property_name": "name", "value": "zzprobe 132 target"}]})
        tgt = r.json()["links"]["self"].rsplit("/", 1)[-1] if r.status_code == 201 else None
        out(f"  script creates {tgt} -> {r.status_code}")
        if tgt:
            made.append(tgt)
            art = dict(callers).get("Artist")
            r = art.put(f"/schema/{CE}/fields/{tgt}", json={"properties": [
                {"property_name": "description", "value": "zzprobe 132 by artist"}]})
            out(f"  Artist PUT description -> {r.status_code} {errs(r)[:400]}")
            d = c.get(f"/schema/{CE}/fields/{tgt}").json()["data"]["description"]["value"]
            out(f"    description reads {d!r}")
            r = art.delete(f"/schema/{CE}/fields/{tgt}")
            out(f"  Artist DELETE -> {r.status_code} {errs(r)[:400]}")
            out(f"    live after: {c.get(f'/schema/{CE}/fields/{tgt}').status_code == 200}")
finally:
    for name in made:
        r = c.delete(f"/schema/{CE}/fields/{name}")
        out(f"  retired {name} -> {r.status_code}")
    left = [k for k in c.get(f"/schema/{CE}/fields").json()["data"] if "zzprobe_132" in k]
    out(f"  zzprobe_132 fields live on the type at exit: {left}")
    _lib.emit("132_field_create_rights (write)", "\n".join(rows), env)
