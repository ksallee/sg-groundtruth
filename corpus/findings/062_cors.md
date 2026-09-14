---
tags: [cors, browser, header, launcher, client]
endpoints: [GET /, POST /auth/access_token, POST /entity/<type>/_search, GET /schema, POST /internal_api/app_session_request, PUT /internal_api/app_session_request/<sessionRequestId>, GET /internal_api/session, POST /internal_api/session]
phase: protocol
scope: api
measured: site-wide, five origins over /api/v1, the four /internal_api calls and two static web paths
coverage: partial
unmeasured: what a live session cookie authenticates on /api/v1, since allow-credentials invites one, and the presigned upload host, which is not this site. A live session needs a person at a browser
verdict: Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those.
---

# 062_cors

**Q** Does the REST API answer a CORS preflight and reflect the origin, and do the App Session
Launcher endpoints?

**Endpoint** `OPTIONS /api/v1/<anything> ; POST /auth/access_token ; POST /entity/<type>/_search ; GET /schema ; POST /internal_api/app_session_request ; GET /internal_api/session`

**Docs claim** Silent. The REST documentation describes no browser client, names no allowed origin,
and does not say the API is reachable from a page at all.

**Actual**

```
OPTIONS, Origin: https://example.invalid, Access-Control-Request-Method: POST,
                                          Access-Control-Request-Headers: authorization,content-type
  /api/v1/auth/access_token       200  access-control-allow-origin: https://example.invalid
  /api/v1/entity/shots/_search    200  access-control-allow-credentials: true
  /api/v1/schema                  200  access-control-allow-methods: GET, POST, PUT, PATCH, DELETE
  /api/v1                         200  access-control-allow-headers: authorization,content-type
                                       access-control-max-age: 3600
                                       vary: Origin, Access-Control-Request-Method
  /internal_api/app_session_request, PUT .../<id>, GET and POST /internal_api/session
                                  200  no CORS header of any kind
  /images/sg_icon_image_map.png, /dist/production/stylesheets/login.css
                                  405  no CORS header of any kind

the same preflight, one origin at a time, allow-credentials true on every one
  https://example.invalid  http://localhost:5173  null  banana  <the site itself>   each echoed back

Access-Control-Request-Method  GET POST PUT PATCH DELETE, any case  -> the fixed list above
                               TRACE, BREW                          -> 200, no CORS header
Access-Control-Request-Headers authorization content-type accept accept-language content-language
                               range origin                         -> echoed verbatim, case as sent
                               any other name, alone or in a list   -> 200, no CORS header
  no Origin -> 200, vary only.  A preflight answer is 0 bytes with no content-type

the request itself, with Origin: https://example.invalid
  GET /api/v1 200, POST /auth/access_token 200 and 400, GET /schema 200,
  POST _search 200 on the vendor content type and 415 on application/json (probe 004)
    allow-origin echoed and allow-credentials true; never allow-headers, never expose-headers
  GET /internal_api/session 401, PUT /internal_api/app_session_request/<unknown> 404,
  GET /images/sg_icon_image_map.png 200, GET /dist/.../login.css 200      no CORS header
  OPTIONS /api/v1/<path no route serves> 200 echoed;  OPTIONS /<path outside /api/v1> 200 nothing
```

**Teaches**
- `/api/v1` reflects whatever `Origin` reaches it. There is no allowlist to be on and nothing to
  register: `null`, an `http://localhost` origin and the string `banana` all come back in
  `access-control-allow-origin`, each with `access-control-allow-credentials: true`, so a browser
  permits a credentialed cross-origin call from any page to any Flow PT site.
- `Vary: Origin, Access-Control-Request-Method` is on every answer, so a shared cache does not hand
  one origin the reply meant for another.
- The preflight is answered in front of the API rather than by the route. Any path under `/api/v1`
  answers 200 with the echo, including one no route serves; a path outside `/api/v1` answers 200
  with nothing. It takes no token, and the answer has an empty body.
- What is allowed is fixed, except the header list, which is an echo of a closed set:

  | asked for | answered |
  |---|---|
  | `Access-Control-Request-Method` one of `GET` `POST` `PUT` `PATCH` `DELETE` | `access-control-allow-methods: GET, POST, PUT, PATCH, DELETE` |
  | `Access-Control-Request-Method: TRACE` or `BREW` | 200 with every CORS header dropped, which fails the preflight |
  | `Access-Control-Request-Headers` drawn from `authorization`, `content-type`, `accept`, `accept-language`, `content-language`, `range`, `origin` | the same string echoed back |
  | one name outside that set, even beside a legal one | 200 with every CORS header dropped |

  A page may send `Authorization` and the `application/vnd+shotgun.api3_hash+json` content type
  (probe 004), and nothing else: `cache-control`, `if-none-match` and `x-requested-with` fail the
  preflight and the request is never made. The content type is not a safelisted value, so every
  call is preflighted, and `access-control-max-age: 3600` is what keeps that to one extra round
  trip per hour.
- No `access-control-expose-headers`, so script reads only the six safelisted response headers
  (`cache-control`, `content-language`, `content-type`, `expires`, `last-modified`, `pragma`).
- `etag` and `x-request-id` are on the response and unreadable from a page, and `if-none-match` is
  refused at the preflight, so a browser client has no conditional request and no request id to
  quote in a support ticket.
- What a page on another origin can call:

  | | from a page on another origin |
  |---|---|
  | everything under `/api/v1` | direct. Mint a token, read, filter, write. The `_upload` flow then leaves the site for a presigned host, whose own answer is not measured here |
  | `/internal_api/*`: the App Session Launcher and the session | through a proxy. The browser discards an answer with no `access-control-allow-origin`, at 200, 401 and 404 alike |
  | `/images/...`, `/dist/...` | as an `<img>` or a `<link>`, which need no CORS. Not through `fetch`, and pixels read back off a canvas are tainted |

  So a page signs a person in by having its own server make the two launcher calls of probe 052,
  opening the returned `url` in a tab for the person to approve, and then minting the bearer from
  the page, since `POST /auth/access_token` is one of the calls it may make. The alternative, a
  page holding `client_credentials`, ships the script key to every visitor.
