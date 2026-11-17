---
tags: [auth, token, error-handling, client]
endpoints: [POST /auth/access_token, GET /entity/<type>, POST /entity/<type>/_search, PUT /entity/<type>/<id>, GET /]
phase: auth
scope: api
measured: site-wide, 2026-11-11; one bearer spent before and after its exp, seven forged ones
verdict: Every bearer refusal is 401 code 102 `Unauthorized`; only `detail` differs: `Token Expired` past exp, `Token invalid` for a bad signature, null for garbage or none. Re-mint on 401 code 102.
---

# 133_bearer_expiry

**Q** What does `/api/v1` answer a bearer past its `exp`, and a bearer the site never issued?

**Endpoint** `GET /entity/<type> ; POST /entity/<type>/_search ; PUT /entity/<type>/<id> ; GET /`

**Docs claim** `expires_in` is 600 (probe 001). The REST reference names no status or body for an
expired or invalid token.

**Actual**

```
minted: expires_in 600; exp - iat = 600 s; iat matched the local clock

GET /entity/projects
  fresh token                                  -> 200
  random 40-char string                        -> 401 detail null
  real header and payload, signature altered   -> 401 detail "Token invalid"
  real signature, payload exp + 1 day          -> 401 detail "Token invalid"
  three segments, random signature             -> 401 detail "Token invalid"
  "Authorization: Bearer" and no token         -> 401 detail null
  no Authorization header                      -> 401 detail null
  POST _search, random string                  -> 401 detail null
  GET /api/v1 (the root), random string        -> 200; the root reads no token

  same token at exp - 20 s                     -> 200
  same token at exp + 5 s  GET, POST _search,
                           PUT on an absent id -> 401 detail "Token Expired"
  same token at exp + 66 s                     -> 401 detail "Token Expired"

every 401: {"errors":[{"id":"<uuid>","status":401,"code":102,"title":"Unauthorized",
            "source":null,"detail":"Token Expired","meta":null}]}
  content-type application/json; charset=utf-8; no WWW-Authenticate header
```

**Teaches**
- `exp` is honoured to the second: 200 at 20 s before it, 401 at 5 s after. No grace period. Mint a
  new bearer when the decoded `exp` (probe 027) is near, or on any 401 code 102, and retry once.
- `detail` tells the cases apart; `status`, `code` and `title` do not. `Token Expired` is the one
  a client fixes by minting. `Token invalid` (a token edited or from elsewhere) and `null` (no
  token, or not three segments) mean the client is sending the wrong thing, and minting may not help.
- A write past `exp` is refused before the row is looked up: the `PUT` named an id that does not
  exist and still got the 401, not a 404.
- No `WWW-Authenticate` header is sent, so read the body, not the header, to classify a 401.
- A session token refused at the token endpoint is a 400 code 102 instead (probe 126). Code 102 is
  "authentication failed" at both doors; the status says which door.
