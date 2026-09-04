---
endpoint: GET /
coverage: measured
tags: [auth, discovery]
scope: api
measured: site-wide
verdict: The site's login configuration, answered without a token. Read `user_authentication_method` here before choosing a grant type.
---

# GET /

**Params**

| part | value |
|---|---|
| path | `/api/v1`, the versioned root itself |
| auth | none needed |

**Sample requests**

```python
r = c.get("/api/v1")
```

On the probed site:

```json
{
  "data": {
    "shotgun_version": "v8.89.0.9724 (build 47ec49f)",
    "api_version": "1.0",
    "unified_login_flow_enabled": true,
    "authentication_app_session_launcher_enabled": true,
    "user_authentication_method": "oxygen",
    "site_id": "<id>",
    "site_name": "<site>",
    "os": "Amazon Linux"
  }
}
```

**Response codes**

| status | when |
|---|---|
| 200 | always |

**Edge cases**

- `user_authentication_method` decides whether a human grant is available at all. `oxygen` on the probed
  site means the identity provider owns the login, so `password` will not work for a person there even
  though the token endpoint accepts the grant type.
- `shotgun_version` is the only version string the API exposes. Anything conditioned on server version
  reads it here rather than inferring it from behaviour.

**Links**

- `endpoints/post_auth_access_token`
- `findings/027_auth_permissions`