# Findings — auth: getting a token, and what it is

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 001_auth

Send the token request as `application/x-www-form-urlencoded`: `application/json` is 400 Invalid JSON body. client_credentials returns a 600s bearer, so ignore the refresh_token and re-auth.

- `expires_in` is 600 exactly, as documented. A long-running client must handle expiry, not assume one token per session.

- A `refresh_token` is issued but buys nothing here: re-authing is one call with credentials already in hand, so the client re-auths instead of storing refresh state.

- The token is a plain bearer string. One exchange against one site was measured, so whether a token or a
  script credential is accepted by a second site is untested. Settling it needs credentials on another site.

**Content-Type.** The endpoint matches the media type and ignores its parameters:

| sent | result |
|---|---|
| header omitted | 200 |
| `application/x-www-form-urlencoded` | 200 |
| `application/x-www-form-urlencoded; charset=utf-8` | 200 |
| `application/x-www-form-urlencoded;charset=UTF-8` | 200 |
| `application/x-www-form-urlencoded; charset=bogus` | 200 |
| `application/json` | 400 `Invalid JSON body`, `source.body` `Empty input (after ) at line 1, column 1 ` |
| `text/plain` | 415 `Unsupported Content-Type 'text/plain'`, `source.content_type` `Content-Type must be one of: 'application/x-www-form-urlencoded'.` |

Two production clients strip the `charset` parameter before posting here, on the report that the endpoint
rejects it. On the probed site it does not: every parameter above returns 200, including one naming a
charset that does not exist. The 415 that names the accepted set comes from the media type in front of the
parameter, so read that part of the header first. `application/json` is a different failure again: it is
accepted as a media type and the form body is then parsed as JSON, giving 400 `Invalid JSON body`.

`corpus/findings/001_auth.md`

## 027_auth_permissions

The token endpoint accepts password and session_token. Impersonation is the OAuth2 scope sudo_as_login:<login>, never a body field, and a lower level reads far fewer rows and as many fields.

- A script key is not the only way in. `password` and `session_token` are accepted grants: both fail on the credential, not on the grant name, while `authorization_code`, `implicit` and the device-code URI all fail on the grant name. A person with a Flow PT login can therefore reach the same REST API without an administrator issuing a script user.

- No route reports the caller. The bearer itself does: it is three dot-separated segments, and segment 2 is base64url JSON with a `user` claim of `{type, id}` plus `auth_type` and `sudo_as_login`. Decode it to read the claim; never verify it, and never log it.

- The permission model is readable as rows and opaque as rules. `PermissionRuleSet` has 10 fields, all read only, and none of them holds a rule. A client learns which set a user is in and nothing about what that set allows.

- Every measurement in this corpus was taken by a script user in the `api_admin` set, and a lower level reads **far fewer rows and exactly as many fields**. Impersonating an `Artist` on the probed site returned 8 projects of 22 and **zero** Versions, Shots, PublishedFiles and Notes, while `/schema/<type>/fields` returned the same counts at every level.

- A row count or a fill rate recorded anywhere in this corpus is an `api_admin` number; a field census is not level-dependent.

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
to a project subset. The `ApiUser` measured here reads every project with an empty list; a HumanUser with an
empty list does not (`entity_types/HumanUser`). A script that cannot decode its own token
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

`corpus/findings/027_auth_permissions.md`

## 052_app_session_launcher

Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session. **[partial]**

not measured: a person clicking deny, and a session left idle past the site's expiry window; both wait on time and on the site, not on the probe

- A person reaches the REST API with no script key and no password: two unauthenticated calls, a
  browser, and a click. The bearer is a `HumanUser`, so `created_by` and `Version.user` are the person
  without `sudo_as_login` and without an administrator granting `can_impersonate_this_user`
  (probe 027).

- The session token is the credential; the bearer is disposable. Hold the session token, mint a 600s
  bearer whenever one is needed, and each mint moves the session's expiry to now plus the site's
  window (one day on the probed site), written at most once every five minutes.

- A token spent at least once per window never expires; one left idle past it does, and the token endpoint then
  refuses it.

- A pending request lives about five minutes and a handed-out one is gone at once. Poll from one place,
  keep `sessionToken` from the one response that holds it, and when the poll turns 404 issue a new request and show
  the person the new `url` rather than tell them what went wrong: forgotten, denied and mistyped all
  read `{"message":"Not Found"}`.

- `/internal_api` is the web app's own surface, found by reading the site's session checker script.
  Every call on it takes the session token as the `_session_id` cookie, answers errors as
  `{"message": ...}` rather than `errors[]`, and is versioned by nobody. Read the site's
  `GET /internal_api/session` for the expiry rather than assume the preference.

`corpus/findings/052_app_session_launcher.md`

## 126_session_idle

The token endpoint refuses a session token it does not accept with 400 code 102 in errors[], "Can't authenticate session token ending with '<last 4>'". No API read exposes the session window. **[partial]**

not measured: a real session token left idle past the window. Needs a person to approve 052 --login, then a day of nobody spending it. Blocked on time

- Treat 400 code 102 from `grant_type=session_token` as "send the person through sign-in again".
  It is in the `errors[]` envelope like every `/api/v1` error; `GET /internal_api/session` answers
  the same token with a bare `{"message":"Unauthorized"}` (probe 052). The title quotes the token's
  last four characters and nothing else, so a mistyped token cannot be told from any other refusal.

- Whether an idle-expired token answers the same code and envelope is unmeasured: on 2026-11-11 no
  saved token existed. `--idle` prints the envelope of both answers beside the never-valid ones.

- The window is not readable: `/preferences` exposes 17 display and scheduling keys and silently
  answers `{}` for any other name. Read `expiresAt` from `GET /internal_api/session` while the token
  is live (probe 052) instead.

- Writing the window was not tried: `PUT /preferences/update` is 400 code 111 for every preference
  on the probed site (probes 047, 114).

`corpus/findings/126_session_idle.md`

## 130_launcher_answers

sessionRequestId is 21 characters of A-Za-z0-9_-. url is on the site's host unless the create call sends X-Forwarded-Host, which url copies: a proxy strips that header. **[partial]**

not measured: the create call on a site with authentication_app_session_launcher_enabled false. The probed site has it on and no preference is changed; blocked on the site

- Validate a `sessionRequestId` as `^[A-Za-z0-9_-]{21}$` on the probed site's nine samples. Treat it as
  opaque beyond that; nothing documents the shape.

- `url` takes its host from `X-Forwarded-Host` when the create call has one, and a person who opens
  it lands on a host that is not the site. A proxy forwarding the launcher calls (probe 062) drops
  that header, and a client checks that `url`'s host equals the site's before opening it.

- `X-Forwarded-Proto`, `X-Forwarded-Port`, `Forwarded`, `Origin` and `Referer` change nothing in `url`.

- `sticky_id` is a second 21-character value, not a copy of the id. Pass `url` through whole.

- A pending request cannot be withdrawn: `DELETE` is 404 code 103 and the request still answers. It
  is forgotten about five minutes after creation (probe 052).

- On a site with the launcher switched off the answer is unmeasured. Read
  `authentication_app_session_launcher_enabled` from `GET /api/v1` before offering this sign-in, and
  measure the create call there with `python probes/130_launcher_answers.py` against such a site.

`corpus/findings/130_launcher_answers.md`

## 131_session_revoke

The REST spec has no revoke or sign-out call. Of five candidate routes only /user/logout answers (302 to login); whether it ends a launcher session is unmeasured. **[partial]**

not measured: whether /user/logout ends a live session and what a bearer minted before it then reads. Needs a person to approve `python probes/131_session_revoke.py --login`. Blocked on the work

- No documented call ends a session. Until `--login` is run, an app's sign-out can only forget the
  session token; the session on the site then ends one window after the last mint (probe 052).

- `GET /user/logout` is the only route that answers, and a 302 to the login page is its answer with
  no session at all. Confirm a sign-out by reading `GET /internal_api/session` afterwards: 401 is
  ended, 200 is not.

`corpus/findings/131_session_revoke.md`
