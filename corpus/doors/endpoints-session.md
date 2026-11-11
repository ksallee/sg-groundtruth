# Endpoints — Session

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `GET /`

The site's login configuration, answered without a token. Read `user_authentication_method` here before choosing a grant type.

- `user_authentication_method` decides whether a human grant is available at all. `oxygen` on the probed
  site means the identity provider owns the login, so `password` will not work for a person there even
  though the token endpoint accepts the grant type.

- `authentication_app_session_launcher_enabled` true means a person can sign in without a script key:
  `POST /internal_api/app_session_request`, approved in a browser (probe 052). On the probed site it is
  the only grant a person has, because `oxygen` refuses `password`.

- `shotgun_version` is the only version string the API exposes. Anything conditioned on server version
  reads it here rather than inferring it from behaviour.

**Measured by**

- `027_auth_permissions` (findings) — The token endpoint accepts password and session_token. Impersonation is the OAuth2 scope sudo_as_login:<login>, never a body field, and a lower level reads far fewer rows and as many fields.  
  rules: `doors/findings-auth`
- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`
- `126_session_idle` (findings) — The token endpoint refuses a session token it does not accept with 400 code 102 in errors[], "Can't authenticate session token ending with '<last 4>'". No API read exposes the session window.  
  rules: `doors/findings-auth`
- `130_launcher_answers` (findings) — sessionRequestId is 21 characters of A-Za-z0-9_-. url is on the site's host unless the create call sends X-Forwarded-Host, which url copies: a proxy strips that header.  
  rules: `doors/findings-auth`
- `133_bearer_expiry` (findings) — Every bearer refusal is 401 code 102 `Unauthorized`; only `detail` differs: `Token Expired` past exp, `Token invalid` for a bad signature, null for garbage or none. Re-mint on 401 code 102.  
  rules: `doors/findings-auth`
- `051_api_version` (findings) — /api/v1 and /api/v1.1 are the same API. Across 20 read-only calls the only difference is api_version in the root document and the prefix each echoes in its own links. Any other segment is 404.  
  rules: `doors/findings-protocol`
- `062_cors` (findings) — Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.  
  rules: `doors/findings-protocol`
- `129_hosted_domains` (findings) — The probed site answers only at its own host; its name under shotgunstudio.com is 404 HTML, no redirect. Both domains resolve any name, so allowlist the configured host, not a suffix.  
  rules: `doors/findings-protocol`

`corpus/endpoints/get_root.md`

## `POST /auth/access_token`

Form-encode it. `application/json` is 415 naming the one legal type, and the 600s bearer is cheaper to re-mint than the refresh_token is to use.

- A wrong `Content-Type` is reported as a problem with the body, not the header. Sending
  `application/json` is 415 here, and probe 001 records the form body under a JSON content type
  reaching `400 Invalid JSON body ... Empty input`. Neither error says "header".

- `refresh_token` is a second bearer credential in the response. Redact it wherever the access token is
  redacted; it is the value `_lib.scrub` used to let through.

- 600 seconds is short enough that a long job re-auths mid-run. Refreshing a minute early costs one call
  and removes the refresh path entirely.

**Measured by**

- `001_auth` (findings) — Send the token request as `application/x-www-form-urlencoded`: `application/json` is 400 Invalid JSON body. client_credentials returns a 600s bearer, so ignore the refresh_token and re-auth.  
  rules: `doors/findings-auth`
- `027_auth_permissions` (findings) — The token endpoint accepts password and session_token. Impersonation is the OAuth2 scope sudo_as_login:<login>, never a body field, and a lower level reads far fewer rows and as many fields.  
  rules: `doors/findings-auth`
- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`
- `126_session_idle` (findings) — The token endpoint refuses a session token it does not accept with 400 code 102 in errors[], "Can't authenticate session token ending with '<last 4>'". No API read exposes the session window.  
  rules: `doors/findings-auth`
- `131_session_revoke` (findings) — The REST spec has no revoke or sign-out call. Of five candidate routes only /user/logout answers (302 to login); whether it ends a launcher session is unmeasured.  
  rules: `doors/findings-auth`
- `133_bearer_expiry` (findings) — Every bearer refusal is 401 code 102 `Unauthorized`; only `detail` differs: `Token Expired` past exp, `Token invalid` for a bad signature, null for garbage or none. Re-mint on 401 code 102.  
  rules: `doors/findings-auth`
- `062_cors` (findings) — Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.  
  rules: `doors/findings-protocol`
- `012_sign_in_as_a_person` (recipes) — Reach the REST API as a person, with no script key and no password, by having them approve a login in their browser  
  rules: `doors/recipes`

`corpus/endpoints/post_auth_access_token.md`

## `POST /internal_api/app_session_request`

Send `appName` and `machineId`, form or JSON, with no token and no cookie. The answer is a `sessionRequestId` to poll and a `url` a logged-in person opens in a browser to approve.

- `sessionRequestId` and `sticky_id` are each 21 characters of `A-Za-z0-9_-`, and differ
  (`130_launcher_answers`).

- `url` takes its host from an `X-Forwarded-Host` request header. A proxy in front of this call strips
  that header, or the person is sent to the proxy's host (`130_launcher_answers`).

- There is no withdraw: `DELETE /internal_api/app_session_request/<id>` is 404 code 103.

- The error envelope is `{"message": ...}`, not the `errors[]` envelope every `/api/v1` call answers with.
  A client that reads `errors[0].title` reads nothing here.

- `url` opened without a site cookie answers 302 to the site's login page with the approval page as
  `return_path`, so the person logs in with whatever the site uses, Autodesk Identity included, and lands
  back on the approval.

- A request nobody approves is forgotten after about five minutes (`052_app_session_launcher`), so a
  client waiting on a person has to be ready to issue a new one and show the new `url`.

- On the probed site `user_authentication_method` is `oxygen`, so this is the only way a person, rather
  than a script, reaches the REST API there.

**Measured by**

- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`
- `130_launcher_answers` (findings) — sessionRequestId is 21 characters of A-Za-z0-9_-. url is on the site's host unless the create call sends X-Forwarded-Host, which url copies: a proxy strips that header.  
  rules: `doors/findings-auth`
- `062_cors` (findings) — Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.  
  rules: `doors/findings-protocol`
- `012_sign_in_as_a_person` (recipes) — Reach the REST API as a person, with no script key and no password, by having them approve a login in their browser  
  rules: `doors/recipes`

`corpus/endpoints/post_internal_api_app_session_request.md`

## `PUT /internal_api/app_session_request/<sessionRequestId>`

Poll it with no body. `{"approved": false}` while pending; once, `{"approved": true, "sessionToken", "userLogin"}`; then 404 forever. Forgotten, denied and unknown all read the same 404.

- **The token is handed out once.** The `PUT` after the approved one is 404, so a client that polls from
  two places loses the token to whichever asked first. Keep `sessionToken` from the one response that holds it.

- The three 404 causes are one body. A client cannot tell a denied request from a forgotten one or a
  typo in the id, and should say so to the person rather than guess.

- On the probed site, an Autodesk Identity site, `userLogin` is the person's email address. Treat it as
  identifying.

- `sessionToken` is what `POST /auth/access_token` takes as `session_token`. It is a credential for the
  person who approved: store it where a key would be stored.

**Measured by**

- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`
- `130_launcher_answers` (findings) — sessionRequestId is 21 characters of A-Za-z0-9_-. url is on the site's host unless the create call sends X-Forwarded-Host, which url copies: a proxy strips that header.  
  rules: `doors/findings-auth`
- `062_cors` (findings) — Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.  
  rules: `doors/findings-protocol`
- `012_sign_in_as_a_person` (recipes) — Reach the REST API as a person, with no script key and no password, by having them approve a login in their browser  
  rules: `doors/recipes`

`corpus/endpoints/put_internal_api_app_session_request_id.md`
