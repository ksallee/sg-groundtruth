# Endpoints — Other

Every call in this family: what the card records, the edge cases that live on the call, and the verdict of every entry that measured it. Each of those lines names the door holding that entry's rules. The map is `corpus/INDEX.md`.

## `POST /internal_api/autodesk_identity/license_renewal`

Renews the Autodesk Identity licence lease behind the `_session_id` cookie: `{"message": "OK"}` and `license.expiresAt` moves to now plus one day. 401 without the cookie.

- It also moves the session's own `expiresAt`, so one call renews both clocks.

- Whether a REST bearer can still be minted once `license.expiresAt` has passed while the session is
  alive is not measured. On the probed site the licence lease started at the person's browser login and
  the session at the approval, so the licence is the one that runs out first.

- Only measured on a site whose `user_authentication_method` is `oxygen`. What it answers on a site
  without Autodesk Identity is not measured.

**Measured by**

- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`

`corpus/endpoints/post_internal_api_autodesk_identity_license_renewal.md`

## `GET /internal_api/session`

With the session token as the `_session_id` cookie, answers when the session and the licence lease expire, in epoch seconds. Reading it does not renew anything. 401 without the cookie.

- Timestamps are epoch seconds. On the probed site `expiresAt - createdAt` is 86400 on both `app` and
  `license`, which is the site's `User Session Expiry` preference reading one day, and `notifyAt` is
  `expiresAt - 900`.

- `expiresAt` is a sliding window, and this call does not slide it. Two reads five seconds apart return
  the same value. What moves it is any spend of the session token: `POST /auth/access_token` with
  `grant_type=session_token`, `POST /internal_api/session`, or the licence renewal
  (`052_app_session_launcher`). A mint moves it only when the last move was 300s or more ago; the
  two `POST` renewals move it every time.

- `license` is the Autodesk Identity seat lease, separate from the session and renewed separately by
  `POST /internal_api/autodesk_identity/license_renewal`. `expirationReason` names which of the two the
  top-level `expiresAt` reports.

- The error envelope is `{"message": ...}`, as on every `/internal_api` call, not the `errors[]` array.

**Measured by**

- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`

`corpus/endpoints/get_internal_api_session.md`

## `POST /internal_api/session`

Renews the session behind the `_session_id` cookie: `{"message": "OK"}` and `expiresAt` moves to now plus the site's expiry window. 401 without the cookie.

- It is not needed to keep a REST client alive: minting a bearer with `grant_type=session_token` moves
  `expiresAt` by the same amount, recorded at most once every 300s (`052_app_session_launcher`). It is the call for a client that holds a
  session token and has nothing to mint for a while.

- The web app calls it only when the page saw input in the last three minutes; a client renewing on a
  timer keeps a session alive indefinitely, which is the behaviour the site's `User Session Expiry`
  preference exists to bound. Renew on use, not on a clock.

**Measured by**

- `052_app_session_launcher` (findings) — Post appName and machineId, open url in a browser, PUT the id until approved. The sessionToken spends at grant_type=session_token as that person, and every mint renews the session.  
  rules: `doors/findings-auth`

`corpus/endpoints/post_internal_api_session.md`
