---
tags: [permission, sudo, schema, discovery]
endpoints: [GET /schema/permission_groups, GET /schema/permission_groups/<code>/entity_types/<Type>, GET /schema/permission_groups/<code>/entity_types/<Type>/fields, GET /spec.<format>, PUT /entity/<type>/<id>]
phase: schema
scope: api
measured: site-wide, 2026-11-20; script, an Admin, and a Vendor via sudo (re-roled, restored); 10 rule writes, none landed
verdict: Rules are readable over REST with their condition trees: an Admin person reads every group, a person only their own. No call writes one: PUT, POST and PATCH on the permission routes are 404.
---

# 162_permission_rules_rest

**Q** Can permission rules be read over REST, enough for an app to check that a site has the rule it
needs, and can a conditional see rule be created or changed over REST?

**Endpoint** `GET /schema/permission_groups/<code>/entity_types/<Type> ; PUT, POST, PATCH on the same route and on .../fields ; PUT /entity/permission_rule_sets/<id>`

**Docs claim** `/spec.json` lists three `GET` routes and no write. Its `PermissionGroupAccess.condition`
is "Present when `access` is `conditional`. Filter structure used by the permission engine." Probe 027
found no rule on `PermissionRuleSet`.

**Actual**

```
GET /schema/permission_groups/vendor/entity_types/Shot, as an Admin person (trimmed)
  "actions": {"read": {"access": "conditional", "condition": {"logical_operator": "or", "conditions": [
      {"path": "tasks.Task.task_assignees", "relation": "is", "values": [<Me>]},
      {"path": "tasks.Task.task_assignees.Group.users", "relation": "is", "values": [<Me>]},
      {"path": "sg_vendor_groups.Group.users", "relation": "is", "values": [<Me>]},
      {"path": "sg_vendor_groups.Group.sg_people", "relation": "is", "values": [<Me>]},
      {"path": "tasks.Task.task_assignees.HumanUser.groups.Group.users", ...}]}},
    "create": {"access": "denied"}, "update": {"access": "denied", "field_exceptions": {"allow": [...], "deny": []}}}
  "permissions": {"see_restricted": "special_rules", "see_condition": <the same tree>, ...}
  <Me> = {"type": "HumanUser", "id": 0, "valid": "logged_in_user_token", "name": "Me"}
the same call on <Bid>: "read": {"access": "allowed"}, no condition, no see_condition

the same call as the Vendor person: <Me> resolved to their own row on every leaf
  {"name": "<person>", "type": "HumanUser", "id": <their id>, "valid": "valid", "status": "act", "uuid": "<uuid>"}
  each leaf also has "no_display_name_check": true; field_exceptions has no "deny" key
vendor, …/artist/entity_types/Shot -> 403 code 102 "Forbidden" "Insufficient permissions to read this permission group configuration"
script, …/vendor/entity_types/Shot -> 404 code 103 "Unknown permission group code 'vendor'"

as the script and as the Admin person, each try followed by a read of Vendor's rights on <Bid>
  PUT, POST, PATCH …/vendor/entity_types/<Bid> {"actions": {"read": {"access": "conditional", "condition": ...}},
                                               "permissions": {"see_condition": ...}}  -> 404 code 103 "Not Found"
  PUT …/vendor/entity_types/<Bid>/fields                                             -> 404 code 103 "Not Found"
  PUT /entity/permission_rule_sets/<vendor> {"display_name": "Vendor"}  -> 400 code 103
      "API update() PermissionRuleSet.display_name is read only."
  rights after all ten tries: equal to the copy taken before, updated_at unchanged
/schema types named like a rule: PermissionRuleSet, WorkDayRule; /entity/permission_rules -> 404
```

**Who reads which group**

| caller | `GET /schema/permission_groups?…=HumanUser` | another group's rights | the person in a condition |
|---|---|---|---|
| script, `api_admin` | `[]` | 404 code 103 `Unknown permission group code '<code>'` | not readable |
| Admin person | every HumanUser group, 5 on the probed site | 200 | `logged_in_user_token`, `id` 0 |
| Vendor person | `['vendor']` | 403 code 102 | their own HumanUser row, `valid: "valid"` |

**Checking a rule**, as `has_rule` in the probe: walk `actions.read.condition`, and accept a leaf whose
`path` is the one the app needs, `relation` is `is`, and whose value is either the token or the caller's
own `{"type": "HumanUser", "id": <me>}`. Matching the token alone answers False for a person reading
their own group, which is the case an app signed in as that person meets.

| rule | token only, as the Admin | token or own id, as the Vendor |
|---|---|---|
| Shot, `sg_vendor_groups.Group.users` | True | True (token only: False) |
| Shot, `sg_vendor_groups.Group.sg_people` | True | True (token only: False) |
| `<Bid>`, a vendor Group field | False: `read` is `allowed` | False |

**Teaches**
- Conditional rules are readable, correcting probe 027: `actions.<action>.condition` holds the tree and
  the raw `permissions.see_condition` holds the same one. Only `conditional` has a tree.
- Read rules as an Admin person through `sudo_as_login`, or as the person themselves. The script reads
  no HumanUser group, and a person asking for another group gets 403 where the script gets 404.
- No REST call creates or changes a rule: the three routes answer `GET` alone and `PermissionRuleSet`'s
  10 fields are read only. A rule an app needs is added in the web interface; check for it, never write it.
- On the probed site Vendor reads `<Bid>` and `<Bid Line>` as `allowed`, and Shot as conditional on the
  five paths above. "See entities in assigned Projects only" is a setting of the role with no key in
  any of these responses; probe 166 measures its effect.
