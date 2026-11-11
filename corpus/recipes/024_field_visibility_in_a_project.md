---
intent: Read which fields of an entity type a project hides, and show or hide one field in one project without touching the others
tags: [schema, custom-field, project, write]
endpoints: [GET /schema/<Type>/fields, PUT /schema/<Type>/fields/<field>]
scope: api
measured: sample project 1 of 1, sandbox project written, one text field on Version, retired
---

# 024_field_visibility_in_a_project

A field exists site-wide and `visible` is per project (probe 115). One listing call per entity type
and project reads it for every field. The write needs the project, and changes that project only.

## Call

```python
def hidden_fields(c, entity_type, project_id):
    """Programmatic names of the fields this project hides. Check the id first: a wrong one reads as none."""
    d = c.get(f"/schema/{entity_type}/fields", params={"project_id": project_id}).json()["data"]
    return sorted(k for k, v in d.items() if v["visible"]["value"] is False)


def set_visible(c, entity_type, field, project_id, visible):
    """Read first, write only on a difference, read back. Returns True when a write was made."""
    path = f"/schema/{entity_type}/fields/{field}"
    now = c.get(path, params={"project_id": project_id}).json()["data"]["visible"]
    if now["value"] is visible:
        return False
    if not now["editable"]:
        raise RuntimeError(f"{entity_type}.{field} cannot be hidden or shown")   # probe 056
    r = c.put(path, json={"properties": [{"property_name": "visible", "value": visible}],
                          "project_id": project_id})
    if not r.ok:
        raise RuntimeError(r.json()["errors"][0]["title"])
    back = c.get(path, params={"project_id": project_id}).json()["data"]["visible"]["value"]
    if back is not visible:
        raise RuntimeError("accepted and not applied")
    return True
```

## Response

```
GET /schema/Shot/fields?project_id=N -> 200, 100 fields, 12 with visible.value false
PUT /schema/Version/fields/sg_zzprobe_115_visibility
    {"properties": [{"property_name": "visible", "value": false}], "project_id": N}
  -> 200, the whole field
  visible   site scope: true   project N: false   another project: true
the same PUT without project_id
  -> 400 code 104 "API schema_field_update(): The 'visible' property requires a project to be updated."
```

## Notes

- A field just created is visible in every project. A field retired and revived is too, whatever it
  was before (probe 115).
- `project_id` is also accepted in the query. Inside the property object it is not read (probe 119).
- A `project_id` that does not exist reads as a project hiding nothing, at 200. The write refuses it,
  400 code 105.
- There is no site-wide write and no call that sets several projects: one PUT per field and project.
