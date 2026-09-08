---
intent: Reach the REST API as a person, with no script key and no password, by having them approve a login in their browser
tags: [auth, token, user, launcher]
endpoints: [POST /internal_api/app_session_request, PUT /internal_api/app_session_request/<sessionRequestId>, POST /auth/access_token]
scope: api
measured: site-wide, two requests approved by one person, tokens spent and refreshed
---

# 012_sign_in_as_a_person

**A person is in this loop.** Step two blocks until someone logged into the site in a browser opens the
page and clicks approve. Nothing in the recipe can do that for them, and a run with nobody at the
browser ends with the request forgotten and a 404.

## Call

```python
import platform, time, webbrowser
import requests

L = f"{site}/internal_api/app_session_request"

# 1. Ask for a login. No credentials of any kind. appName is what the person sees.
made = requests.post(L, data={"appName": "my tool", "machineId": platform.node()}, timeout=30).json()
sid, url = made["sessionRequestId"], made["url"]

# 2. Put the url in front of the person and poll until they approve. A request nobody approves is
#    forgotten after about five minutes and answers 404 from then on, so ask again and show the new
#    url rather than keep polling a dead id.
webbrowser.open(url)
while True:
    r = requests.put(f"{L}/{sid}", timeout=30)
    if r.status_code == 404:
        made = requests.post(L, data={"appName": "my tool", "machineId": platform.node()}, timeout=30).json()
        sid, url = made["sessionRequestId"], made["url"]
        webbrowser.open(url)
        continue
    d = r.json()
    if d.get("approved"):
        break
    time.sleep(2)
session_token, login = d["sessionToken"], d["userLogin"]     # handed out once; keep it now

# 3. Spend it. Same endpoint as a script key, different grant. Repeatable: a session token is not
#    consumed by minting, so hold the session token and mint a bearer whenever expires_in runs out.
t = requests.post(f"{site}/api/v1/auth/access_token",
                  data={"grant_type": "session_token", "session_token": session_token},
                  headers={"Accept": "application/json"}, timeout=30).json()
headers = {"Authorization": f"Bearer {t['access_token']}", "Accept": "application/json"}
```

## Response

Step two, the one 200 that holds the token:

```json
{"approved": true, "sessionToken": "<token>", "userLogin": "<login>"}
```

Step three:

```json
{"token_type": "Bearer", "access_token": "<token>", "expires_in": 600, "refresh_token": "<token>"}
```

The bearer's middle segment, decoded (`027_auth_permissions`):

```json
{"user": {"type": "HumanUser", "id": 253}, "sudo_as_login": null, "auth_type": "session_token", "session_uuid": null}
```

## Notes

- `user` is a `HumanUser`, so every row this bearer writes has the person as `created_by` and, on a
  Version, as `user`, which the web UI shows as Artist. A script key gets the same result only through
  `sudo_as_login`, and that needs an administrator to grant `can_impersonate_this_user` per person
  (`027_auth_permissions`). This needs nobody.
- The person's permission level applies, not a script's. Rows collapse to what they may see
  (`027_auth_permissions`); on the probed site the approver was in the `Admin` set and saw everything.
- `expires_in` is 600, the same as a script token, and `grant_type=refresh_token` on the returned
  `refresh_token` answers 200 with another 600. Re-minting from the session token costs the same one
  call and needs no refresh bookkeeping.
- The session token is the credential to keep, not the bearer. How long the site keeps it alive is the
  site's `User Session Expiry` preference (`052_app_session_launcher`), and is not returned anywhere.
- `machineId` is not checked when polling, so it is a label for the person, not a binding.
