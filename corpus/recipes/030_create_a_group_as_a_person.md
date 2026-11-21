---
intent: Create a Group as the signed-in person, once their permission group allows it, without a second Group of the same name
tags: [group, permission, sudo]
endpoints: [GET /entity/<type>/<id>, GET /schema/permission_groups/<code>/entity_types/<Type>, POST /entity/<type>/_search, POST /entity/<type>, PUT /entity/<type>/<id>]
scope: api
measured: site-wide, 2026-11-21; run as written by a Manager and a Vendor via sudo; 1 Group made and retired
coverage: partial
unmeasured: an App Session Launcher bearer (recipe 012); it needs the person at a browser. `sudo_as_login` applies the same permission set (probe 094)
---

# 030_create_a_group_as_a_person

A Group is site-wide and has no project. Whether a person may create one is their permission group's
rule on Group, which they can read about themselves before the app shows a create control (probe 168).
`code` is neither required nor unique, so the app looks for the name first.

## Call

```python
def my_group_code(c, me):
    """The person's own permission group code. An Admin lists every group, so read it off the person."""
    s = c.get(f"/entity/human_users/{me}", params={"fields": "permission_rule_set"}).json()
    set_id = s["data"]["relationships"]["permission_rule_set"]["data"]["id"]
    return c.get(f"/entity/permission_rule_sets/{set_id}", params={"fields": "code"}).json()["data"]["attributes"]["code"]


def group_rights(c, me):
    """{'read': 'allowed', 'create': 'denied', ...} for Group, as this person's group has it."""
    code = my_group_code(c, me)
    acts = c.get(f"/schema/permission_groups/{code}/entity_types/Group").json()["data"]["actions"]
    return {k: v["access"] for k, v in acts.items()}


def find_or_create_group(c, name, members):
    """One Group per name. Two may share a `code`, so the first live match wins."""
    hit = c.post("/entity/groups/_search",
                 headers={"Content-Type": "application/vnd+shotgun.api3_array+json"},
                 json={"filters": [["code", "is", name]], "fields": ["code", "users"]}).json()["data"]
    if hit:
        return hit[0]["id"], False
    r = c.post("/entity/groups", json={"code": name,
                                       "users": [{"type": "HumanUser", "id": i} for i in members]})
    if r.status_code == 400 and r.json()["errors"][0]["code"] == 104:
        raise PermissionError(r.json()["errors"][0]["title"])
    r.raise_for_status()
    return r.json()["data"]["id"], True


def add_member(c, group_id, person_id):
    """`add`, never a bare list: a bare list replaces every member (recipe 009)."""
    return c.put(f"/entity/groups/{group_id}", json={"users": {
        "multi_entity_update_mode": "add", "value": [{"type": "HumanUser", "id": person_id}]}})
```

## Response

```
group_rights, as each person   manager, admin  {'read': 'allowed', 'create': 'allowed', 'update': 'allowed',
                                                 'retire': 'allowed', 'delete': 'allowed'}
                               artist, vendor  {'read': 'allowed', 'create': 'denied', 'update': 'denied',
                                                 'retire': 'denied', 'delete': 'denied'}
find_or_create_group, manager  (<id>, True); created_by is the person; users read back [the member]
  called again with the name   (<the same id>, False)
find_or_create_group, vendor   (<the manager's id>, False) once it exists; before that
                               PermissionError: Entity of type Group cannot be created by this user.
add_member, manager            200
add_member, vendor             400 code 104 "The field is not editable for this user: [Group.users]."
```

## Notes

- Show the control when `create` is `allowed`. On the probed site that is Manager and Admin; the
  rule is site configuration and changes only in the web interface (probe 162).
- The same rule lets the person rename, re-member and retire every Group on the site, not only the
  ones they made. Keep those controls to the Groups the app made, by id.
- Without `code` the server names the Group `New Group <id>` and answers 201. Always send one.
- The `_search` and the `POST` are two calls, so two people creating the same name at once can still
  make two Groups.
- A new Group in `Shot.sg_vendor_groups` reaches the vendor's next request (probes 166, 168).
