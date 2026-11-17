---
intent: Create rows from a client that retries after timeouts, without duplicating any row
tags: [create, batch, custom-field, idempotency]
endpoints: [POST /schema/<Type>/fields, POST /entity/<type>, POST /entity/_batch, POST /entity/<type>/_search]
scope: api
measured: sandbox project written, 2026-11-11; 25 Versions made and deleted, one unique text field created and retired
coverage: partial
unmeasured: whether `unique` spans projects and whether deleting a row frees its value (probe 127). Blocked on the work
---

# 025_retry_safe_create

A timed-out create may have committed (probe 127, recipe 002) and the API ignores idempotency
headers. Give every row a client UUID in a text field created with `unique: true`; the server then
refuses the duplicate, and the client reads the row it already made.

## Call

```python
import uuid

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


def add_uuid_field(c, entity_type, display="Client UUID"):
    """Once per type, by an admin script. `unique` is accepted at create only (probe 116)."""
    r = c.post(f"/schema/{entity_type}/fields", json={"data_type": "text", "properties": [
        {"property_name": "name", "value": display},
        {"property_name": "unique", "value": True}]})
    r.raise_for_status()
    return r.json()["links"]["self"].rsplit("/", 1)[-1]          # e.g. sg_client_uuid


def find_by_uuid(c, slug, field, value):
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json={
        "filters": [[field, "is", value]], "fields": ["id"], "page": {"size": 2}})
    data = r.json()["data"]
    return data[0]["id"] if data else None


def create_once(c, slug, field, body, client_uuid=None):
    """Same client_uuid on every retry. Returns (id, created_now)."""
    client_uuid = client_uuid or str(uuid.uuid4())
    try:
        r = c.post(f"/entity/{slug}", json={**body, field: client_uuid})
    except Exception:                       # a timeout: the row may exist
        found = find_by_uuid(c, slug, field, client_uuid)
        if found:
            return found, False
        raise
    if r.status_code == 201:
        return r.json()["data"]["id"], True
    err = (r.json().get("errors") or [{}])[0]
    if err.get("code") == 104 and "required to be unique" in err.get("title", ""):
        return find_by_uuid(c, slug, field, client_uuid), False
    r.raise_for_status()
```

## Response

```
create with <uuid>                 -> 201
the same create again              -> 400 code 104 "Create failed for [Version]: The value for the
                                      zzprobe 127 client uuid field is required to be unique. <br> "
<uuid> uppercased, or " " + <uuid> -> 400, the same
POST /entity/_batch with <uuid>    -> 400, the same, nothing in the batch committed
["<field>", "is", <uuid>]          -> 1 row, straight after the 201
```

## Notes

- Generate the UUID when the record is captured and keep it with the local record, so every retry,
  on any day, sends the same value.
- Uniqueness ignores case and outer spaces; a UUID is unaffected, a human-typed code is.
- In a batch, one collision rolls back every request in it. On a 104 from `_batch`, look up each
  UUID and re-send only the ones not found.
- The title names the field by display name and ends in `<br> `; match code 104 and the phrase.
