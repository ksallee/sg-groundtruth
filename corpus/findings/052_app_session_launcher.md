---
tags: [auth, token, user, launcher, permission]
endpoints: [GET /, POST /internal_api/app_session_request, PUT /internal_api/app_session_request/<sessionRequestId>, POST /auth/access_token, GET /internal_api/session, POST /internal_api/session, POST /internal_api/autodesk_identity/license_renewal]
phase: auth
scope: api
measured: site-wide, two requests approved by one person in a browser, the session read and renewed
coverage: partial
unmeasured: a person clicking deny, and a session left idle past the site's expiry window; both wait on time and on the site, not on the probe
verdict: Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.
---

# 052_app_session_launcher

**Q** Can a client with only `requests` sign a person in through the App Session Launcher, and what is the
session token it gets worth at the REST token endpoint?

**A person is in this loop.** The token is handed out only after someone logged into the site in a
browser opens the request's page and clicks approve. The probe's `--login` mode opens that page and
waits; nothing in it can approve on their behalf.

**Endpoint** `POST /internal_api/app_session_request ; PUT /internal_api/app_session_request/<id> ; POST /auth/access_token ; GET /internal_api/session`

**Docs claim** The REST docs list `session_token` as a grant and say a session token comes from the
Python API or from "logging into the web application". The launcher endpoints are undocumented. The
Site Preferences help says an API-generated session expires when its last update is more than one
hour, day or week old, per the `User Session Expiry` setting.

**Actual**

```
GET /api/v1 -> user_authentication_method 'oxygen', authentication_app_session_launcher_enabled True

POST /internal_api/app_session_request, no body      400 {"message":"Missing params: appName, machineId"}
POST form or json appName+machineId                  200 {"sessionRequestId":"<id>","url":"<site>/app_session_request/<id>?sticky_id=<id>"}
GET  url, no cookie                                  302 -> <site>/user/login?return_path=/app_session_request/<id>

PUT /internal_api/app_session_request/<id>  pending  200 {"approved":false}      machineId ignored
                                            approved 200 {"approved":true,"sessionToken":"<token>","userLogin":"<login>"}
                                            again    404 {"message":"Not Found"}
                                            unknown  404 {"message":"Not Found"}
                                            nobody approves: 404 after 305s

POST /auth/access_token grant_type=session_token     200 expires_in 600, refresh_token present
  bearer claims  user {"type":"HumanUser","id":<id>}  auth_type "session_token"  sudo_as_login null
  same session token, second time                    200        minting does not consume it
  grant_type=refresh_token on its refresh_token       200 expires_in 600
GET /entity/human_users/<id>                          200 permission_rule_set {"name": "Admin", ...}

GET /internal_api/session, cookie _session_id=<session token>
  200 {"app":{"createdAt":<t>,"expiresAt":<t+86400>},"license":{...},"expired":false,"expiresAt":...}
  a second GET               expiresAt unchanged
  after minting a bearer     expiresAt = now + 86400
  POST /internal_api/session 200 {"message":"OK"}, expiresAt = now + 86400
  POST .../license_renewal   200 {"message":"OK"}, license and app both reset to now
  no cookie, or bearer only  401 {"message":"Unauthorized"}
```

**Teaches**
- A person reaches the REST API with no script key and no password: two unauthenticated calls, a
  browser, and a click. The bearer is a `HumanUser`, so `created_by` and `Version.user` are the person
  without `sudo_as_login` and without an administrator granting `can_impersonate_this_user`
  (probe 027).
- The session token is the credential; the bearer is disposable. Hold the session token, mint a 600s
  bearer whenever one is needed, and each mint moves the session's expiry to now plus the site's
  window (one day on the probed site). A token spent at least once per window never expires; one left
  idle past it does, and the token endpoint then refuses it.
- A pending request lives about five minutes and a handed-out one is gone at once. Poll from one place,
  keep `sessionToken` from the one response that holds it, and when the poll turns 404 issue a new request and show
  the person the new `url` rather than tell them what went wrong: forgotten, denied and mistyped all
  read `{"message":"Not Found"}`.
- `/internal_api` is the web app's own surface, found by reading the site's session checker script.
  Every call on it takes the session token as the `_session_id` cookie, answers errors as
  `{"message": ...}` rather than `errors[]`, and is versioned by nobody. Read the site's
  `GET /internal_api/session` for the expiry rather than assume the preference.
