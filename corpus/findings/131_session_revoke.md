---
tags: [auth, token, launcher]
endpoints: [GET /spec.<format>, GET /user/logout, GET /internal_api/session, POST /auth/access_token]
phase: auth
scope: api
measured: site-wide, 2026-11-11; no cookie and a cookie no session holds, no person's token
coverage: partial
unmeasured: whether /user/logout ends a live session and what a bearer minted before it then reads. Needs a person to approve `python probes/131_session_revoke.py --login`. Blocked on the work
verdict: The REST spec has no revoke or sign-out call. Of five candidate routes only /user/logout answers (302 to login); whether it ends a launcher session is unmeasured.
---

# 131_session_revoke

**Q** Can a client end the session behind a session token, so that signing out of an app signs the
token out on the site?

**Endpoint** `GET /spec.json ; GET /user/logout ; POST /user/logout ; GET /internal_api/session`

**Docs claim** Silent. The REST reference documents `POST /auth/access_token` and no revoke, logout
or session call. Probe 052: the session token is the web app's `_session_id` cookie and lives one
window past its last spend.

**Actual**

```
GET /spec.json  49 paths, 68 operations
  revoke, logout, log_out, sign_out, signout, invalidate, session   nowhere
  operations under /auth                                             POST /auth/access_token

route                          no cookie                    _session_id=<32 random hex>
DELETE /internal_api/session   404 errors[] code 103        404 errors[] code 103
POST   /user/logout            302 -> <site>/user/login     302 -> <site>/user/login
GET    /user/logout            302 -> <site>/user/login     302 -> <site>/user/login
DELETE /api/v1/auth/access_token 404 errors[] code 103      404 errors[] code 103
POST   /api/v1/auth/revoke     404 errors[] code 103        404 errors[] code 103
```

**Pending**

| step | who | command |
|---|---|---|
| approve a fresh launcher request in a browser, then try each route with that token | a person with a login on the site | `python probes/131_session_revoke.py --login` |

After each route `--login` reads `GET /internal_api/session` and mints once. The first route after
which the session reads 401 and the mint is refused is the sign-out call; the probe then reads with a
bearer minted before it, to say whether a 600s bearer outlives sign-out. The token is held in memory
only; `session_token.local.json` is not touched.

**Teaches**
- No documented call ends a session. Until `--login` is run, an app's sign-out can only forget the
  session token; the session on the site then ends one window after the last mint (probe 052).
- `GET /user/logout` is the only route that answers, and a 302 to the login page is its answer with
  no session at all. Confirm a sign-out by reading `GET /internal_api/session` afterwards: 401 is
  ended, 200 is not.
