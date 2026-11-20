"""Q: can permission rules be read over REST, enough for an app to check that a site has the rule it
needs, and can a conditional see rule be created or changed over REST?

sg-bids needs the Vendor group to see only its own Bid rows. Probe 027 found `PermissionRuleSet` rows
with no rule on them; probes 132 and 143 read `actions` from the permission group calls without the
condition. `/spec.json` gives `PermissionGroupAccess` a `condition` key "present when `access` is
`conditional`". This reads the Vendor group's rules on Bid, Bid Line, Shot and Project as the script,
as an Admin person and as a Vendor person, checks the Shot rule an award depends on the way an app
would, and lists every method the spec offers on the permission routes.

`--write` then tries to add one conditional see rule to the Vendor group on Bid, as the script and as
the Admin person, by every write a client could try on those routes. Before each try the group's
rights on Bid are read; after it they are read again, and a change is put back from the copy and read
back. It also re-roles vendor A (`_bids.vendors`) to read the rules as a Vendor, and restores them.

    python probes/162_permission_rules_rest.py [--write --people A,B --groups GA,GB]
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bids  # noqa: E402
import _lib  # noqa: E402
from _bids import said  # noqa: E402
from sg_groundtruth.client import FPT  # noqa: E402

env = _lib.load_env()
c = _lib.client()
S = _bids.slots(c)
BID = S["Bid"]
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def label(t):
    return {S["Bid"]: "<Bid>", S["Bid Line"]: "<Bid Line>"}.get(t, t)


def leaves(cond):
    """Every leaf of a condition tree, as (path, relation, first value's `valid` or the value, its id)."""
    if not cond:
        return []
    if "conditions" in cond:
        return [x for k in cond["conditions"] for x in leaves(k)]
    v = (cond.get("values") or [None])[0]
    return [(cond.get("path"), cond.get("relation"), v.get("valid") if isinstance(v, dict) else v,
             v.get("id") if isinstance(v, dict) else None)]


def has_rule(rights, path, me=None):
    """An app's check: is this type's read conditional on `path` holding the signed-in person?

    An Admin reads the person as `logged_in_user_token`; the person reading their own group reads
    their own row in its place, so `me` is their HumanUser id.
    """
    read = rights["actions"]["read"]
    return read["access"] == "conditional" and any(
        p == path and rel == "is" and (valid == "logged_in_user_token" or (me and i == me))
        for p, rel, valid, i in leaves(read.get("condition")))


out("===== what the spec offers")
spec = c.get("/spec.json").json()
for p, ops in spec["paths"].items():
    if "permission" in p:
        out(f"  {p}: {sorted(m.upper() for m in ops if m in ('get', 'put', 'post', 'patch', 'delete'))}")
acc = spec["components"]["schemas"]["PermissionGroupAccess"]["properties"]
out(f"  PermissionGroupAccess keys {sorted(acc)}; access enum {acc['access']['enum']}")
out(f"  condition: {acc['condition']['description']!r}")
types = [t for t in c.get("/schema").json()["data"] if "Permission" in t or "Rule" in t]
out(f"  /schema types named like a rule: {types}")
for t in ("permission_rules", "permissions", "PermissionRule"):
    out(f"  GET /entity/{t} -> {said(c.get(f'/entity/{t}'))}")
f = c.get("/schema/PermissionRuleSet/fields").json()["data"]
out(f"  /schema/PermissionRuleSet/fields: {len(f)} fields, {sum(v['editable']['value'] for v in f.values())} editable")

adm = FPT.from_env(env, sudo_as_login=env["FPT_USER_LOGIN"])
out("\n===== who can read the Vendor group's rules")
for who, cl in (("script", c), ("Admin person", adm)):
    r = cl.get("/schema/permission_groups", params={"permission_rule_set_entity_type": "HumanUser"})
    out(f"  {who}: GET /schema/permission_groups?…=HumanUser -> {r.status_code} {[g['code'] for g in r.json()['data']]}")
    out(f"  {who}: GET …/vendor/entity_types/Shot -> {said(cl.get('/schema/permission_groups/vendor/entity_types/Shot'))}")

out("\n===== the Vendor group's rules, as the Admin person reads them")
rights = {}
for t in (BID, S["Bid Line"], "Shot", "Project"):
    d = adm.get(f"/schema/permission_groups/vendor/entity_types/{t}").json()["data"]
    rights[t] = d
    a = d["actions"]
    out(f"  {label(t)}: " + ", ".join(f"{k} {a[k]['access']}" for k in ("read", "create", "update", "retire", "delete"))
        + (f"; update allows {a['update']['field_exceptions']['allow']}" if a["update"].get("field_exceptions") else ""))
    for k in ("read", "retire"):
        if a[k].get("condition"):
            cond = a[k]["condition"]
            out(f"    {k} condition, logical_operator {cond.get('logical_operator')!r}:")
            for leaf in leaves(cond):
                out(f"      {leaf[:3]}")
    raw = d["permissions"]
    out(f"    raw hash keys: {sorted(raw)}")
out(f"  raw Shot see_condition == actions.read.condition: "
    f"{rights['Shot']['permissions'].get('see_condition') == rights['Shot']['actions']['read'].get('condition')}")
out(f"  updated_at on the group: {rights['Shot']['permission_group']['updated_at']}")
fl = adm.get(f"/schema/permission_groups/vendor/entity_types/{BID}/fields").json()["data"]["fields"]
out(f"  <Bid> fields: {len(fl)}; see denied on {[x['field_name'] for x in fl if x['see']['access'] != 'allowed']}; "
    f"update allowed on {[x['field_name'] for x in fl if x['update']['access'] != 'denied']}")
out("\n===== an app's check, `has_rule(rights, path)`")
for t, path in (("Shot", "sg_vendor_groups.Group.users"), ("Shot", "sg_vendor_groups.Group.sg_people"),
                ("Shot", "sg_zzprobe_nothing.Group.users"), (BID, "sg_zzprobe_163_vendor_groups.Group.users")):
    out(f"  {label(t)} read conditional on {path} is Me: {has_rule(rights[t], path)}")

_lib.emit("162_permission_rules_rest", "\n".join(rows), env)
if not _lib.writes_allowed():
    raise SystemExit("\nread-only half done; --write tries the rule writes and reads as a Vendor")

rows.clear()
SB = _lib.sandbox_id(c, env)
COND = {"logical_operator": "or", "conditions": [{"path": "created_by", "relation": "is", "values": [_bids.TOKEN]}]}
WANT = {"actions": {"read": {"access": "conditional", "condition": COND}},
        "permissions": {"see": True, "see_restricted": "special_rules", "see_condition": COND}}
URL = f"/schema/permission_groups/vendor/entity_types/{BID}"


def state():
    d = adm.get(URL).json()["data"]
    return {"actions": d["actions"], "permissions": d["permissions"], "updated_at": d["permission_group"]["updated_at"]}


before = state()
out(f"===== before any write, the Vendor group on <Bid>: {json.dumps(before['actions'])}")
out(f"  updated_at {before['updated_at']}")
changed = False
tries = [("PUT", URL, WANT), ("POST", URL, WANT), ("PATCH", URL, WANT),
         ("PUT", URL + "/fields", {"fields": [{"field_name": "code", "see": {"access": "denied"}}]}),
         # the role's own row, written with the value it holds: a 200 here changes nothing
         ("PUT", "/entity/permission_rule_sets/" + str(_bids.vendor_set(c)), {"display_name": "Vendor"})]
for who, cl in (("script", c), ("Admin person", adm)):
    for method, url, body in tries:
        r = cl.request(method, url, json=body)
        now = state()
        moved = now != before
        out(f"  {who}: {method} {url.replace(BID, '<Bid>')} -> {said(r)}; rights changed: {moved}")
        if moved:
            changed = True
            out(f"    now {json.dumps(now['actions'])}")
            back = cl.request("PUT", URL, json={"actions": before["actions"], "permissions": before["permissions"]})
            out(f"    put back -> {said(back)}; matches the copy: {state()['actions'] == before['actions']}")
            if state()["actions"] != before["actions"]:
                _lib.emit("162_permission_rules_rest (write)", "\n".join(rows), env)
                raise SystemExit("a rule changed and could not be put back: stop and report")
out(f"  after every try, equal to the copy: {state() == before}")

out("\n===== the same rules, read by a Vendor person")
with _bids.vendors(c, env, SB, out) as vs:
    (pa, va, ga, _), _ = vs
    r = va.get("/schema/permission_groups")
    out(f"  vendor A: GET /schema/permission_groups -> {r.status_code} {[g['code'] for g in r.json()['data']]}")
    r = va.get("/schema/permission_groups", params={"permission_rule_set_entity_type": "HumanUser"})
    out(f"  vendor A: …?permission_rule_set_entity_type=HumanUser -> {r.status_code} {[g['code'] for g in r.json()['data']]}")
    for t in ("Shot", BID):
        r = va.get(f"/schema/permission_groups/vendor/entity_types/{t}")
        same = r.ok and r.json()["data"]["actions"] == rights[t]["actions"]
        out(f"  vendor A: …/vendor/entity_types/{label(t)} -> {said(r)}; equals the Admin's read: {same}")
        if r.ok and not same:
            mine = r.json()["data"]
            for k in ("read", "create", "update", "retire", "delete"):
                if mine["actions"].get(k) != rights[t]["actions"].get(k):
                    out(f"    {k}: vendor reads {json.dumps(mine['actions'].get(k))[:700]}")
                    out(f"    {k}: Admin reads  {json.dumps(rights[t]['actions'].get(k))[:700]}")
            out(f"    raw hash keys as the vendor: {sorted(mine['permissions'])}")
        if r.ok:
            for path in ("sg_vendor_groups.Group.users", "sg_vendor_groups.Group.sg_people"):
                out(f"    has_rule(path {path}): token only {has_rule(r.json()['data'], path)}, "
                    f"token or own id {has_rule(r.json()['data'], path, me=pa)}")
    out(f"  vendor A: …/artist/entity_types/Shot -> {said(va.get('/schema/permission_groups/artist/entity_types/Shot'))}")
    r = va.get("/schema/permission_groups/vendor/entity_types/Shot/fields")
    out(f"  vendor A: …/vendor/entity_types/Shot/fields -> {said(r)}")
_lib.emit("162_permission_rules_rest (write)", "\n".join(rows), env)
