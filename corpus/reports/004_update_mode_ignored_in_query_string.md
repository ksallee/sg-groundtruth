---
evidence: [findings/field_types/multi_entity, recipes/009_multi_entity_safely, findings/028_loud_and_silent]
endpoints: [PUT /entity/<type>/<id>]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: sandbox project, one multi_entity field written and restored
summary: multi_entity_update_mode sent as a query parameter is accepted and ignored, and the whole link set is replaced when the caller asked to add.
---

# 004_update_mode_ignored_in_query_string

**Expected** A request naming an update mode either applies it or is rejected. A parameter the server
does not act on does not silently change a write from `add` to `replace`.

**Actual** Starting from a `multi_entity` field holding `[A]` and asking to add `[B]`:

| how the mode was sent | answer | field afterwards |
|---|---|---|
| in the body, `{"multi_entity_update_mode": "add", "value": [B]}` | `200` | `[A, B]` |
| `?multi_entity_update_mode=add` in the query string | `200` | `[B]`, `A` gone |
| `?options[multi_entity_update_modes][field]=add` in the query string | `200` | `[B]`, `A` gone |

Both query-string spellings answer `200` and neither takes effect. A bare list is a replace, so the
ignored parameter turns an add into the destruction of every link the caller did not name. Nothing in
the response distinguishes the three rows above.

**Reproduce**

```
# Seed the field with one link, then ask to add a second through the query string
curl -sS -X PUT "$SITE/api/v1/entity/versions/<id>?multi_entity_update_mode=add" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"sg_ai_generated_from":[{"type":"Version","id":<B>}]}'
# 200

curl -sS "$SITE/api/v1/entity/versions/<id>?fields=sg_ai_generated_from" \
  -H "Authorization: Bearer $TOKEN"
# the field holds [B] alone. A is gone

# The same intent in the body keeps both
curl -sS -X PUT "$SITE/api/v1/entity/versions/<id>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"sg_ai_generated_from":{"multi_entity_update_mode":"add","value":[{"type":"Version","id":<B>}]}}'
```

**Impact** A client that reaches for the query-string form loses every existing link on the field and is
told the write succeeded. The loss is silent at write time and is found later by whoever notices the
links are missing, with a `200` in the log. The body form working is what makes this a trap rather than
a missing feature: the parameter name is right and the server knows it in one place.

**Proposed change** Reject an update mode sent as a query parameter with a 400 naming the body form, or
honour it. Either is safe; accepting it at 200 and replacing the list is not.
