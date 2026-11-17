---
tags: [auth, launcher, header, trap]
endpoints: [GET /, POST /internal_api/app_session_request, PUT /internal_api/app_session_request/<sessionRequestId>]
phase: auth
scope: api
measured: site-wide, 2026-11-11, nine pending requests over two runs, none approved
coverage: partial
unmeasured: the create call on a site with authentication_app_session_launcher_enabled false. The probed site has it on and no preference is changed; blocked on the site
verdict: sessionRequestId is 21 characters of A-Za-z0-9_-. url is on the site's host unless the create call sends X-Forwarded-Host, which url copies: a proxy strips that header.
---

# 130_launcher_answers

**Q** What shape is a `sessionRequestId`, is the approval `url` always on the site's own host, and what
does the launcher answer when the site has it switched off?

**Endpoint** `POST /internal_api/app_session_request ; PUT /internal_api/app_session_request/<id> ; GET /api/v1`

**Docs claim** Silent. The launcher is undocumented (probe 052).

**Actual**

```
GET /api/v1  authentication_app_session_launcher_enabled True   user_authentication_method 'oxygen'

POST /internal_api/app_session_request, appName + machineId, nine times
  200 keys ['sessionRequestId', 'url']
  sessionRequestId  length 21 every time; characters seen 0-9 a-z A-Z - _; not a UUID; 9 distinct
  url               https://<site host>/app_session_request/<id>?sticky_id=<sticky_id>
  sticky_id         length 21, same alphabet, never equal to the id

extra request header                                   url host        url scheme, port
none                                                   the site's      https, none
X-Forwarded-Host: example.invalid                      example.invalid https, none
X-Forwarded-Host + X-Forwarded-Proto: http + -Port: 8443  example.invalid https, none
Forwarded: host=example.invalid;proto=https            the site's      https, none
Origin and Referer: https://example.invalid            the site's      https, none

DELETE /internal_api/app_session_request/<id>  404 {"errors":[{"status":404,"code":103,"title":"Not Found",...}]}
PUT    the same id after it                    200 {"approved":false}
PUT    every 30s                               404 for all five by 313s
```

**Teaches**
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
