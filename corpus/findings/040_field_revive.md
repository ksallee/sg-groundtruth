---
tags: [schema, custom-field, create, error-handling, trap, discovery]
scope: api
measured: site-wide, two field names created, trashed, revived and re-trashed on Version; both spent forever
verdict: A trashed field is revived by POST /schema/<Type>/fields/<name> with {"revive": true} at 204, but it returns at its original data_type, and a PUT changing data_type is a 200 that does nothing.
---

# 040_field_revive

**Q** What happens when you create a field whose display name belongs to a trashed field, and can the
trashed one be recovered?

**Endpoint** `POST /schema/<Type>/fields ; POST /schema/<Type>/fields/<name> ; PUT /schema/<Type>/fields/<name>`

**Docs claim** Nothing. The revive call appears in no documentation; the API names it in a 400.

**Actual**

Create, trash, and the field is gone from `/schema`:

```
POST /schema/Version/fields  name='zzprobe 040 revive' data_type=text -> 201
  programmatic name, from the last segment of links.self: sg_zzprobe_040_revive
DELETE /schema/Version/fields/sg_zzprobe_040_revive -> 204
  visible in /schema: False
```

Creating the same display name again, at `text` or at `number`, is the identical 400:

```
400 API schema_field_create() failed, there is a retired field with the same field_name:
    sg_zzprobe_040_revive. Delete the retired field forever from the Trash Page in Shotgun
    and try again.
```

The data type is irrelevant. The collision is on the programmatic name alone.

**The revive call, which the API names itself**

`POST` to the field's own path with an empty body returns a 400 that gives the parameter away:

```
POST /schema/Version/fields/sg_zzprobe_040_revive  {} -> 400
  source: {"revive": ["revive is missing"]}
```

```
POST /schema/Version/fields/sg_zzprobe_040_revive  {"revive": true} -> 204
  body: empty
  visible in /schema afterwards: True
  data_type: text        name: zzprobe 040 revive
```

It comes back at the type it had, not the type you wanted.

**The type cannot be changed, and one route says so quietly**

| sent | result |
|---|---|
| `PUT` with `data_type` inside `properties` | `400 API schema_field_update() invalid property 'data_type'` |
| `PUT` with `data_type` at the top level | **`200`, and `data_type` is unchanged** |

`data_type` reads `editable: false`. What is editable on a custom field is `name`, `description`,
`custom_metadata` and `visible`, and nothing else.

The top-level `PUT` is the trap: it returns the whole field, at 200, with the old type still in it. A
client that sends the change and does not compare the response believes it worked.

**The sequence a client has to implement**

| step | call |
|---|---|
| 1 | `GET /schema/<Type>/fields`, match on the programmatic name before writing anything |
| 2 | create. A 400 naming a retired field means the name is taken by something unlistable |
| 3 | `POST /schema/<Type>/fields/<name>` with `{"revive": true}` |
| 4 | read the revived field's `data_type` |
| 5 | if it is the type you wanted, you are done |
| 6 | if it is not, `DELETE` it again and tell the caller they cannot have that programmatic name |

Step 6 is where a client has to give up. There is no path from a trashed `text` field to a live `number`
field of the same name, so code that needs a specific programmatic name reports failure rather than
working around it.

**Where a trashed field is visible**

Nowhere.

| listing | status | trashed field present | fields returned |
|---|---|---|---|
| plain | 200 | no | 71 |
| `options[retired_only]=true` | 200 | no | 71 |
| `options[return_only]=retired` | 200 | no | 71 |

Both option spellings return the identical 71 live fields. `GET /schema/<Type>/fields/<name>` on a
trashed field is a 404 reading `Field 'Version.<name>' does not exist`, which is the only way to ask
whether a name is taken, and it does not distinguish "trashed" from "never existed".

**Teaches**

| do | why |
|---|---|
| Read the schema and match before creating | a trashed name is unlistable, so the collision is unpredictable otherwise |
| Revive with `POST <field path>` and `{"revive": true}` | it is a 204 and it is in no documentation |
| Read `data_type` back after reviving | it returns at its original type, whatever you asked for |
| Never trust a `PUT` that changes `data_type` | the top-level form is a 200 that does nothing |
| Give up on the name when the type is wrong | nothing converts a trashed field to another type |
| Never create a field to test with | the name is spent whether you trash it, revive it or re-trash it |

The quiet neighbour is worse still. A duplicate of a **live** field does not error: it silently becomes
`<name>_1` (probe 019). A create returns 201 both when it did what you meant and when your code now
writes to a field that is not the one you asked for.
