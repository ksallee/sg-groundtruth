---
tags: [auth, client, token]
scope: api
verdict: client_credentials works and returns a 600s bearer token; a refresh_token comes back but re-authing is simpler and costs one call.
---

# 001_auth

**Q** What does the token endpoint return, and how long is a token good for?

**Endpoint** `POST /api/v1/auth/access_token ; GET /api/v1/entity/projects`

**Docs claim** client_credentials with a script name and key returns a bearer token; `expires_in` is documented as 600s.

**Actual**

```
POST auth -> 200
{
  "token_type": "Bearer",
  "access_token": "<str, 415 chars>",
  "expires_in": 600,
  "refresh_token": "<str, 527 chars>"
}

GET /entity/projects -> 200
projects: [(63, 'demo_show'), (70, 'sample_show'), (78, 'template_show')]

=== Content-Type on the token endpoint
  'text/plain' -> 415
    "title": "Unsupported Content-Type 'text/plain'",
    "source": {"content_type": "Content-Type must be one of: 'application/x-www-form-urlencoded'."}
  'application/json' -> 400
    "title": "Invalid JSON body",
    "source": {"body": "Empty input (after ) at line 1, column 1 "}
```

**Teaches**
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
