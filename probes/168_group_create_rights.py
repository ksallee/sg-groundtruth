"""Q: which permission groups may create, update and retire a Group over REST, as a person, and does
the rights call predict it?

sg-bids wants production to create a vendor Group from the app as the signed-in person. Probe 150
created one with the script only. Here person A is moved through Manager, Admin, Artist and Vendor
in turn and acts through `sudo_as_login` (probe 027), which applies that person's permission set
(probe 094); person B is the member A adds and removes. Per group, as A: the group's own rights on
Group (`GET /schema/permission_groups/<code>/entity_types/Group` and `/fields`) and `editable` in
`GET /schema/Group/fields`; then `POST /entity/groups` without `code`, with `code`, with the same
`code` again and with `users`; on the Group A made, a `PUT` of `code`, `users` add and remove, and a
`DELETE`; the same `PUT` and `DELETE` on a Group the script made. Then, with A a Manager and B a
Vendor: A creates a Group holding B and adds it to a sandbox Shot's `sg_vendor_groups`, and B fetches
the Shot before and after (probe 166).

People are site data, so they are named on the command line, never in source. The probe refuses a
person who is not an active, impersonatable alias of the operator (same email as `FPT_USER_LOGIN`),
never activates anyone, and in a `finally` puts back each person's permission group and projects,
then reads them back.

Writes behind `--write`: Groups `zzprobe_168_*` (site-wide) and one sandbox Shot, deleted on exit;
the two people's permission group, restored.

    python probes/168_group_create_rights.py --write --people A,B
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
from sg_groundtruth.client import FPT  # noqa: E402

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
ROLES = ["manager", "admin", "artist", "vendor"]
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed() or "--people" not in sys.argv:
    raise SystemExit("probe 168 writes; run with --write --people A,B")
A, B = [int(x) for x in sys.argv[sys.argv.index("--people") + 1].split(",")]
SB = _lib.sandbox_id(c, env)
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def said(r):
    """Status, and the whole `errors` array when there is one (probe.md: never truncate an error)."""
    if r.ok:
        return str(r.status_code)
    try:
        return f"{r.status_code} {json.dumps(r.json().get('errors', r.json()))}"
    except ValueError:
        return f"{r.status_code} {r.text[:1500]!r}"


def ref(t, i):
    return {"type": t, "id": i}


def person(i):
    d = c.get(f"/entity/human_users/{i}", params={
        "fields": "login,email,sg_status_list,can_impersonate_this_user,permission_rule_set,projects,groups"}).json()["data"]
    a, rel = d["attributes"], d["relationships"]
    _lib.note_names(a["login"])
    return {"login": a["login"], "email": (a["email"] or "").lower(), "status": a["sg_status_list"],
            "impersonatable": a["can_impersonate_this_user"],
            "set": rel["permission_rule_set"]["data"]["id"], "set_name": rel["permission_rule_set"]["data"]["name"],
            "projects": sorted(x["id"] for x in rel["projects"]["data"] or []),
            "groups": sorted(x["id"] for x in rel["groups"]["data"] or [])}


def show(i, s):
    return (f"person {'A' if i == A else 'B'}: {s['set_name']}, status {s['status']}, "
            f"projects {['sandbox' if p == SB else p for p in s['projects']]}, groups {s['groups']}")


login = env["FPT_USER_LOGIN"].strip()
mail = (c.post("/entity/human_users/_search", headers=ARR, json={
    "filters": [["login", "is", login]], "fields": ["email"]}).json()["data"][0]["attributes"]["email"] or "").lower()
before = {i: person(i) for i in (A, B)}
for i, s in before.items():
    if s["email"] != mail or s["status"] != "act" or not s["impersonatable"]:
        raise SystemExit(f"person {i} is not an active, impersonatable alias of the operator; refusing")
    if SB not in s["projects"]:
        raise SystemExit(f"person {i} is not in the sandbox project; the visibility step needs both there")
SETS = {s["attributes"]["code"]: s["id"] for s in c.get("/entity/permission_rule_sets", params={
    "fields": "code,entity_type", "page[size]": 100}).json()["data"] if s["attributes"]["entity_type"] == "HumanUser"}
out("before: " + "; ".join(show(i, s) for i, s in before.items()))


def role(i, code):
    r = c.put(f"/entity/human_users/{i}", json={"permission_rule_set": ref("PermissionRuleSet", SETS[code])})
    if not r.ok:
        raise SystemExit(f"could not move person {i} to {code}: {said(r)}")


def restore():
    for i, s in before.items():
        r = c.put(f"/entity/human_users/{i}", json={"permission_rule_set": ref("PermissionRuleSet", s["set"]),
                                                    "projects": [ref("Project", p) for p in s["projects"]]})
        out(f"  restore person {'A' if i == A else 'B'} -> {said(r)}")


def rights(who, code):
    r = who.get(f"/schema/permission_groups/{code}/entity_types/Group")
    if not r.ok:
        return said(r)
    acts = r.json()["data"]["actions"]
    return {k: v["access"] + (f" {v['field_exceptions']}" if v.get("field_exceptions") else "")
            + (f" condition {json.dumps(v['condition'])}" if v.get("condition") else "") for k, v in acts.items()}


def field_rights(who, code, names=("code", "users", "sg_people")):
    r = who.get(f"/schema/permission_groups/{code}/entity_types/Group/fields")
    if not r.ok:
        return said(r)
    return {x["field_name"]: {k: v["access"] for k, v in x.items() if isinstance(v, dict) and "access" in v}
            for x in r.json()["data"]["fields"] if x["field_name"] in names}


def editable(who, names=("code", "users", "sg_people")):
    r = who.get("/schema/Group/fields")
    if not r.ok:
        return said(r)
    return {k: v["editable"]["value"] for k, v in r.json()["data"].items() if k in names}


def members(g):
    d = c.get(f"/entity/groups/{g}", params={"fields": "users"})
    return sorted("B" if x["id"] == B else "A" if x["id"] == A else "other" for x in d.json()["data"]["relationships"]["users"]["data"]) if d.ok else said(d)


made_groups = {}
EVER = []


class Tracked(_lib.Created):
    """`Created`, remembering every row so the end of the run can read each one back."""

    def add(self, slug, entity_id):
        EVER.append((slug, entity_id))
        return super().add(slug, entity_id)


with Tracked(c) as made:
    try:
        for code in ROLES:
            role(A, code)
            p = FPT.from_env(env, sudo_as_login=before[A]["login"])
            out(f"\n===== person A as {code}")
            out(f"  rights on Group, own group: {rights(p, code)}")
            out(f"  field rights: {field_rights(p, code)}")
            out(f"  GET /schema/Group/fields editable: {editable(p)}")
            r = p.get("/schema/permission_groups", params={"permission_rule_set_entity_type": "HumanUser"})
            out(f"  GET /schema/permission_groups?…=HumanUser -> {said(r)} "
                f"{[x['code'] for x in r.json()['data']] if r.ok else ''}")
            r = p.get(f"/entity/human_users/{A}", params={"fields": "permission_rule_set"})
            own = r.json()["data"]["relationships"]["permission_rule_set"]["data"] if r.ok else None
            out(f"  own HumanUser permission_rule_set -> {said(r)} {own}")
            if own:
                r = p.get(f"/entity/permission_rule_sets/{own['id']}", params={"fields": "code,display_name"})
                out(f"  GET /entity/permission_rule_sets/<own> -> {said(r)} {r.json()['data']['attributes'] if r.ok else ''}")
            if code == "admin":
                for other in ROLES:
                    out(f"  as admin, {other} rights on Group: {rights(p, other)}")
                    out(f"  as admin, {other} field rights: {field_rights(p, other)}")
            r = p.post("/entity/groups", json={"users": []})
            out(f"  POST {{users: []}} (no code) -> {said(r)}")
            if r.status_code == 201:
                g = made.add("groups", r.json()["data"]["id"])
                d = c.get(f"/entity/groups/{g}", params={"fields": "code,cached_display_name"}).json()["data"]["attributes"]
                out(f"    read back: code {d['code']!r}, cached_display_name {d['cached_display_name']!r}")
            name = f"zzprobe_168_{code}"
            r = p.post("/entity/groups", json={"code": name}, params={"fields": "code,created_by"})
            out(f"  POST {{code}} -> {said(r)}")
            mine = None
            if r.status_code == 201:
                mine = made.add("groups", r.json()["data"]["id"])
                cb = r.json()["data"]["relationships"].get("created_by", {}).get("data") or {}
                out(f"    created_by is person A: {cb.get('id') == A}")
            r = p.post("/entity/groups", json={"code": name})
            out(f"  POST {{code}} again, same code -> {said(r)}")
            if r.status_code == 201:
                made.add("groups", r.json()["data"]["id"])
            r = p.post("/entity/groups", json={"code": f"{name}_users", "users": [ref("HumanUser", B)]})
            out(f"  POST {{code, users: [B]}} -> {said(r)}")
            if r.status_code == 201:
                g = made.add("groups", r.json()["data"]["id"])
                out(f"    users read back: {members(g)}")
            theirs = made.add("groups", c.post("/entity/groups", json={"code": f"{name}_script"}).json()["data"]["id"])
            for label, g in (("own", mine), ("script's", theirs)):
                if g is None:
                    out(f"  {label} Group: none to change")
                    continue
                r = p.put(f"/entity/groups/{g}", json={"code": f"zzprobe_168_{code}_{label[:3]}_renamed"})
                out(f"  {label} Group: PUT code -> {said(r)}")
                r = p.put(f"/entity/groups/{g}", json={"users": {"multi_entity_update_mode": "add",
                                                                 "value": [ref("HumanUser", B)]}})
                out(f"  {label} Group: PUT users add B -> {said(r)}; users {members(g)}")
                r = p.put(f"/entity/groups/{g}", json={"users": {"multi_entity_update_mode": "remove",
                                                                 "value": [ref("HumanUser", B)]}})
                out(f"  {label} Group: PUT users remove B -> {said(r)}; users {members(g)}")
                now = c.get(f"/entity/groups/{g}", params={"fields": "code"}).json()["data"]["attributes"]["code"]
                r = p.delete(f"/entity/groups/{g}")
                after = c.get(f"/entity/groups/{g}")
                out(f"  {label} Group: DELETE -> {said(r)}; GET as the script after -> {after.status_code}")
                if r.ok:
                    made.rows.remove(("groups", g))
                    if label == "own":
                        made_groups[code] = now

        out("\n===== duplicate and retired codes, as the script")
        g = made.add("groups", c.post("/entity/groups", json={"code": "zzprobe_168_dup"}).json()["data"]["id"])
        r = c.post("/entity/groups", json={"code": "zzprobe_168_dup"})
        out(f"  POST the code of a live Group -> {said(r)}")
        if r.status_code == 201:
            made.add("groups", r.json()["data"]["id"])
        r = c.post("/entity/groups", json={"code": "ZZPROBE_168_DUP"})
        out(f"  POST the same code in upper case -> {said(r)}")
        if r.status_code == 201:
            made.add("groups", r.json()["data"]["id"])
        if made_groups:
            r = c.post("/entity/groups", json={"code": next(iter(made_groups.values()))})
            out(f"  POST the code of a Group retired above -> {said(r)}")
            if r.status_code == 201:
                made.add("groups", r.json()["data"]["id"])

        out("\n===== a Group person A made, as Manager, in Shot.sg_vendor_groups; person B a Vendor")
        role(A, "manager")
        role(B, "vendor")
        p = FPT.from_env(env, sudo_as_login=before[A]["login"])
        v = FPT.from_env(env, sudo_as_login=before[B]["login"])
        r = p.post("/entity/groups", json={"code": "zzprobe_168_award", "users": [ref("HumanUser", B)]})
        out(f"  A: POST {{code, users: [B]}} -> {said(r)}")
        maker = p if r.status_code == 201 else c
        if r.status_code != 201:
            r = c.post("/entity/groups", json={"code": "zzprobe_168_award", "users": [ref("HumanUser", B)]})
            out(f"  the script made it instead -> {said(r)}")
        g = made.add("groups", r.json()["data"]["id"])
        shot = made.add("shots", c.post("/entity/shots", json={"project": ref("Project", SB),
                                                               "code": "zzprobe_168_shot"}).json()["data"]["id"])
        out(f"  B: GET the Shot, no vendor group -> {said(v.get(f'/entity/shots/{shot}'))}")
        r = p.put(f"/entity/shots/{shot}", json={"sg_vendor_groups": {"multi_entity_update_mode": "add",
                                                                      "value": [ref("Group", g)]}})
        out(f"  A: PUT sg_vendor_groups add the Group -> {said(r)}")
        if not r.ok:
            r = c.put(f"/entity/shots/{shot}", json={"sg_vendor_groups": [ref("Group", g)]})
            out(f"  the script added it instead -> {said(r)}")
        t0 = time.time()
        out(f"  B: GET the Shot at once -> {said(v.get(f'/entity/shots/{shot}'))} ({time.time() - t0:.1f} s)")
        r = c.put(f"/entity/shots/{shot}", json={"sg_vendor_groups": []})
        out(f"  script: clear sg_vendor_groups -> {said(r)}; B: GET -> {said(v.get(f'/entity/shots/{shot}'))}")
    finally:
        out("\n===== restore")
        restore()

after = {i: person(i) for i in (A, B)}
out("after: " + "; ".join(show(i, s) for i, s in after.items()))
same = all(after[i][k] == before[i][k] for i in (A, B) for k in ("set", "projects", "groups", "status"))
out(f"  everything as before: {same}")
left = [(t, i) for t, i in EVER if c.get(f"/entity/{t}/{i}").status_code != 404]
out(f"  rows the probe made: {len(EVER)}; still live: {left}")
_lib.emit("168_group_create_rights", "\n".join(rows), env)
