---
evidence: [findings/019_create_fields, endpoints/post_schema_type_fields]
endpoints: [POST /schema/<Type>/fields, DELETE /schema/<Type>/fields/<field>]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: site-wide, custom fields created on the Version schema and deleted
summary: Creating a custom field whose display name is taken answers 201 for a suffixed field instead of a conflict, and every retry burns a programmatic name no REST call frees.
---

# 006_duplicate_field_name_is_201

**Expected** A create that cannot produce the field the caller asked for is rejected, the way a create
against a retired name already is. The programmatic name the server derived is in the response body.

**Actual** Two creates of the same display name:

```
POST /schema/Version/fields  'zzprobe 019 collide'  -> 201  sg_zzprobe_019_collide
POST /schema/Version/fields  'zzprobe 019 collide'  -> 201  sg_zzprobe_019_collide_1
```

The second is a different field. Neither response names it: the programmatic name is absent from the
body and is only the last segment of `links.self`.

Deleting is one-way:

| call | result |
|---|---|
| `DELETE /schema/Version/fields/<name>` | `204`, and the field is absent from `/schema` |
| `GET` that field | `404` |
| create the same display name again | `400 schema_field_create() failed` |

No listing shows a retired field, so the 400 names a collision the caller cannot see and cannot resolve
over REST.

**Reproduce**

```
curl -sS -X POST "$SITE/api/v1/schema/Version/fields" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"data_type":"text","properties":[{"property_name":"name","value":"my field"}]}'
# 201. The name is only in links.self

# The identical call again
curl -sS -X POST "$SITE/api/v1/schema/Version/fields" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"data_type":"text","properties":[{"property_name":"name","value":"my field"}]}'
# 201 again, for sg_my_field_1
```

**Impact** A create that is retried, by a job that lost its response or by a client written to be
idempotent, adds a field per attempt. Each is permanent from REST: `DELETE` retires it and burns the
programmatic name, and nothing over the API lists what was burned or frees it. The recovery is a person
emptying the Trash in the web interface. An idempotent `ensure()` has to read `/schema/<Type>/fields`
and match before every write, and the response not naming the field it made is what makes even that
awkward.

**Proposed change** Answer 409 when the display name is taken, naming the existing field. Return the
derived programmatic name in the response body rather than only in `links.self`. Independently, expose
retired fields on a listing so the `schema_field_create() failed` 400 is something a caller can act on.
