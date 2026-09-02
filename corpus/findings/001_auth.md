---
tags: [auth, client, token]
verdict: client_credentials works; token lives 600s; refresh_token returned but the client re-auths instead.
---

# 001_auth

**Endpoint** `POST /api/v1/auth/access_token  +  GET /api/v1/entity/projects`

**Docs claim** client_credentials with script name/key returns a bearer token; expires_in documented as 600s.

**Actual**

```
POST auth -> 200
payload keys/values: {
  "token_type": "Bearer",
  "access_token": "<str, 415 chars>",
  "expires_in": 600,
  "refresh_token": "<str, 527 chars>"
}

GET /entity/projects -> 200
projects: [(63, 'Tundra Quartz Inlet'), (70, 'Fjord Inlet Vapor'), (78, 'Jules Quarry')]
```

**Verdict** client_credentials works; token lives 600s; refresh_token returned but the client re-auths instead.
