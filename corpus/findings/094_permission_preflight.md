---
tags: [permission, batch, sudo, task, write]
endpoints: [GET /schema/<Type>/fields, PUT /entity/<type>/<id>, POST /entity/<type>, DELETE /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 5 Shots and 1 Task, an Artist and an Admin via sudo; 47.5 s, 117 calls + 3 tokens
coverage: partial
unmeasured: a launcher session (probe 052) of a lower-level person, and the allowed side of a conditional rule (an Artist assigned to the Task); both need a person, the first at a browser
verdict: Ask with a write that cannot land: a no-op PUT per field (update), a POST with a bad status (create), a _batch of [delete, 404 sentinel] (delete). Permission is checked first, and nothing is written.
---

# 094_permission_preflight

**Q** How does a person learn, before writing anything, whether they may update Tasks, update Shots and
Assets, create Tasks and delete Tasks, and which way of asking leaves no row, no event and no
`updated_at` change?

**Endpoint** `GET /schema/<Type>/fields?project_id= ; PUT /entity/<type>/<id> ; POST /entity/<type> ; DELETE /entity/<type>/<id> ; POST /entity/_batch`

**Docs claim** Silent. No endpoint reports what the caller may do, and permission rules are not readable
(probe 027).

**Actual**

```
schema editable, sandbox project   Admin person: Task 35/56, Shot 75/100, Asset 48/72
                                   Artist: Task 2 ['sg_status_list','task_reviewers'], Shot 2, Asset 1
                                   GET /schema/Task -> ['name', 'visible'] for both
                                   Admin person                       Artist
 2 no-op PUT Task content          200                                400 The field is not editable for this user: [Task.content].
 3 no-op PUT Task sg_status_list   200                                400 ... [Task.sg_status_list]. Rule: Artist -- PermissionRule 2615:
                                                                          update_field_condition ... RULE: {"logical_operator":"and","conditions":
                                                                          [... task_assignees is logged_in_user_token, task_reviewers is ...]}
 4 no-op PUT Shot code             200                                400 ... [Shot.code].
 5 PUT Task {}                     200                                200
 6 POST Task, sg_status_list zz_bad  400 Invalid field value, ...     400 Entity of type Task cannot be created by this user.
                                   'zz_bad' is not a valid status. Valid statuses: 'wtg', 'ip', ...
 7 POST Task, unknown field        400 API create() Task.zz_no_such_field doesn't exist.   (both)
 8 DELETE Task 999999999           404 Entity of type [Task] with id=999999999 does not exist.   (both)
 9 _batch [delete Task, sentinel]  404 (the sentinel)                 400 Entity of type Task can not be deleted by this user.
10 _batch [create Task, sentinel]  404 (the sentinel)                 400 Entity of type Task cannot be created by this user.
11 _batch [PUT content new, sent.] 404 (the sentinel)                 400 ... [Task.content].
12 _batch [PUT Shot code new, s.]  404 (the sentinel)                 400 ... [Shot.code].
   sentinel = {"request_type":"update","entity":"Task","record_id":999999999,"data":{"content":"x"}}

after every call: Task and Shot updated_at unchanged, 11 events on the two rows before and after,
Shot.tasks 1, no retired Task under any Shot, live zzprobe_094 rows after exit 0
record_id 0 or -1 as the sentinel: 400 "record_id must be greater than 0", checked before request 1 runs
```

**Teaches**
- Every refusal is a 400 naming the entity or the field, checked before value validation and before the
  batch reaches its next request. An allowed caller gets the validation error or the sentinel's 404
  instead. Nothing reaches the rows either way: no updated_at bump, no EventLogEntry, no retired row.
- `properties.editable` in `GET /schema/<Type>/fields?project_id=` is per caller. `false` is a refusal
  without a write. `true` can still be refused by a conditional rule (candidate 3), so it means maybe.
- Candidates 5, 7 and 8 answer the same for both callers and test nothing: an empty PUT passes, and an
  unknown field or a missing id fails before permission is read.
- A no-op PUT tests the current value. A rule can depend on `field_value`, so test the intended value
  with a `_batch` of [the real update, sentinel] (candidate 11), which rolls back.

**Callers.** The refused person and the allowed person are the script acting through `sudo_as_login`
(probe 027), which applies that person's permission set. A person signed in with the App Session
Launcher (probe 052, recipe 012) has the same set on a `HumanUser` bearer; that session was not
measured as an Artist, because the launcher needs the person to approve at a browser.

**Precondition, declared.** The probe provisions its rows. It cannot provision the refused caller:
`can_impersonate_this_user` is not writable over REST (probe 027). Its `requires` list names an active
non-Admin HumanUser with that flag on and in the sandbox project, found by a `_search`, and the probe
exits with the list when there is none. On the probed site two Artists qualify.

**A conditional refusal prints its rule.** Probe 027 found no rule readable as a row. The 400 for a
conditional rule returns the rule id and its condition tree: on the probed site an Artist may set
`Task.sg_status_list` only where `task_assignees` or `task_reviewers` (or a Group in either) holds the
caller. An unconditional refusal names only the field.

**A late bump on a rolled-back create.** In exploratory runs of the same `_batch` [create a Task under a
Shot, sentinel] by an allowed caller, the parent Shot's `updated_at` moved a few seconds after the call
in 4 of 15 rolled-back creates, with `updated_by` unchanged, no EventLogEntry and no Task. The run above
saw none; one earlier probe run saw one. No other candidate moved a timestamp in any run. Check create
with the invalid-status POST (candidate 6), which left its parent unchanged in all 3 probe runs.

**Unmeasured.** An Artist assigned to the Task, which is the allowed side of the rule in candidate 3:
assigning a real person can notify them. Delete is checked per entity type here; a conditional delete
rule would need the same `_batch` per row. Assets were read in the schema only; the PUT candidates ran
on a Shot.
