---
intent: Learn whether the signed-in person may update, create or delete a type before writing, with calls that change nothing
tags: [permission, batch, task, write]
endpoints: [GET /schema/<Type>/fields, GET /entity/<type>/<id>, PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/_batch]
scope: api
measured: sandbox project written, an Artist and an Admin via sudo_as_login, 1 Shot and 1 Task made and deleted
---

# 0XX_check_permission_before_writing

No endpoint reports what a caller may do (probe 027), so ask with a write the server refuses before it
lands. Permission is checked first; an allowed caller gets a different error, and nothing is written
(probe 094). Works on any client: a script acting through `sudo_as_login`, or a person's bearer from the
App Session Launcher (recipe 012).

## Call

```python
import json

SENTINEL_ID = 999999999   # a Task id that does not exist; the check below refuses to run otherwise


def first_error(r):
    return r.json()["errors"][0]["title"] if not r.ok else None


def editable_fields(c, entity_type, project_id):
    """Fields this caller may never write (False) or may write, possibly under a condition (True)."""
    d = c.get(f"/schema/{entity_type}/fields", params={"project_id": project_id}).json()["data"]
    return {k: v["editable"]["value"] for k, v in d.items()}


def can_update(c, slug, row_id, fields):
    """No-op PUT: write each field's current value back. 200 changes nothing (no event, no updated_at)."""
    cur = c.get(f"/entity/{slug}/{row_id}", params={"fields": ",".join(fields)}).json()["data"]
    body = {f: cur["attributes"][f] if f in cur["attributes"] else cur["relationships"][f]["data"]
            for f in fields}
    r = c.put(f"/entity/{slug}/{row_id}", json=body)
    return r.ok, first_error(r)


def _rolled_back(c, request):
    """Run `request` in a _batch whose second request fails, so the batch rolls back (recipe 002)."""
    if c.get(f"/entity/tasks/{SENTINEL_ID}").status_code != 404:
        raise SystemExit("sentinel id exists; pick another")
    sentinel = {"request_type": "update", "entity": "Task", "record_id": SENTINEL_ID,
                "data": {"content": "x"}}
    r = c.post("/entity/_batch", json={"requests": [request, sentinel]})
    if r.ok:
        raise SystemExit("batch committed: " + json.dumps(r.json()))   # cannot happen with a 404 sentinel
    detail = r.json()["errors"][0].get("detail") or ""
    return f"id={SENTINEL_ID} does not exist" in detail, first_error(r)


def can_update_to(c, entity_type, row_id, values):
    """The intended values, for rules that depend on the value written."""
    return _rolled_back(c, {"request_type": "update", "entity": entity_type, "record_id": row_id,
                            "data": values})


def can_create_task(c, project_id, entity):
    """A create with an invalid status: refused on permission first, else on the status."""
    r = c.post("/entity/tasks", json={"project": {"type": "Project", "id": project_id},
                                      "entity": entity, "content": "permission check",
                                      "sg_status_list": "zz_not_a_status"})
    err = first_error(r) or ""
    return "is not a valid status" in err, err


def can_delete(c, entity_type, row_id):
    return _rolled_back(c, {"request_type": "delete", "entity": entity_type, "record_id": row_id})
```

## Response

```
                                     Admin person          Artist
editable_fields Task, True           35 of 56              ['sg_status_list', 'task_reviewers']
can_update tasks content             (True, None)          (False, 'The field is not editable for this user: [Task.content].')
can_update shots code                (True, None)          (False, 'The field is not editable for this user: [Shot.code].')
can_update_to Task content           (True, 'Not Found')   (False, 'The field is not editable for this user: [Task.content].')
can_create_task                      (True, "Invalid field value, update failed [5 - ... 'zz_not_a_status'
                                            is not a valid status. Valid statuses: 'wtg', 'ip', ...]")
                                                           (False, 'Entity of type Task cannot be created by this user.')
can_delete Task                      (True, 'Not Found')   (False, 'Entity of type Task can not be deleted by this user.')
```

## Notes

- `editable` `False` in the schema is a refusal without a write, and one call covers every field. `True`
  can still be refused by a conditional rule, such as an Artist setting `sg_status_list` on a Task
  they are not assigned to; the 400 then prints the rule's condition tree (probe 094).
- The no-op PUT and the rolled-back update test different things: the first the current value, the
  second the value about to be written. Use `can_update_to` when a rule may depend on the value.
- Check create with the invalid status, not with a rolled-back batch create: that one moved the parent
  Shot's `updated_at` a few seconds later in 4 of 15 tries, with no event (probe 094).
- An empty PUT (`{}`), an unknown field and a missing id test nothing: the first passes for everyone,
  the other two fail before permission is read.
- `record_id` 0 or negative is rejected before the first request runs, so it cannot be the sentinel.
