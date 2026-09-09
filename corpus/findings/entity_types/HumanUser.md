---
tags: [user, permission, sudo]
scope: api
measured: site-wide, 25 HumanUser rows, one row created and deleted twice
coverage: partial
unmeasured: what an active user costs in seats, since the site refuses to create or promote one; and whether `projects` or the permission rule set produces the project subset, which needs two users the site does not have
summary: A person with a login, the row every created_by, assignee and follower points at.
verdict: `sudo_as_login` matches `login` and never `email`; a create is 401 unless it sends `sg_status_list: "dis"`, and an empty `projects` is not site-wide access.
---

# HumanUser

**Type** Schema name `HumanUser`, addressed at `/entity/human_users`. Site-wide: it has no `project`
field, and a person's project membership is the `projects` multi_entity on the row.

| path | result |
|---|---|
| `/entity/human_users`, `/entity/HumanUser` | 200, `type: "HumanUser"` |
| `/entity/humanusers` | 404 `Entity type 'humanusers' does not exist.` |
| `/entity/users` | 404 `Entity type 'users' does not exist.` |

**Identity** `login`, the only field on the type flagged unique. `email` is not unique, and neither is
the display name.

| field | data_type | editable | mandatory | unique |
|---|---|---|---|---|
| `login` | text | yes | no | **yes** |
| `email` | text | yes | no | no |
| `name` | text | yes | yes | no |
| `firstname`, `lastname` | text | yes | no | no |
| `cached_display_name` | text | yes | no | no |
| `password_proxy` | password | no | no | no |

`code` does not exist on the type: a filter on it is
`400 API read() HumanUser.code doesn't exist.` `login`, `email`, `name` and `firstname` all filter at
200. `name` is the display name and reads back as `firstname` and `lastname` joined by a space.

**Create** Measured behind `--write`, with the operator's consent, on a login and an email under
`example.invalid`. One row was created, deleted, created again and deleted again, leaving nothing.

| body | result |
|---|---|
| `{}` | 401 code 110 `User promotion to active is permitted only for Identity Users` |
| `{"login": ...}` | 401, the same title |
| `{"login": ..., "email": ...}` | 401, the same title |
| `{"login": ..., "email": ..., "firstname": ..., "lastname": ...}` | 401, the same title |
| `{"login": ..., "email": ..., "sg_status_list": "dis"}` | **201** |
| the same body while the first row is live | 400 code 104 `Create failed for [HumanUser]: The value for the Login field is required to be unique. <br> ` |
| the same body after the row is deleted | 201, a new id. The login is free again |
| `PUT {"sg_status_list": "act"}` on the created row | 401 code 110, the same title as the create |

`sg_status_list` has `default_value` `act`, so a create that omits it asks for an active user and is
refused. The one body that works asks for a disabled one, and nothing over REST then activates it.

```
GET /entity/human_users/<new id>
 attributes    {"login": "zzprobe_054_user", "email": "<email>", "name": "New User c5eb099acf",
                "firstname": "New", "lastname": "User c5eb099acf", "sg_status_list": "dis",
                "can_impersonate_this_user": true}
 relationships {"permission_rule_set": {"id": 8, "name": "Artist", "type": "PermissionRuleSet"},
                "projects": [], "groups": []}
```

`login` and `email` are stored as sent. `firstname`, `lastname` and `name` are server-written when
omitted, and `permission_rule_set` is the site's default for the type: the field is not editable.

**Seats** A disabled row is free, and neither call is a row count (`endpoints/get_license_info`).

| step | `GET /license_info` | `GET /subscription_seat/user_subscriptions` |
|---|---|---|
| before the create | `{"assigned": 4, "rule": "quantity", "free": 46, "total": 50}` | 15 keys |
| row created | unchanged | unchanged, no key for the new id |
| row deleted | unchanged | unchanged |
| created and deleted a second time | unchanged | unchanged |

Those numbers are the probed site's. What an **active** user costs was not measured: the site is on
Autodesk Identity, and it refuses to create or promote one over REST.

**Delete** `DELETE /entity/human_users/<id>` retires the row at 204 and empties nothing.

| after the delete | result |
|---|---|
| `GET /entity/human_users/<id>` | 404 `HumanUser: 488 not found` |
| `GET /entity/human_users/<id>?options[return_only]=retired` | 200, `login` still on the row |
| `_search` on `login` or on `email` | 200, 0 rows |
| creating the same `login` and `email` again | 201, a new id |

A retired user is still readable and still referenced by every `created_by` pointing at it, so a
client resolving an id has to handle a row that no search will ever return.

**Impersonation** `sudo_as_login:<x>` is matched against `login`, never against `email`. Probe 027
covers the scope form, the refusals and what a level changes.

| scope sent | result |
|---|---|
| the subject's `login` | 200, the claim set to what was sent |
| the subject's `email`, where it differs from the login | 400 code 102 `Cannot 'sudo' - unknown or retired user: '<email>'` |
| the subject's `email`, where the login is the email | 200 |

On the probed site 10 of 25 rows have `login` equal to `email`, which is what makes an email look
like it works. Read `login` off the row and send that.

`can_impersonate_this_user` is a `checkbox` and is not editable, on a row the caller made as much as
on any other. On the probed site it is true on all 25 rows and on a freshly created one.

```
PUT /entity/human_users/<id>  {"can_impersonate_this_user": true}
 400 code 104 "The field is not editable for this user: [HumanUser.can_impersonate_this_user].
               Rule: API Admin -- PermissionRule 2027: DENY update_field FOR
               entity_type => HumanUser, field_name => can_impersonate_this_user, field_value => "
```

**What a person reads** An empty `projects` is not site-wide access. Correcting probe 027, which read
an empty list off an `ApiUser` and called it site-wide:

| subject | `permission_rule_set` | `HumanUser.projects` | projects whose `users` name them | projects read as them |
|---|---|---|---|---|
| an Artist | `Artist` | 0 | 0 | 8 of 22 |
| an Admin | `Admin` | 4 | 3 | 22 of 22 |

On the probed site the Artist's 8 were 7 template projects and one archived template, none of the 14
plain shows, and one of them is absent from the script user's own listing. The two ends of the link
disagree as well, 4 against 3 on the Admin. Impersonate and count rather than reading either field.

**Status** `sg_status_list`, a `status_list`.

| key | value on the probed site |
|---|---|
| `valid_values` | `['act', 'dis']` |
| `display_values` | `{'act': 'Active', 'dis': 'Disabled'}` |
| `default_value` | `'act'` |

`act` is one of the two conditions on impersonation, with `can_impersonate_this_user` (probe 027).

**Links** On the probed site `/schema/HumanUser/fields` returns 65 fields, 48 of them editable.

| field | type | editable | `valid_types` |
|---|---|---|---|
| `projects` | multi_entity | yes | `Project` |
| `groups`, `sg_vendor_group` | multi_entity, entity | yes | `Group` |
| `permission_rule_set` | entity | no | `PermissionRuleSet` |
| `department` | entity | yes | `Department` |
| `pipeline_configurations` | multi_entity | yes | `PipelineConfiguration` |
| `custom_home_page` | entity | yes | `Page` |
| `bookings`, `contracts`, `app_welcomes`, `tags` | multi_entity | `contracts` no, rest yes | `Booking`, `Contract`, `AppWelcome`, `Tag` |
| `banners` | multi_entity | yes | `[]`, declared empty |
| `created_by`, `updated_by` | entity | no | `HumanUser`, `ApiUser` |
| `image_source_entity` | entity | no | 106 types, every one on the site |

**Traps**
- Key on `login`. `email` is not unique, `name` is not unique, and `code` does not exist.
- A create is 401 and not 400, so a client checking for a 4xx body shape finds `code: 110` where every
  other create failure is `code: 103`.
- The only creatable user is a disabled one, and `PUT sg_status_list: "act"` is refused the same way.
  A script cannot onboard a person on this site.
- `permission_rule_set` and `can_impersonate_this_user` are read only: what a person may do and who
  may act as them are granted in the web interface and read over REST.
- A deleted user is retired, not erased, and its `login` becomes reusable, so two rows can hold the
  same login with only one of them live.
