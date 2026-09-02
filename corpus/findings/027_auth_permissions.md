---
tags: [auth, token, permission, user, client]
scope: api
verdict: The token endpoint also accepts password and session_token, not authorization_code; the bearer is a signed token whose user claim names the caller and the row holding its permission rule set.
---

# 027_auth_permissions

**Q** Who can authenticate, and how does the caller's permission level change what the API returns?

**Endpoint** `POST /api/v1/auth/access_token ; GET /api/v1 ; GET /entity/api_users ; GET /entity/permission_rule_sets`

**Docs claim** The REST docs describe `client_credentials` with a script name and key, and mention `refresh_token`. They do not list the full accepted set, and they name no endpoint that reports who the caller is.

**Actual**

```
GET /api/v1 -> user_authentication_method 'oxygen', unified_login_flow_enabled True,
               authentication_app_session_launcher_enabled True

POST /auth/access_token  grant_type=
  client_credentials             200
  client_credentials, bad secret 400 "Can't authenticate script '<script name>'"
  password, fake user+password   400 "Can't authenticate user '<user>'."
  password, no arguments         400 "Missing or invalid authentication arguments"
  session_token, fake token      400 "Can't authenticate session token ending with 'alue'"
  session_token, no arguments    400 "Missing or invalid authentication arguments"
  refresh_token, fake token      401 "Unauthorized"
  authorization_code / implicit / urn:ietf:params:oauth:grant-type:device_code / "" / typo
                                 400 "Unsupported grant_type"
  "source" is {} or null on every 400 above; none names the accepted set

GET /me, /auth/me, /session, /auth/session, /users/me, /entity/human_users/me,
    /entity/api_users/me -> 404 {"status":404,"code":103,"title":"Not Found","source":null}

access_token: 3 segments [20, 350, 43], header {"alg":"HS256"}; segment 2 decodes to
  {"iss": "<site host>", "aud": "<site host>", "exp": ..., "iat": ..., "jti": ...,
   "user": {"type": "ApiUser", "id": <id>}, "sudo_as_login": null,
   "auth_type": "api_key", "session_uuid": null}
GET /entity/api_users/<id> -> 200 permission_rule_set {"id": 6, "name": "API Admin",
  "type": "PermissionRuleSet"}, projects []

GET /entity/permissions -> 404 "Entity type 'permissions' does not exist." (same for
  permission_rules and roles)
/schema/PermissionRuleSet/fields -> 10 fields, 0 editable, none holding a rule:
  cached_display_name code created_at created_by display_name entity_type id parent_set
  updated_at updated_by
```

**Teaches**
- A script key is not the only way in. `password` and `session_token` are accepted grants: both fail on the credential, not on the grant name, while `authorization_code`, `implicit` and the device-code URI all fail on the grant name. A person with a Flow PT login can therefore reach the same REST API without an administrator issuing a script user.
- No route reports the caller. The bearer itself does: it is three dot-separated segments, and segment 2 is base64url JSON with a `user` claim of `{type, id}` plus `auth_type` and `sudo_as_login`. Decode it to read the claim; never verify it, and never log it.
- The permission model is readable as rows and opaque as rules. `PermissionRuleSet` has 10 fields, all read only, and none of them holds a rule. A client learns which set a user is in and nothing about what that set allows.
- Every measurement in this corpus was taken by a script user in the `api_admin` set. A caller at a lower level may see fewer rows and fewer fields, and no finding here is qualified by that.

**Grant types.** Two failure shapes separate an accepted grant from a rejected one. `Unsupported grant_type` (code 103) means the name is not in the set. Any other error means the name was accepted and the credential was not.

| `grant_type` | result | accepted? |
|---|---|---|
| `client_credentials` | 200 | yes |
| `password` | 400 `Can't authenticate user '<user>'.` | yes |
| `session_token` | 400 `Can't authenticate session token ending with 'alue'` | yes |
| `refresh_token` | 401 `Unauthorized` | yes |
| `authorization_code` | 400 `Unsupported grant_type` | no |
| `implicit` | 400 `Unsupported grant_type` | no |
| `urn:ietf:params:oauth:grant-type:device_code` | 400 `Unsupported grant_type` | no |
| omitted or misspelled | 400 `Unsupported grant_type` | no |

Unlike a filter operator (probe 017), the rejection does not enumerate the accepted set: `source` is `{}` or `null` on all of them. The set above was found by probing names, so a grant this probe did not try may exist.

`session_token` is the grant the official launcher's flow ends at. `GET /api/v1` reports
`authentication_app_session_launcher_enabled` and `unified_login_flow_enabled` before any token exists, so a
client can test a site for that path without credentials. Obtaining a session token needs the launcher and
was not measured here.

Passing `sudo_as_login` to the token endpoint alongside `client_credentials` returned 200 with the claim
still `null`, so the parameter is ignored at that layer.

**Who am I.** There is no `me` route under any of the seven shapes tried. The identity is in the token:

```python
import base64, json
p = access_token.split(".")[1]
who = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))["user"]   # {"type": "ApiUser", "id": 298}
```

Then `GET /entity/api_users/<id>` or `/entity/human_users/<id>` returns `permission_rule_set` under
`relationships` as a `{id, name, type}` hash, and `projects` as the multi_entity list that scopes the caller
to a project subset. An empty `projects` list is site-wide access. A script that cannot decode its own token
can still find itself by filtering `api_users` on `firstname is <the client_id it authenticated with>`,
because `firstname` is the script name; `_search` returned exactly one row for it.

**What the permission model exposes.** `/entity/permissions`, `/entity/permission_rules` and `/entity/roles`
do not exist. `PermissionRuleSet` rows are the whole of it, keyed by `entity_type`: a plain type name is a set
users are assigned to, and a dotted `PermissionRuleSet.<Type>` composite is the site's default set for that
type. On the probed site there are 12 rows. `Group` exists as a separate 18-field type whose `users`
multi_entity holds members; on the probed site all 4 groups are empty, and `HumanUser.groups` was empty on
every row.

| `entity_type` | `code` on the probed site |
|---|---|
| `HumanUser` | `admin`, `manager`, `artist`, `vendor`, one site-added variant |
| `ApiUser` | `api_admin` |
| `ClientUser` | `client_user` |
| `PermissionRuleSet.HumanUser` | `admin_system_default`, `manager_system_default`, `artist_system_default` |
| `PermissionRuleSet.ApiUser` | `api_admin_system_default` |
| `PermissionRuleSet.ClientUser` | `client_user_system_default` |

On the probed site the 24 `HumanUser` rows split 12 `Admin`, 6 `Artist`, 3 `Manager`, 3 `Vendor`, and all 16
`ApiUser` rows are `API Admin`.

**Unmeasured.** One credential was available, a script user in `api_admin`. Nothing here measures what a
lower-permission caller reads. A row count, a field census, a fill rate or a status vocabulary recorded
anywhere in this corpus was taken at that level and may be smaller for an artist. Whether `password` or
`session_token` yields a usable REST token at all, and what `auth_type` then reads, is untested: both were
sent deliberately fake credentials. The experiment that settles it is a second credential at a lower level,
running the same probes and diffing the output row for row and field for field.
