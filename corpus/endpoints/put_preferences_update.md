---
endpoint: PUT /preferences/update
tags: [custom-entity, write, error-handling, permission]
scope: api
measured: site-wide, rejections only
verdict: Enables a custom entity slot and nothing else. On the probed site every body, valid or not, answered 400 code 111 `Updating the preferences is not available`, so the shape stays unverified.
---

# PUT /preferences/update

Enables a `CustomEntityNN` or `CustomNonProjectEntityNN` slot and gives it a display name. Despite
the name it does not write the preferences `GET /preferences` reads; there is no write path for
those.

**Params**

| part | value |
|---|---|
| body `preference` | required. `enable_entity` is the only operation `/spec.json` names |
| body `entity_type` | required. Singular CamelCase, `CustomNonProjectEntity01` |
| body `display_name` | optional. What the site shows for the slot |
| body | may also be an array of such objects, to enable several at once |
| `Content-Type` | `application/json` |

**Sample requests**

An empty body:

```python
r = c.put("/preferences/update", json={})
```

```json
[{"id": "dd6e310016e15c550a726f8a8f5e24bf", "status": 400, "code": 111,
  "title": "Updating the preferences is not available", "source": null, "detail": null,
  "meta": null}]
```

A well-formed body naming an entity type that does not exist:

```python
r = c.put("/preferences/update",
          json={"preference": "enable_entity", "entity_type": "NotAnEntityType"})
```

```json
[{"id": "c608c8307c9500ffdc27375223b7df3f", "status": 400, "code": 111,
  "title": "Updating the preferences is not available", "source": null, "detail": null,
  "meta": null}]
```

On the probed site all six bodies tried, from `{}` to a complete one, answered the same 170 bytes.

| body | status | title |
|---|---|---|
| `{}` | 400 | `Updating the preferences is not available` |
| `{"preference": "enable_entity"}` | 400 | same |
| `{"entity_type": "NotAnEntityType"}` | 400 | same |
| `{"preference": "definitely_not_a_preference", "entity_type": "NotAnEntityType"}` | 400 | same |
| `{"preference": "enable_entity", "entity_type": "NotAnEntityType"}` | 400 | same |
| `[]` | 400 | same |

**Response codes**

| status | when |
|---|---|
| 200 | `/spec.json` says the preference was updated. Not reached on the probed site |
| 400 | code 111, `Updating the preferences is not available` |
| 401 | `Request rejected due to invalid credentials.` |
| 404 | `Record does not exist.` |

**Edge cases**

- **The success path is deliberately unexercised.** Enabling a custom entity slot changes the schema
  of the whole site for every user and cannot be undone by this endpoint: `/spec.json` names no
  `disable_entity`. Only rejections were sent.
- The 400 precedes validation. An empty body and a complete one get the same status, the same
  code and the same string, so the error says nothing about whether the body was right. A client
  cannot use it to test its own payload.
- `code` is 111 and `source` is `null`, where the parameter errors elsewhere in the API report 103
  with a populated `source`. Read `code`, not the status.
- The refusal is a 400, not a 403. Whatever gates this call, it is not reported as an authorisation
  failure, so retrying with different credentials is not indicated by the response.
- Enabling a slot is site configuration. Read which slots are already enabled with
  `PYTHONPATH=src python -m sg_groundtruth.schema entities --custom` rather than probing for them.

**Links**

- `endpoints/get_preferences`
- `endpoints/get_schema`
- `findings/008_custom_entities`
- `findings/047_site_facts_and_the_working_week`