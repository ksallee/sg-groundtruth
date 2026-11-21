"""Plumbing for the bidding probes, 162 to 167 and `field_types/currency` (issue #118).

sg-bids keeps bids on two custom entities displayed `Bid` and `Bid Line`, and awards a Shot by adding
the vendor's Group to `Shot.sg_vendor_groups`. A slot is site configuration, so both are found by
display name and never named here.

Two throwaway people act as vendor A and vendor B, and two Groups as their vendors. People and Groups
are site data exactly as a project is, so they are named on the command line, never in source:

    --people <A>,<B> --groups <group A>,<group B>

`vendors()` moves each person to the Vendor permission group, joins them to their Group's `users` and
keeps them in the sandbox project. On the way out, failure included, it puts back each person's
permission group and projects and each Group's `users` and `sg_people`, then reads them back. It
refuses a person who is not an alias of the operator (same email as `FPT_USER_LOGIN`, active,
impersonatable: the rule `_people` uses), so it cannot re-role a real account. It never activates
anyone.

The probes' schema fields are created when absent, revived when retired, and left in place: a field's
name stays taken after `DELETE` (probe 019), so a rerun reuses them.
"""
import sys
import time
from contextlib import contextmanager

import _lib
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}

# (display name of the type, data_type, field display name, valid_types). "<Bid>" is the Bid slot.
FIELDS = [
    ("Bid", "multi_entity", "zzprobe 163 vendor groups", ["Group"]),
    ("Bid Line", "entity", "zzprobe 163 bid", ["<Bid>"]),
    ("Bid Line", "entity", "zzprobe 163 shot", ["Shot"]),
    ("Bid Line", "currency", "zzprobe currency amount", None),
]
TOKEN = {"type": "HumanUser", "id": 0, "valid": "logged_in_user_token", "name": "Me"}


def said(r):
    """Status and the whole first error, `source` included (probe.md: never truncate an error)."""
    if r.ok:
        return str(r.status_code)
    try:
        e = r.json()["errors"][0]
        src = e.get("source")
        return (f"{r.status_code} code {e.get('code')} {e.get('title')!r}"
                + (f" source {src}" if src else "") + (f" detail {e['detail']!r}" if e.get("detail") else ""))
    except (ValueError, KeyError, IndexError, TypeError):
        return f"{r.status_code} {r.text[:600]!r}"


def slots(c):
    """{'Bid': 'CustomEntityNN', 'Bid Line': 'CustomEntityMM'}, by display name."""
    found = {}
    for t, v in c.get("/schema").json()["data"].items():
        if t.startswith("CustomEntity") and t[12:].isdigit() and v["name"]["value"] in ("Bid", "Bid Line"):
            found[v["name"]["value"]] = t
    if set(found) != {"Bid", "Bid Line"}:
        raise SystemExit(f"enable two custom entities displayed 'Bid' and 'Bid Line'; found {found}")
    return found


def slug(t):
    return f"custom_entity{t[12:]}s"


def field_name(display):
    return "sg_" + "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in display.lower())


def ensure_fields(c, s, out=print):
    """Create, or revive, the probes' fields. Returns {display name of the field: field name}."""
    names = {}
    for owner, dt, display, vt in FIELDS:
        t = s[owner]
        name = field_name(display)
        names[display] = name
        live = c.get(f"/schema/{t}/fields").json()["data"]
        if name in live:
            out(f"  {owner}.{name}: {dt}, already live")
            continue
        props = [{"property_name": "name", "value": display}]
        if vt:
            props.append({"property_name": "valid_types", "value": [s["Bid"] if v == "<Bid>" else v for v in vt]})
        r = c.post(f"/schema/{t}/fields", json={"data_type": dt, "properties": props})
        if r.status_code == 201:
            made = r.json()["links"]["self"].rsplit("/", 1)[-1]
            out(f"  {owner}.{made}: {dt}, created -> 201")
            if made != name:
                raise SystemExit(f"created {made}, expected {name}")
            continue
        rv = c.post(f"/schema/{t}/fields/{name}", json={"revive": True})
        out(f"  {owner}.{name}: create {said(r)}; revive {said(rv)}")
        if not rv.ok:
            raise SystemExit("could not create or revive a probe field")
    return names


def _ids(flag):
    if flag not in sys.argv:
        raise SystemExit(f"name two throwaway people and their Groups: --people A,B --groups GA,GB")
    return [int(x) for x in sys.argv[sys.argv.index(flag) + 1].split(",")]


def _ref(t, i):
    return {"type": t, "id": i}


def _link_ids(row, field):
    return sorted(x["id"] for x in (row["relationships"][field]["data"] or []))


def snapshot(c, people, groups):
    snap = {"people": {}, "groups": {}}
    for p in people:
        d = c.get(f"/entity/human_users/{p}", params={
            "fields": "login,email,sg_status_list,can_impersonate_this_user,permission_rule_set,projects,groups"}).json()["data"]
        snap["people"][p] = {"login": d["attributes"]["login"], "email": d["attributes"]["email"],
                             "status": d["attributes"]["sg_status_list"],
                             "impersonatable": d["attributes"]["can_impersonate_this_user"],
                             "set": d["relationships"]["permission_rule_set"]["data"]["id"],
                             "set_name": d["relationships"]["permission_rule_set"]["data"]["name"],
                             "projects": _link_ids(d, "projects"), "groups": _link_ids(d, "groups")}
        _lib.note_names(d["attributes"]["login"])
    for g in groups:
        d = c.get(f"/entity/groups/{g}", params={"fields": "code,users,sg_people"}).json()["data"]
        snap["groups"][g] = {"code": d["attributes"]["code"], "users": _link_ids(d, "users"),
                             "sg_people": _link_ids(d, "sg_people")}
        _lib.note_names(d["attributes"]["code"])
    return snap


def _check_aliases(c, env, snap):
    login = (env.get("FPT_USER_LOGIN") or "").strip()
    op = c.post("/entity/human_users/_search", headers=ARR, json={
        "filters": [["login", "is", login]], "fields": ["email"]}).json()["data"]
    mail = (op[0]["attributes"]["email"] or "").lower() if op else None
    for p, s in snap["people"].items():
        if not mail or (s["email"] or "").lower() != mail or s["status"] != "act" or not s["impersonatable"]:
            raise SystemExit(f"person {p} is not an active, impersonatable alias of the operator; refusing")


def set_membership(c, snap, group, person, users, sg_people):
    """Put `person` in the Group's `users` and/or `sg_people`, keeping every original member."""
    o = snap["groups"][group]

    def ids(orig, keep):
        return [_ref("HumanUser", i) for i in sorted((set(orig) - {person}) | ({person} if keep else set()))]

    return c.put(f"/entity/groups/{group}", json={"users": ids(o["users"], users),
                                                  "sg_people": ids(o["sg_people"], sg_people)})


def restore(c, snap, out=print):
    """Put every person and Group back as `snap` read them, then read back. True when all match."""
    for p, s in snap["people"].items():
        r = c.put(f"/entity/human_users/{p}", json={
            "permission_rule_set": _ref("PermissionRuleSet", s["set"]),
            "projects": [_ref("Project", i) for i in s["projects"]]})
        out(f"  restore person {p}: {said(r)}")
    for g, s in snap["groups"].items():
        r = c.put(f"/entity/groups/{g}", json={"users": [_ref("HumanUser", i) for i in s["users"]],
                                               "sg_people": [_ref("HumanUser", i) for i in s["sg_people"]]})
        out(f"  restore group {g}: {said(r)}")
    now = snapshot(c, list(snap["people"]), list(snap["groups"]))
    ok = True
    for p, s in snap["people"].items():
        n = now["people"][p]
        same = all(n[k] == s[k] for k in ("set", "projects", "groups", "status"))
        ok &= same
        out(f"  read back person {p}: permission group {n['set_name']} (was {s['set_name']}), "
            f"projects {n['projects']} (was {s['projects']}), groups {n['groups']} (was {s['groups']}), "
            f"status {n['status']} (was {s['status']}) -> {'restored' if same else 'MISMATCH'}")
    for g, s in snap["groups"].items():
        n = now["groups"][g]
        same = n["users"] == s["users"] and n["sg_people"] == s["sg_people"]
        ok &= same
        out(f"  read back group {g}: users {n['users']} (was {s['users']}), sg_people {n['sg_people']} "
            f"(was {s['sg_people']}) -> {'restored' if same else 'MISMATCH'}")
    return ok


def vendor_set(c):
    sets = c.get("/entity/permission_rule_sets", params={"fields": "code,entity_type", "page[size]": 100}).json()["data"]
    v = [s["id"] for s in sets if s["attributes"]["code"] == "vendor" and s["attributes"]["entity_type"] == "HumanUser"]
    if not v:
        raise SystemExit("no HumanUser permission group with code 'vendor' on this site")
    return v[0]


@contextmanager
def vendors(c, env, sandbox, out=print):
    """Yield [(person id, client acting as them, group id, snapshot)] for vendor A and vendor B."""
    people, groups = _ids("--people"), _ids("--groups")
    if len(people) != 2 or len(groups) != 2:
        raise SystemExit("two people and two groups")
    snap = snapshot(c, people, groups)
    _check_aliases(c, env, snap)
    out(f"  before: " + "; ".join(
        f"person {p} {s['set_name']}, projects {s['projects']}, groups {s['groups']}" for p, s in snap["people"].items())
        + "; " + "; ".join(f"group {g} users {s['users']} sg_people {s['sg_people']}" for g, s in snap["groups"].items()))
    vset = vendor_set(c)
    try:
        for p, g in zip(people, groups):
            body = {"permission_rule_set": _ref("PermissionRuleSet", vset)}
            if sandbox not in snap["people"][p]["projects"]:
                body["projects"] = [_ref("Project", i) for i in snap["people"][p]["projects"] + [sandbox]]
            r = c.put(f"/entity/human_users/{p}", json=body)
            out(f"  person {p} -> Vendor{' and the sandbox project' if 'projects' in body else ''}: {said(r)}")
            if not r.ok:
                raise SystemExit("could not re-role; nothing measured")
            r = set_membership(c, snap, g, p, users=True, sg_people=False)
            out(f"  person {p} into group {g} users: {said(r)}")
        yield [(p, FPT.from_env(env, sudo_as_login=snap["people"][p]["login"]), g, snap)
               for p, g in zip(people, groups)]
    finally:
        out("\n===== restore")
        ok = restore(c, snap, out)
        out(f"  everything as before: {ok}")
        if not ok:
            time.sleep(2)
            ok = restore(c, snap, out)
            out(f"  second restore, everything as before: {ok}")
