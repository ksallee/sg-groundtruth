---
intent: Keep one Note per Shot, addressed to the people on the Shot's Tasks, found again by a client key and updated in place
tags: [note, task, idempotency, jsonb, follow]
endpoints: [POST /entity/<type>/_search, GET /entity/<type>/<id>, POST /entity/<type>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>/followers]
scope: api
measured: sandbox project written, 2026-11-17; Notes, a Group, Shots and Tasks made and deleted (probes 146 to 150)
coverage: partial
unmeasured: the Inbox the addressees see, and a launcher bearer as the writer. Needs a browser and a person (probes 147, 148, 149)
---

# 026_note_per_shot

Write as the person (a launcher bearer, probe 052, or `sudo_as_login`): a script's Note create was
absent from every stream after 430 s (probe 067). Key the Note on a client UUID in `meta`, which needs no schema change (probe 146).
Expand Group assignees before addressing (probe 150).

## Call

```python
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


def assignees(c, shot_id):
    """The people on a Shot's Tasks. A Group assignee is stored as the Group (probe 150)."""
    rows = c.post("/entity/tasks/_search", headers=ARR, json={
        "filters": [["entity", "is", {"type": "Shot", "id": shot_id}]],
        "fields": ["task_assignees"], "page": {"size": 500}}).json()["data"]
    people, groups, tasks = set(), set(), []
    for t in rows:
        tasks.append({"type": "Task", "id": t["id"]})
        for a in t["relationships"]["task_assignees"]["data"] or []:
            (people if a["type"] == "HumanUser" else groups).add(a["id"])
    for g in groups:
        users = c.get(f"/entity/groups/{g}", params={"fields": "users"}).json()["data"]["relationships"]["users"]["data"]
        people.update(u["id"] for u in users or [])
    return [{"type": "HumanUser", "id": i} for i in sorted(people)], tasks


def find_note(c, project_id, key):
    """`contains` is case-sensitive, and nothing stops a second Note with the key (probe 146)."""
    rows = c.post("/entity/notes/_search", headers=ARR, json={
        "filters": [["project", "is", {"type": "Project", "id": project_id}],
                    ["meta", "contains", {"onset_uuid": key}]],
        "fields": ["id"], "sort": "id", "page": {"size": 5}}).json()["data"]
    return rows[0]["id"] if rows else None


def sync_note(c, project_id, shot_id, key, subject, body):
    to, tasks = assignees(c, shot_id)
    nid = find_note(c, project_id, key)
    if nid is None:
        r = c.post("/entity/notes", json={
            "project": {"type": "Project", "id": project_id}, "subject": subject, "content": body,
            "note_links": [{"type": "Shot", "id": shot_id}], "tasks": tasks, "addressings_to": to,
            "meta": {"onset_uuid": key}})            # meta is written on create only
        r.raise_for_status()
        return r.json()["data"]["id"]
    r = c.put(f"/entity/notes/{nid}", json={"content": body, "addressings_to": to})
    r.raise_for_status()
    return nid
```

## Response

```
POST /entity/notes ... meta {"onset_uuid": K}         -> 201; followers [the addressees, the writer]
["meta", "contains", {"onset_uuid": K}]               -> [that Note], for the person and the script
the same create again                                 -> 201, a second Note: look up first
PUT content                                           -> 200; addressee reads "unread" again; no stream row
PUT addressings_to += C                               -> 200; C follows at once
["task_assignees", "is", <person>]                    -> misses a Task assigned to their Group
["task_assignees.Group.users", "is", <person>]        -> finds it
```

## Notes

- A bare list on `addressings_to` replaces the set (`field_types/multi_entity`); the call sends the
  whole current list each sync. Whether someone dropped from it stops following is unmeasured; on a
  Task, a member removed from the Group kept following (probe 150).
- The create is the only stream row; edits write none (probe 149). A feed polls `updated_at`.
- For a key the server enforces, add a `unique: true` text field to Note (an administrator's call,
  probe 132) and send it on create; a duplicate is then 400 code 104 (probe 146).
