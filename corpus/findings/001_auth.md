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
```

**Teaches**
- `expires_in` is 600 exactly, as documented. A long-running client must handle expiry, not assume one token per session.
- A `refresh_token` is issued but buys nothing here: re-authing is one call with credentials already in hand, so the client re-auths instead of storing refresh state.
- The token is a plain bearer string; nothing about the grant is site-specific.
