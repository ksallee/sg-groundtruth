---
endpoint: PUT /internal_api/app_session_request/<sessionRequestId>
coverage: measured
tags: [auth, token, user, launcher]
scope: api
measured: site-wide, polled on pending, approved, spent, forgotten and unknown ids
verdict: Poll it with no body. `{"approved": false}` while pending; once, `{"approved": true, "sessionToken", "userLogin"}`; then 404 forever. Forgotten, denied and unknown all read the same 404.
---

# PUT /internal_api/app_session_request/<sessionRequestId>

Step two of the App Session Launcher. The client polls this while a person approves the request in a
browser, and the one 200 with `approved: true` is the only time the session token is handed out.

**Params**

| part | value |
|---|---|
| path | `<site>/internal_api/app_session_request/<sessionRequestId>`, the id from the `POST` |
| auth | none |
| body | none needed. `machineId` sent here is ignored, right or wrong |

**Sample requests**

```python
r = requests.put(f"{site}/internal_api/app_session_request/{sid}", timeout=30)
```

Before the person has approved:

```json
{"approved": false}
```

After:

```json
{"approved": true, "sessionToken": "<token>", "userLogin": "<login>"}
```

Any call after that one, and any call on an id the site does not hold:

```json
{"message": "Not Found"}
```

**Response codes**

| status | when |
|---|---|
| 200 | pending, `approved` false, or approved, with `sessionToken` and `userLogin` |
| 404 | `{"message": "Not Found"}`. The id is unknown, the token was already handed out, or nobody approved it in time |
| 404 | `GET` or `POST` on this path. JSON:API envelope, code 103 |

**Edge cases**

- **The token is handed out once.** The `PUT` after the approved one is 404, so a client that polls from
  two places loses the token to whichever asked first. Keep `sessionToken` from the one response that holds it.
- The three 404 causes are one body. A client cannot tell a denied request from a forgotten one or a
  typo in the id, and should say so to the person rather than guess.
- On the probed site, an Autodesk Identity site, `userLogin` is the person's email address. Treat it as
  identifying.
- `sessionToken` is what `POST /auth/access_token` takes as `session_token`. It is a credential for the
  person who approved: store it where a key would be stored.

**Links**

- `endpoints/post_internal_api_app_session_request`
- `endpoints/post_auth_access_token`
- `findings/052_app_session_launcher`
- `recipes/012_sign_in_as_a_person`
