"""Q: when a person creates a Note and later updates it, what reaches the activity streams, does the
addressee's read state reset, and is an addressee added later made a follower?

sg-onset writes one Note per Shot at sync and updates it in place at the next sync (probe 146). Probe
067 found a Note created by the script absent from every stream, a Note created under
`sudo_as_login` on the Shot's stream within 60 s, and status changes by the script never streamed.
Nothing measured a person's `PUT` to `content` or to the addressees.

Steps, the Note written by the operator (`sudo_as_login`, probe 027), in the sandbox:

1. Shot, Task on it assigned to B (the script)
2. Note: note_links [Shot], tasks [Task], addressings_to [B]; poll the streams
3. B marks it read (probe 068)
4. `PUT content`; read B's state at once; poll the streams
5. `PUT addressings_to` add C (`multi_entity_update_mode`); C's follower and read state; poll
6. a Reply by the operator, the control that probe 067 saw stream in 33 s; poll

Streams polled: the Shot, the Note, the Task, every 15 s for up to `--wait` seconds (default 150) per
step, for rows naming the Note. B and C are test accounts sharing the operator's email (`_people`).

Writes behind `--write`: the Shot, Task, Note and Reply, deleted on exit.

    python probes/149_note_update_activity.py --write [--wait 150]
"""
import sys
import time

import _lib
import _people
from sg_groundtruth.client import FPT

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 149 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
ME, LOGIN, aliases = _people.operator_and_aliases(c, env, SB)
(B, B_LOGIN, _), (C, C_LOGIN, _) = aliases[0], aliases[1]
WAIT = int(sys.argv[sys.argv.index("--wait") + 1]) if "--wait" in sys.argv else 150
ROLE = {B: "B", C: "C", ME: "the operator"}
rows = []
U = lambda i: {"type": "HumanUser", "id": i}  # noqa: E731


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


author = FPT.from_env(env, sudo_as_login=LOGIN)
as_ = {"B": FPT.from_env(env, sudo_as_login=B_LOGIN), "C": FPT.from_env(env, sudo_as_login=C_LOGIN)}
seen = set()


def stream_rows(path, note):
    r = c.get(path, params={"limit": 50})
    if not r.ok:
        return []
    found = []
    for u in r.json()["data"]["updates"]:
        pe, meta = u.get("primary_entity") or {}, u.get("meta") or {}
        if (pe.get("type"), pe.get("id")) == ("Note", note) or (meta.get("entity_type"), meta.get("entity_id")) == ("Note", note):
            found.append(u)
    return found


def poll(streams, note, step):
    """Every row naming the Note that was not seen before, per stream, until one shows or WAIT runs out."""
    t0, new = time.time(), {}
    while time.time() - t0 < WAIT:
        for label, path in streams.items():
            for u in stream_rows(path, note):
                if (label, u["id"]) in seen:
                    continue
                seen.add((label, u["id"]))
                by = u.get("created_by") or {}
                new.setdefault(u["id"], {"t": time.time() - t0, "type": u["update_type"],
                                         "meta": {k: v for k, v in (u.get("meta") or {}).items() if k != "content"},
                                         "by": f"{by.get('type')} <{ROLE.get(by.get('id'), 'other')}>", "on": []})
                new[u["id"]]["on"].append(label)
        if new and time.time() - t0 > 40:
            break
        time.sleep(15)
    if not new:
        out(f"  {step}: nothing new on {sorted(streams)} in {WAIT} s")
    for uid, n in sorted(new.items()):
        out(f"  {step}: t+{n['t']:.0f}s {n['type']} by {n['by']} on {n['on']}, meta {n['meta']}")


def state(nid):
    f = c.get(f"/entity/notes/{nid}/followers").json()["data"]
    rs = {w: cl.get(f"/entity/notes/{nid}", params={"fields": "read_by_current_user"}).json()["data"]["attributes"]["read_by_current_user"]
          for w, cl in as_.items()}
    return f"followers {sorted(ROLE.get(x['id'], 'other') for x in f)}; read as B {rs['B']!r}, as C {rs['C']!r}"


with _lib.Created(c) as made:
    shot = made.add("shots", c.post("/entity/shots", json={"project": P, "code": "zzprobe_149_shot"}).json()["data"]["id"])
    task = made.add("tasks", c.post("/entity/tasks", json={"project": P, "content": "zzprobe_149_task",
                                                           "entity": {"type": "Shot", "id": shot},
                                                           "task_assignees": [U(B)]}).json()["data"]["id"])
    r = author.post("/entity/notes", json={"project": P, "subject": "zzprobe_149", "content": "take 1 captured",
                                           "note_links": [{"type": "Shot", "id": shot}],
                                           "tasks": [{"type": "Task", "id": task}], "addressings_to": [U(B)]})
    out(f"1. Note create, as the operator -> {said(r)}")
    note = made.add("notes", r.json()["data"]["id"])
    streams = {"Shot": f"/entity/shots/{shot}/activity_stream", "Note": f"/entity/notes/{note}/activity_stream",
               "Task": f"/entity/tasks/{task}/activity_stream"}
    out(f"   {state(note)}")
    poll(streams, note, "create")

    r = as_["B"].put(f"/entity/notes/{note}", json={"read_by_current_user": "read"})
    out(f"2. B marks it read -> {said(r)}; {state(note)}")

    r = author.put(f"/entity/notes/{note}", json={"content": "take 1 captured\ntake 2 captured"})
    out(f"3. PUT content, as the operator -> {said(r)}; at once: {state(note)}")
    poll(streams, note, "PUT content")
    out(f"   after the poll: {state(note)}")

    r = author.put(f"/entity/notes/{note}", json={"addressings_to": {"multi_entity_update_mode": "add", "value": [U(C)]}})
    out(f"4. PUT addressings_to add C, as the operator -> {said(r)}; at once: {state(note)}")
    poll(streams, note, "PUT addressings_to")
    out(f"   after the poll: {state(note)}")

    r = as_["B"].put(f"/entity/notes/{note}", json={"read_by_current_user": "read"})
    rr = author.post("/entity/replies", json={"entity": {"type": "Note", "id": note}, "content": "zzprobe_149 reply"})
    if rr.status_code == 201:
        made.rows.insert(len(made.rows), ("replies", rr.json()["data"]["id"]))
    out(f"5. B marks it read again -> {said(r)}; Reply, as the operator -> {said(rr)}; at once: {state(note)}")
    poll(streams, note, "Reply")
    out(f"   after the poll: {state(note)}")
    n = c.get(f"/entity/notes/{note}", params={"fields": "updated_by,updated_at,created_at"}).json()["data"]
    out(f"   Note updated_by {ROLE.get((n['relationships']['updated_by']['data'] or {}).get('id'), 'other')}")
    _lib.emit("149_note_update_activity", "\n".join(rows), env)
