---
endpoint: PUT /entity/<type>/<id>/_upload
tags: [storage, attachment]
scope: api
measured: sandbox project written, one Note, deleted
verdict: The fieldless `storage_service: "sg"` upload target. The spec declares only `filename` and `signature`, and the site asks for `user_id`, `user_type` and `expiration` as well.
---

# PUT /entity/<type>/<id>/_upload

The same route as `endpoints/put_entity_type_id_field_upload` with the field left out of the path:
`/entity/<type>/<id>/attachments/_upload`. It is the target `links.upload` points at when
`storage_service` is `sg`.

**Params**

| part | value |
|---|---|
| URL | `links.upload` from the fieldless init, verbatim, when `storage_service` is `sg` |
| `filename` | required |
| `signature`, `user_id`, `user_type`, `expiration` | all four required, all minted by the init |
| body | the raw bytes |

**Sample requests**

The spec lists two query parameters for this form, `filename` and `signature`. The site rejects a
call holding `filename` alone by naming four:

```python
c.put("/entity/notes/10965/attachments/_upload",
      params={"filename": "notes.pdf"}, data=b"...")
```

```json
{"errors": [{"status": 400, "code": 103, "title": "Request Parameters invalid.",
  "source": {"user_id": ["user_id is missing"], "user_type": ["user_type is missing"],
             "expiration": ["expiration is missing"], "signature": ["signature is missing"]}}]}
```

**Response codes**

| status | when |
|---|---|
| 200 | stored, with `data.upload_id` and `links.complete_upload` in the reply |
| 400 | `source` naming `signature`, `user_id`, `user_type` and `expiration` as missing |
| 404 | the record does not exist |

**Edge cases**

- The field form and this one reject an unsigned call with the identical `source`. The spec declares
  different required parameters for the two, and the site does not distinguish them.
- On the probed site `storage_service` is `s3` on every init, field form and fieldless alike, so no
  link produced here was exercisable. The 200 shape is what the spec declares, not what was measured.

**Links**

- `endpoints/put_entity_type_id_field_upload`
- `endpoints/get_entity_type_id_upload`
- `endpoints/put_links_upload`
- `endpoints/post_entity_type_id_upload`
- `findings/044_multipart_upload`