"""Q: what does putting a HumanUser or a Group in a Note's `addressings_to` or `addressings_cc` do for
the people named: do they follow it, can they read it, can they find it, and does it reach their Inbox?

sg-onset addresses its Shot Note to the people assigned to the Shot's Tasks, and an assignee may be a
Group (probe 150). The Inbox has no REST call: probe 066 found a HumanUser's activity stream is what
the person created. What the API can show is the Note's followers (`GET /entity/notes/<id>/followers`),
each person's `read_by_current_user` (probe 068) and the filters a client would run for "Notes to me".

Written by the operator (`sudo_as_login`, probe 027), in the sandbox, one Note each:

    to B          addressings_to [B]
    cc B          addressings_cc [B]
    to the group  addressings_to [a Group of B and C]
    none          no addressee, the control

B and C are test accounts sharing the operator's email (`_people`). For each Note, the followers;
then as B and as C, the Note's `read_by_current_user` and the filters below.

`--hold <seconds>` keeps every row alive that long before cleanup, so a person can open B's and C's
Inbox in a browser (see the finding).

Writes behind `--write`: a Group (site-wide), the Notes, all deleted on exit.

    python probes/147_note_addressing.py --write [--hold 900]
"""
import sys
import time

import _lib
import _people
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 147 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
ME, LOGIN, aliases = _people.operator_and_aliases(c, env, SB)
(B, B_LOGIN, B_GROUP), (C, C_LOGIN, C_GROUP) = aliases[0], aliases[1]
HOLD = int(sys.argv[sys.argv.index("--hold") + 1]) if "--hold" in sys.argv else 0
rows = []
ROLE = {B: "B", C: "C", ME: "the operator"}


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
        return f"{r.status_code} {r.text}"


author = FPT.from_env(env, sudo_as_login=LOGIN)
as_ = {"B": FPT.from_env(env, sudo_as_login=B_LOGIN), "C": FPT.from_env(env, sudo_as_login=C_LOGIN)}
U = lambda i: {"type": "HumanUser", "id": i}  # noqa: E731

with _lib.Created(c) as made:
    G = made.add("groups", c.post("/entity/groups", json={"code": "zzprobe_147_group",
                                                          "users": [U(B), U(C)]}).json()["data"]["id"])
    GR = {"type": "Group", "id": G}
    out(f"B is {B_GROUP}, C is {C_GROUP}; the group holds B and C")
    notes = {}
    for label, extra in (("to B", {"addressings_to": [U(B)]}),
                         ("cc B", {"addressings_cc": [U(B)]}),
                         ("to the group", {"addressings_to": [GR]}),
                         ("none", {})):
        r = author.post("/entity/notes", json={"project": P, "subject": f"zzprobe_147 {label}",
                                               "content": "zzprobe_147", **extra})
        out(f"POST /entity/notes {label}, as the operator -> {said(r)}")
        if r.status_code == 201:
            notes[label] = made.add("notes", r.json()["data"]["id"])
    n0 = c.get(f"/entity/notes/{notes['to the group']}", params={"fields": "addressings_to,suppress_email_notif"}).json()["data"]
    out(f"  'to the group' reads back addressings_to "
        f"{[(x['type'], 'the group' if x['id'] == G else x['id']) for x in n0['relationships']['addressings_to']['data']]}, "
        f"suppress_email_notif {n0['attributes'].get('suppress_email_notif')!r}")

    time.sleep(5)
    out("\n===== followers, read state")
    for label, nid in notes.items():
        f = c.get(f"/entity/notes/{nid}/followers").json()["data"]
        st = {}
        for who, cl in as_.items():
            r = cl.get(f"/entity/notes/{nid}", params={"fields": "read_by_current_user"})
            st[who] = r.json()["data"]["attributes"]["read_by_current_user"] if r.ok else said(r)
        out(f"  {label:13} followers {sorted(ROLE.get(x['id'], 'other') for x in f)}; read as B {st['B']!r}, as C {st['C']!r}")

    out("\n===== the filters a client runs for 'Notes to me', as each person")
    for who, cl in as_.items():
        me = U(B if who == "B" else C)
        for v, flt in (("addressings_to is me", ["addressings_to", "is", me]),
                       ("addressings_cc is me", ["addressings_cc", "is", me]),
                       ("addressings_to.Group.users is me", ["addressings_to.Group.users", "is", me]),
                       ("addressings_to.HumanUser.id is my id", ["addressings_to.HumanUser.id", "is", me["id"]])):
            r = cl.post("/entity/notes/_search", headers=ARR, json={
                "filters": [["project", "is", P], ["subject", "starts_with", "zzprobe_147"], flt],
                "fields": ["subject"]})
            got = sorted(x["attributes"]["subject"].replace("zzprobe_147 ", "") for x in r.json()["data"]) if r.ok else said(r)
            out(f"  as {who}: {v} -> {got}")

    if HOLD:
        out(f"\nholding {HOLD} s: open B's and C's Inbox now")
        print(f"note ids {notes}", flush=True)
        time.sleep(HOLD)
    _lib.emit("147_note_addressing", "\n".join(rows), env)
