---
tags: [custom-field, idempotency, create, trap]
endpoints: [POST /schema/<Type>/fields, POST /entity/<type>, DELETE /entity/<type>/<id>, POST /entity/<type>/<id>, GET /entity/<type>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2026-11-11; six rows on a custom slot, one unique text field created and retired
coverage: partial
unmeasured: uniqueness across two projects. Probes write only into the sandbox and a project entity refuses a row with no project. Blocked on the site: needs a second writable project
verdict: A deleted row frees its `unique` value: a new row may take it. Reviving the old row while another holds the value is a 400 code 104 PG transaction error, and the row stays retired.
---

# 136_unique_scope_retired

**Q** Does a `unique: true` text field's uniqueness span projects, does a deleted (retired) row keep its
value reserved, and what happens when a row is revived into a value another row now holds?

**Endpoint** `POST /entity/<type> ; DELETE /entity/<type>/<id> ; POST /entity/<type>/<id>?revive=true`

**Docs claim** Silent. Probe 127 found a `unique` text field refuses a second create.

**Actual**

```
1. across projects
  A with K, in the sandbox         -> 201
  B with K, no project             -> 400 code 103 "API create() missing 'project' attribute: {...}"
  B without K, no project          -> 400, the same: a project entity takes no project-less row

2. a deleted row's value
  delete A                         -> 204
  GET ?options[return_only]=retired&filter[id]=A  -> A, still holding K
  C with K                         -> 201; live rows holding K: [C]
  delete C, then D with K          -> 201

3. revive A while D holds K
  POST /entity/<slot>/A?revive=true -> 400 {"code": 104, "title": "Revive failed for [CustomEntityNN
      with id=<A>]: PG::InFailedSqlTransaction: ERROR:  current transaction is aborted, commands
      ignored until end of transaction block\n: SELECT a.attname, format_type(...) ..."}
  A stays retired; live rows holding K: [D]
  delete D; revive C, nothing live holds K -> 200
  E with K                         -> 400 code 104 "Create failed for [CustomEntityNN]: The value for
                                      the zzprobe 136 key field is required to be unique. <br> "
```

**Teaches**

| row state | holds K for uniqueness |
|---|---|
| live | yes: a create with K is 400 code 104 |
| retired (deleted) | no: a create with K is 201, and the retired row still stores K |
| revived while a live row holds K | the revive fails, 400 code 104, row stays retired |
| revived while nothing holds K | 200; the row holds K again and blocks the next create |

- A lookup by key must search live rows only (the default) and treat a retired match as absent. A
  client that undoes a delete by reviving must expect the revive to fail when the key was reused,
  and the error names a Postgres transaction, not uniqueness.
- The duplicate refusal names the field's display name, not its `sg_` name, and ends in `<br> `.
- Whether two projects can hold the same value is unmeasured. The refusal says "required to be
  unique" and names no scope; key on a value that is unique across the site (a UUID) and the
  question does not arise.
