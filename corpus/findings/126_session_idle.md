---
tags: [auth, token, launcher, error-handling]
endpoints: [POST /auth/access_token, GET /internal_api/session, GET /preferences, GET /]
phase: auth
scope: api
measured: site-wide, 2026-11-11; three never-valid session tokens, no person's token
coverage: partial
unmeasured: a real session token left idle past the window. Needs a person to approve 052 --login, then a day of nobody spending it. Blocked on time
verdict: A session token the site does not accept is 400 code 102 "Can't authenticate session token ending with '<last 4>'" at the token endpoint. No API read exposes the site's session window.
---

# 126_session_idle

**Q** What does a client get back when it spends a session token left idle past the site's window,
and can a client read that window?

**Endpoint** `POST /auth/access_token ; GET /internal_api/session ; GET /preferences`

**Docs claim** The Site Preferences help says an API-generated session expires when its last update
is more than one hour, day or week old, per the `User Session Expiry` setting (probe 052). The REST
reference is silent on reading it.

**Actual**

```
POST /auth/access_token grant_type=session_token
  session_token "0000...0000" (32) -> 400
    {"status":400,"code":102,"title":"Can't authenticate session token ending with '0000'","source":{}}
  session_token ""                 -> 400  code 102 "Can't authenticate session token ending with ''"
  session_token <32 random hex>    -> 400  code 102 "Can't authenticate session token ending with 'd93d'"
GET /internal_api/session  cookie _session_id=<32 random hex>  -> 401 {"message":"Unauthorized"}

GET /preferences?prefs=*  -> 200, 17 keys, none naming session, expiry or timeout
GET /preferences?prefs=user_session_expiry | session_expiry | api_session_expiry | session_timeout
                          -> 200 data={}
GET /api/v1               -> one key naming a session: authentication_app_session_launcher_enabled
```

**What is set up for the idle case**

| step | who | command |
|---|---|---|
| sign in once, approve in a browser | a person with a login on the site | `python probes/052_app_session_launcher.py --login` |
| leave it alone for more than the window | nobody | do not run `052 --check`: spending the token renews the session (probe 052) |
| spend it | anyone | `python probes/126_session_idle.py --idle` |

`--idle` reads `GET /internal_api/session` first (a GET does not renew), then mints, and prints both
answers whole. The token stays in the gitignored `session_token.local.json`.

**Teaches**
- Treat 400 code 102 from `grant_type=session_token` as "send the person through sign-in again".
  The title quotes the token's last four characters and nothing else, so an expired, revoked or
  mistyped token cannot be told apart from it. Whether an expired one answers the same is unmeasured.
- The window is not readable: `/preferences` exposes 17 display and scheduling keys and silently
  answers `{}` for any other name. Read `expiresAt` from `GET /internal_api/session` while the token
  is live (probe 052) instead.
- Writing the window was not tried: `PUT /preferences/update` is 400 code 111 for every preference
  on the probed site (probes 047, 114).
