---
tags: [event-log, permission, write, silent, trap, observe, auth]
endpoints: [POST /entity/<type>/_search, POST /entity/<type>, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, GET /schema/<Type>/fields/<field>, PUT /entity/<type>/<id>]
phase: observe
scope: api
measured: sandbox project written, one Shot created, updated and deleted
verdict: A script's writes reach the event log only while its ApiUser has generate_event_log_entries True. The default is False and nothing errors when off. One create logs one row per field plus one _New.
---

# 049_script_events

**Q** Does this script's own write reach the event log, and what does one write put there?

**Endpoint** `POST /entity/shots ; PUT /entity/shots/<id> ; DELETE /entity/shots/<id> ; POST /entity/event_log_entries/_search`

**Docs claim** The REST reference does not mention `generate_event_log_entries`, and documents
`EventLogEntry` as an ordinary entity type. Nothing in the REST surface says a script's own writes can
be absent from the log.

**Actual**

```
GET /schema/ApiUser/fields/generate_event_log_entries -> 200   default_value False
POST /entity/api_users/_search on its own name        -> 200   generate_event_log_entries=True
PUT /entity/api_users/<own id> {"generate_event_log_entries": True} -> 200   a script can set its own

create: POST /entity/shots, 4 keys sent -> 6 rows, first visible after 0.4s
  Shotgun_Shot_Change  attribute='description'             in_create=True  None -> 'probe 049'
  Shotgun_Shot_Change  attribute='sg_shot_type'            in_create=True  None -> 'VFX'
  Shotgun_Shot_Change  attribute='sg_status_list'          in_create=True  None -> 'wtg'
  Shotgun_Shot_Change  attribute='sg_latest_vendor_status' in_create=True  None -> 'wtg'
  Shotgun_Shot_Change  attribute='code'                    in_create=True  None -> 'zzprobe_049_shot'
  Shotgun_Shot_New     attribute=None   meta.type='new_entity'
  every row: user=<script> 1.0 /ApiUser, session_uuid=None, entity=Shot:<id>

update: PUT sg_status_list 'wtg' -> 'ip'  -> 1 row after 0.3s
delete: DELETE                            -> 2 rows
  Shotgun_Shot_Retirement  meta.type='entity_retirement'
    meta keys: class_name, display_name, entity_id, entity_type, id, retirement_date, type
  Shotgun_Shot_Change      attribute='retirement_date'  None -> '2026-09-04 17:42:34 UTC'

filtering on entity after the delete -> 0 rows (was 7); found by meta.entity_id -> 9
total for one create + one update + one delete: 9 events
```

**Teaches**

- **`generate_event_log_entries` on the ApiUser gates the whole feed, and its default is `False`.**
  While it is off the write still answers 201, the log stays empty, and any webhook scoped to that
  change has nothing to fire on. Nothing errors, so a client cannot detect it from the response. Read
  the flag before concluding the API does not log an operation.
- **A script can read and set its own flag.** `PUT /entity/api_users/<own id>` with
  `{"generate_event_log_entries": true}` answers 200. Turning it on is a one-call fix; it also means a
  compromised script key can switch its own audit trail off.
- **One create costs one row per populated field plus one `_New`.** Four keys sent produced five
  `Shotgun_<Type>_Change` rows, because server-set defaults are logged too, and each sets
  `in_create: true`. A consumer counting operations must not count events.
- Events are visible 0.3s to 0.4s after the call. There is no lag to design around at this size.
- `session_uuid` is null on every row this script generated, and set on the rows the web interface
  generated. It does not group a script's calls into a session.
- **A delete logs two rows and orphans all the others in the same instant.** `Shotgun_<Type>_Retirement`
  puts `retirement_date` and `display_name` in `meta`, and every earlier row for that entity drops
  its `entity` link at once, so the history is reachable only through `meta.entity_id`, which is
  unfilterable (probe 025). Capture the id before deleting or lose the trail.

**Python equivalent**

```python
# probe 049: is this script even logging? check before trusting an empty feed
me = sg.find_one("ApiUser", [["firstname", "is", SCRIPT_NAME]], ["generate_event_log_entries"])
if not me["generate_event_log_entries"]:
    sg.update("ApiUser", me["id"], {"generate_event_log_entries": True})
```
