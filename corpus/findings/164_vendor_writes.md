---
tags: [permission, sudo, custom-entity, batch, write]
endpoints: [POST /entity/<type>, POST /entity/_batch, PUT /entity/<type>/<id>, DELETE /entity/<type>/<id>, GET /schema/<Type>/fields, GET /schema/permission_groups/<code>/entity_types/<Type>/fields]
phase: write
scope: api
measured: sandbox project written, 2026-11-20; a Bid, a Bid Line and a Shot; one person re-roled to Vendor via sudo, restored
verdict: On the probed site a Vendor creates no Bid or Bid Line, by POST or `_batch`, and updates only `sg_status_list`, each refusal 400 code 104. Both preflight reads predicted every answer.
---

# 164_vendor_writes

**Q** Can a person in the Vendor group create or update a row of a custom entity, and which fields?

**Endpoint** `POST /entity/<type> ; POST /entity/_batch ; PUT /entity/<type>/<id> ; DELETE /entity/<type>/<id>`

**Docs claim** Silent. Probe 143 measured an Artist and read Vendor's rights without exercising them.

**Actual**

```
as vendor A, on a Bid and a Bid Line the script made for group A (both slots answered alike)
  GET /schema/<Type>/fields?project_id=<sandbox>, editable for the vendor  ['sg_status_list']
  GET /schema/permission_groups/vendor/entity_types/<Type>/fields, update not denied  ['sg_status_list']

  POST create                 -> 400 code 104 "Entity of type CustomEntityNN cannot be created by this user."
  _batch [create]             -> 400 code 104, the same title
  PUT code                    -> 400 code 104 "The field is not editable for this user: [CustomEntityNN.code]."
  PUT description             -> 400 code 104, the same, [CustomEntityNN.description]
  PUT sg_status_list null     -> 200
  PUT the vendor groups field -> 400 code 104, the same, naming the field
  PUT the currency amount     -> 400 code 104, the same, naming the field
  PUT the Shot and Bid links  -> 400 code 104, the same, naming each field
  DELETE                      -> 400 code 104 "Entity of type CustomEntityNN can not be deleted by this user."
                                 GET as the script after -> 200
```

**Teaches**
- A Vendor on the probed site cannot enter a bid: no row can be created and no amount written, on a
  row assigned to their own Group as on any other. `_batch` is refused like a single `POST`; it skips
  validation (probe 137), not permission.
- The refusal is checked before anything is written and names the type or the field (probe 094). An
  app reads it in advance from either call above; both listed exactly the one field that took a write.
- For vendors to enter their own lines, the site gives Vendor create on Bid Line and update on the
  amount, ideally conditional on the Bid's Group, in the web interface (probe 162). Otherwise the app
  writes through a script after checking who is asking, and the row's `created_by` is the script.
