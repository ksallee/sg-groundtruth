"""Q: which streams does a Note, a Reply and a Task status change appear in, and how long after the write?

Probe 043 found three Shots absent from their own streams 90 seconds after creation, and the sandbox
Project's stream held no Note row at all although four Notes exist there. An artist page that draws
"what changed" from `activity_stream` has to know whether a Note written over REST ever appears, on
which record's stream (the Note, the Version or Shot it links, the Task in `tasks`, the Project), and
how stale the feed runs. `--write` only; every row is deleted on exit.
"""
import json
import sys
import time

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
rows = []

if not _lib.writes_allowed():
    raise SystemExit("needs --write: every step here is a mutation")
SANDBOX = _lib.sandbox_id(c, env)
login = (env.get("FPT_USER_LOGIN") or "").strip()
me = c.post("/entity/human_users/_search", headers=ARR,
            json={"filters": [["login", "is", login]], "fields": ["login"]}).json()["data"]
ME = me[0]["id"]
PATIENCE = int(next((a.split("=")[1] for a in sys.argv if a.startswith("--wait=")), "300"))


def ids(path):
    r = c.get(path, params={"limit": 50})
    if not r.ok:
        return None
    return {u["id"]: u for u in r.json()["data"]["updates"]}


pre = {
    "Project": f"/entity/projects/{SANDBOX}/activity_stream",
    "HumanUser": f"/entity/human_users/{ME}/activity_stream",
}
before = {k: set(ids(v) or {}) for k, v in pre.items()}

with _lib.Created(c) as made:
    shot = c.post("/entity/shots", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_067_shot"}).json()["data"]
    made.add("shots", shot["id"])
    task = c.post("/entity/tasks", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "content": "zzprobe_067_task",
        "entity": {"type": "Shot", "id": shot["id"]},
        "task_assignees": [{"type": "HumanUser", "id": ME}]}).json()["data"]
    made.add("tasks", task["id"])
    version = c.post("/entity/versions", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_067_v001",
        "entity": {"type": "Shot", "id": shot["id"]}, "sg_task": {"type": "Task", "id": task["id"]},
        "user": {"type": "HumanUser", "id": ME}}).json()["data"]
    made.add("versions", version["id"])
    t0 = time.time()
    rows.append(f"t+0s   created Shot {shot['id']}, Task {task['id']} assigned to the person, "
                f"Version {version['id']} on both")

    streams = {
        "Shot": f"/entity/shots/{shot['id']}/activity_stream",
        "Task": f"/entity/tasks/{task['id']}/activity_stream",
        "Version": f"/entity/versions/{version['id']}/activity_stream",
        **pre,
    }
    for k in ("Shot", "Task", "Version"):
        before[k] = set()

    note = c.post("/entity/notes", headers=JSON, json={
        "project": {"type": "Project", "id": SANDBOX}, "subject": "zzprobe_067_note",
        "content": "zzprobe 067: a note on the version, about the task, addressed to the person",
        "note_links": [{"type": "Version", "id": version["id"]}, {"type": "Shot", "id": shot["id"]}],
        "tasks": [{"type": "Task", "id": task["id"]}],
        "addressings_to": [{"type": "HumanUser", "id": ME}]}).json()["data"]
    made.add("notes", note["id"])
    streams["Note"] = f"/entity/notes/{note['id']}/activity_stream"
    before["Note"] = set()
    reply = c.post("/entity/replies", headers=JSON, json={
        "entity": {"type": "Note", "id": note["id"]}, "content": "zzprobe 067: a reply"}).json()["data"]
    made.add("replies", reply["id"])
    r = c.put(f"/entity/tasks/{task['id']}", headers=JSON, json={"sg_status_list": "ip"})
    r2 = c.put(f"/entity/versions/{version['id']}", headers=JSON, json={"sg_status_list": "rev"})
    rows.append(f"t+{time.time() - t0:.0f}s   Note {note['id']} (note_links Version+Shot, tasks Task, "
                f"addressed to the person) -> 201, Reply {reply['id']} -> 201, "
                f"Task status -> ip {r.status_code}, Version status -> rev {r2.status_code}")

    rows.append(f"\npolling every 30s for up to {PATIENCE}s; a line per stream the first time it gains rows")
    seen = {k: None for k in streams}
    deadline = t0 + PATIENCE
    while time.time() < deadline and any(v is None for v in seen.values()):
        time.sleep(30)
        for k, path in streams.items():
            if seen[k] is not None:
                continue
            now = ids(path)
            if now is None:
                rows.append(f"t+{time.time() - t0:.0f}s   {k}: stream not readable")
                seen[k] = []
                continue
            new = [now[i] for i in sorted(set(now) - before[k], reverse=True)]
            if new:
                seen[k] = new
                rows.append(f"t+{time.time() - t0:.0f}s   {k} stream: {len(new)} new rows")
                if not any(v for v in seen.values() if v):
                    pass
                if k == "Shot":
                    rows.append("           first row verbatim: " + json.dumps(new[0])[:700])
                for u in new:
                    pe = u.get("primary_entity") or {}
                    m = u["meta"] or {}
                    rows.append(f"           {u['id']} {u['update_type']:<7} {m.get('type', ''):<17} "
                                f"{pe.get('type', '')} {pe.get('id', '')}  "
                                f"{m.get('attribute_name', '')} {m.get('old_value', '')}->{m.get('new_value', '')}"
                                .rstrip())
    for k, v in seen.items():
        if v is None:
            rows.append(f"t+{time.time() - t0:.0f}s   {k} stream: nothing new after {PATIENCE}s")
    if seen.get("Note") is None or seen.get("Note") == []:
        rows.append("   the Note's own stream, verbatim: " + json.dumps(ids(streams["Note"]))[:300])
    # What the web application shows the person for this Note.
    n = c.get(f"/entity/notes/{note['id']}", params={"fields": "read_by_current_user,sg_status_list"}).json()
    rows.append(f"\nthe Note read back by the script: {json.dumps(n['data']['attributes'])}")

_lib.emit("067_notes_in_the_stream", "\n".join(rows), env)
