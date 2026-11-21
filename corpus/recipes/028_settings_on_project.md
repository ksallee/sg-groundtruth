---
intent: Keep an app's settings for a project as JSON on the Project row, written by an Admin and read by everyone in the project
tags: [custom-field, project, permission, schema]
endpoints: [GET /schema/<Type>/fields, POST /schema/<Type>/fields, POST /schema/<Type>/fields/<field>, GET /schema/<Type>/fields/<field>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>]
scope: api
measured: sandbox project written, 2026-11-17; three text fields on Project made and retired; an Admin and two Artists via sudo
coverage: partial
unmeasured: a Manager's create and write (probes 157, 159). Blocked on the site: nobody active in Manager has impersonation on
---

# 028_settings_on_project

A `jsonb` field cannot be created over REST (probe 160), and a `text` field stores 1,000,000
characters of JSON byte for byte (probe 158). One text field per settings list on Project, created
once by an Admin, gives every project its own copy, readable by its members (probe 159).

## Call

```python
import json
import re


def ensure_field(c, display):
    """Once per site, as an Admin or the script. `Onset Templates` -> `sg_onset_templates` (probe 117)."""
    assert display.isascii(), "a non-ASCII display name is created as sg_text (probe 117)"
    name = "sg_" + re.sub(r"[^a-z0-9_]", "_", display.lower())
    if name in c.get("/schema/Project/fields").json()["data"]:       # a second create gives `_1` (probe 019)
        return name
    r = c.post("/schema/Project/fields", json={"data_type": "text", "properties": [
        {"property_name": "name", "value": display}]})
    if r.status_code == 400 and "retired field" in r.text:           # in the Trash (probe 117)
        c.post(f"/schema/Project/fields/{name}", json={"revive": True}).raise_for_status()  # probe 040
        return name
    r.raise_for_status()                                             # an Artist: 500 code 105 (probe 157)
    return r.json()["links"]["self"].rsplit("/", 1)[-1]


def can_write(c, field, project_id):
    """Per caller. False for an Artist (probe 159)."""
    r = c.get(f"/schema/Project/fields/{field}", params={"project_id": project_id})
    return r.ok and r.json()["data"]["editable"]["value"]


def write_settings(c, field, project_id, value):
    r = c.put(f"/entity/projects/{project_id}", json={field: json.dumps(value, ensure_ascii=False)})
    r.raise_for_status()


def read_settings(c, field, project_id, default=None):
    r = c.get(f"/entity/projects/{project_id}", params={"fields": field})   # always name fields (probe 158)
    if r.status_code == 404:                       # not a member of this project (probe 159)
        return default
    raw = r.json()["data"]["attributes"][field]
    return json.loads(raw) if raw else default     # "" is stored as null (field_types/text)
```

## Response

```
POST /schema/Project/fields, an Admin person -> 201 links.self .../schema/Project/fields/sg_zzprobe_157_admin
POST /schema/Project/fields, an Artist       -> 500 code 105 "API schema_field_create() RuntimeError: User doesn't
                                                have permission to create a Field"
the same display name after a retire         -> 400 code 105 "... there is a retired field with the same
                                                field_name: sg_zzprobe_159_rights. ..."; revive -> 204
PUT 1,000,000 characters of JSON             -> 200 in 1.0 s; GET reads it back byte for byte
PUT, an Artist in the project                -> 400 code 104 "The field is not editable for this user: [Project.<field>]."
GET, an Artist in the project                -> 200, the value
GET, an Artist not in the project            -> 404 code 104 "Project: <id> not found"
```

## Notes

- Compare parsed values, never the raw string: a leading or trailing newline is stripped on write.
- An Artist cannot save settings. Show them read-only when `can_write` is false, or send the write
  through the script.
- A field on Project is site-wide: creating it adds it to every project. The value is per project.
- `GET /entity/projects/<id>` with no `fields` returns the whole settings string, so every other
  client reading a Project without `fields` pays for its size.
