---
endpoint: GET /entity/<type>/<id>/relationships/<related_field>
tags: [entity-field, multi-entity, cost]
scope: api
measured: sample project 1 of 1, read only
verdict: The `entity` or `multi_entity` link list on its own, unpaged and unsorted. `page`, `fields` and `sort` are accepted and ignored, and every link is returned in one body.
---

# GET /entity/<type>/<id>/relationships/<related_field>

**Params**

| part | value |
|---|---|
| `<related_field>` | an `entity` or `multi_entity` field. Anything else is a 400 |
| `page[size]`, `page[number]` | accepted and ignored |
| `fields` | accepted and ignored. Links are always `{id, name, type}` |
| `sort` | accepted and ignored |
| `options[return_only]` | `retired` looks up the owning row, not the links |

**Sample requests**

```python
c.get("/entity/versions/17055/relationships/entity").json()
```

```json
{"data": {"id": 1230, "name": "charA", "type": "Asset"},
 "links": {"self": "/api/v1/entity/versions/17055/relationships/entity"}}
```

A `multi_entity` field answers a list, and an unset one answers `[]`:

```json
{"data": [], "links": {"self": "/api/v1/entity/versions/17055/relationships/playlists"}}
```

Sixty links, and paging asked for anyway:

```python
r = c.get("/entity/assets/1300/relationships/shots", params={"page[size]": 2})
len(r.json()["data"]), r.json()["links"]
# 60, {'self': '/api/v1/entity/assets/1300/relationships/shots'}
```

A field that is not a link:

```json
{"errors": [{"status": 400, "code": 103,
             "title": "Field 'code' is not a relationship field",
             "source": {"related_field": [" is not an Entity or Multi Entity field."]}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | the link or links, `[]` when unset |
| 400 | `Field 'code' is not a relationship field`, for a non-link field |
| 404 | `Field 'Version.sg_not_a_field' does not exist.`, code 103 |
| 404 | `Asset: 1300 not found`, code 103, under `options[return_only]=retired` on a live row |

**Edge cases**

| you send | result |
|---|---|
| `page[size]=2` on a 60-link field | 200, all 60 rows |
| `page[number]=2` | 200, the same 60 rows |
| `fields=code` | ignored, links stay `{id, name, type}` |
| `sort=code` | ignored, source order kept |
| an `image` field | 400 `is not a relationship field` |

- `data` is byte-identical to what `GET /entity/<type>/<id>?fields=<field>` returns under
  `relationships`, in the same order, minus the `links.related` pointer to the linked row.
- There is no `links.next` and no measured page cap. The whole link list is in the one response.
- The saving is small: on the probed site 120 bytes against 353 for a single link, and 3048 against
  3231 for 60. Call it when the link list is the entire request, not to trim a read you are making
  anyway.
- `options[return_only]=retired` is evaluated against the owning record, so it 404s on a live row
  rather than filtering the links.
- `GET` is the only verb. `POST` and `DELETE` on this path are 404 (`field_types/multi_entity`); edit
  links with `PUT /entity/<type>/<id>`.

**Links**

- `endpoints/get_entity_type_id`
- `endpoints/put_entity_type_id`
- `field_types/entity`
- `field_types/multi_entity`
- `recipes/009_multi_entity_safely`
