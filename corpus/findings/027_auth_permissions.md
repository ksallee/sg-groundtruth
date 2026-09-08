---
tags: [auth, token, permission, user, client, sudo]
endpoints: [POST /auth/access_token, GET /, GET /entity/<type>]
phase: auth
scope: api
measured: site-wide, the caller's own token and the permission listings
verdict: The token endpoint accepts password and session_token. Impersonation is the OAuth2 scope sudo_as_login:<login>, never a body field, and a lower level reads far fewer rows and as many fields.
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
- Every measurement in this corpus was taken by a script user in the `api_admin` set, and a lower level reads **far fewer rows and exactly as many fields**. Impersonating an `Artist` on the probed site returned 8 projects of 22 and **zero** Versions, Shots, PublishedFiles and Notes, while `/schema/<type>/fields` returned the same counts at every level. A row count or a fill rate recorded anywhere in this corpus is an `api_admin` number; a field census is not level-dependent.

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

**Impersonation.** `sudo_as_login` is an OAuth2 **scope**, not a body field. `/spec.json` declares it on both
accepted grants as `sudo_as_login:{user_login}`, and only the scope form is read:

| sent with `client_credentials` | result |
|---|---|
| `sudo_as_login=<login>` as a body field | 200, claim `sudo_as_login` still `null`. Silently ignored |
| `scope=sudo_as_login:<login>` | 200, claim `sudo_as_login` set to that login |
| `scope`, inactive target | 400 code 102 `Cannot 'sudo' - inactive user account: '<login>'` |
| `scope`, unknown target | 400 code 102 `Cannot 'sudo' - unknown or retired user: '<login>'` |
| `scope`, target with the flag off | 400 code 102 `Cannot 'sudo' - user account has 'can_impersonate_this_user' turned off: '<login>'` |

The target needs `HumanUser.can_impersonate_this_user` true **and** `sg_status_list` active. Each refusal
names its own reason and all three land at the token endpoint, before any request the caller meant to make,
so a client learns it cannot act as someone the moment it authenticates rather than part way through a job.

The flag is not settable over REST. A script in `api_admin` writing it is refused
`400` code 104 `The field is not editable for this user: [HumanUser.can_impersonate_this_user]`, so
impersonation is something a site administrator grants in the web UI and a client can only read.

That last refusal was measured with the flag turned off by hand in the web UI, because no active account
on the probed site had it set to false. The probe looks for one and prints the row only where the site
has it, so a rerun elsewhere may show two refusals rather than three.

A sudo'd token does not change who the caller *is*: `user` stays the `ApiUser`, and `sudo_as_login` is added
holding the login string the caller supplied. The token therefore reports nothing the caller did not already
know, so a client wanting the human's id must look the login up.

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

**What a level changes.** The experiment this finding once called for, a second caller at a lower level
diffed row for row, needs no second credential: impersonation supplies it. Measured with one script key,
acting as itself, as an `Admin` and as an `Artist`:

```
rows projects          script:22   Admin:22   Artist:8
rows human_users       script:25   Admin:25   Artist:25
rows api_users         script:16   Admin:16   Artist:400 "Entity of type ApiUser can not be
                                                          accessed by this user. Rule: Artist"
rows versions          script:200  Admin:200  Artist:0
rows shots             script:200  Admin:200  Artist:0
rows published_files   script:200  Admin:200  Artist:0
rows notes             script:200  Admin:200  Artist:0
schema fields Version  script:71   Admin:71   Artist:71
GET /license_info      script:200  Admin:200  Artist:401 "Must sudo as Administrator to query
                                                          license information"
GET /me                script:404  Admin:404  Artist:404
```

Rows collapse, fields do not, and a refusal is a 400 naming the rule or a 401 naming the level rather than an
empty list. `/me` stays absent for a human caller too, so that finding is a property of the API and not of
the script user who first measured it.

**Unmeasured.** Which permission *rules* produce those numbers: `PermissionRuleSet` exposes no rule and the
site's own settings are not on the REST surface, so only the effect is measurable, never the cause.
Conditional permissions are therefore invisible here. Whether `password` or `session_token` yields a usable
REST token at all, and what `auth_type` then reads, is still untested: both were sent deliberately fake
credentials. Only levels the probed site has *active* can be compared, and a site whose lower-level accounts
are all disabled measures nothing.
