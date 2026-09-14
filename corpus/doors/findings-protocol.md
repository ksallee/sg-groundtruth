# Findings — protocol: headers, and what a status code is worth

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 004_array_vs_hash

api3_array/api3_hash are a POST _search request Content-Type, not a GET Accept header: as Accept they 406, and entity fields are returned under relationships either way.

- `?fields` can change the value of a field you did ask for, not only drop ones you did not.
  `?fields=display_type,url` on an Icon returns `url` as `""`; adding `image_data` to the same request
  returns the real `data:image/png;base64` URI, and omitting `?fields` returns it too. Narrowing a
  projection is not free, and the wrong answer is a plausible one (`recipes/010`).

**Trap.** Where a bogus name appears decides whether you hear about it:

| bogus name in | result |
|---|---|
| `?fields` | 200, the field absent |
| `filter[]` | 400 `API read() Version.sg_not_a_field doesn't exist.` |
| a filter operator | 400 (probe 017) |

Only `?fields` fails quietly, and a typo there reads as "no data" rather than "wrong field".

- Representation is not negotiable: entity and multi-entity fields are returned under `relationships` as
  `{data, links}` under the default, under `api3_array` and under `api3_hash`, the two 200 `_search` rows
  matching byte for byte. As an Accept header both vendor types 406 with an empty body. Neither one is a
  rendering switch.

- `application/vnd+shotgun.api3_array+json` and `...api3_hash+json` belong on POST `/entity/<type>/_search`
  (and `_summarize`), which rejects `application/json` with 415 (probe 020). What the vendor type selects is
  the `filters` syntax of the request body, not the response:

| Content-Type | `filters` |
|---|---|
| `api3_array` | `[[field, op, value]]` |
| `api3_hash` | `{"logical_operator": "and", "conditions": [[field, op, value]]}` |

  The conditions inside the hash form stay triples. An object of `path`/`relation`/`values` is 400
  `Missing logical operator`, and a bare list under `api3_hash` is 400 `Query is not an Hash`. The
  per-type filters of `POST /entity/_text_search` split the same way, one key at a time (probe 063).

`corpus/findings/004_array_vs_hash.md`

## 028_loud_and_silent

A 400 is trustworthy and usually names the legal set, but a 200 proves nothing: an unknown field, sort key or query param is a no-op, and a batch can return an id for a row it never made.

Every case below is measured elsewhere in the corpus; this entry is the map. The rows marked verified
were re-run read-only on the date of this probe and none had changed.

**Loud, and usually self-documenting.** The rejection names the legal set, which is what made the
field-type matrix cheap to build.

| sent | answer | recorded |
|---|---|---|
| an operator no data type has | 400 naming every legal relation for that data type. All 21 reachable types reject; 16 enumerate, the five unfilterable ones answer `cannot be used in a filter` (verified) | probe 017, `field_types/*` |
| a `_summarize` `type` that is not one of the fourteen | 400 `Request Parameters invalid.`, `source.summary_fields` indexed by position, naming all fourteen (verified) | probe 020 |
| an entity type name that does not exist, in a path or in `/schema` | 404 `Entity type '<x>' does not exist.`, quoting the name back (verified) | `entity_types/Project`, probe 023 |
| a field name that does not exist, in a filter | 400 `API read() <Type>.<field> doesn't exist.` (verified) | probe 026 |
| a `list` value outside `valid_values`, on a write | 400 naming the legal values | `field_types/list` |
| a wrong Python type, on a write or as a filter value | 400 naming the accepted Ruby classes (verified as a filter value) | `field_types/number`, `float`, `percent` |
| a malformed `POST /entity/_batch` body | 400 per missing key, and `request_type must be one of: create, update, delete` | probe 024 |
| sort syntax: empty, a space, a leading `+` | 400 `sort must be filled` or `sort list is not valid` (verified) | probe 026 |

**Silent.** HTTP 200, and the part of the request the server did not understand is gone.

| sent | answer | recorded |
|---|---|---|
| a name in `?fields` that is not a field, on a read | 200, the key absent from `attributes` (verified) | probe 004, probe 023 |
| `?fields` on a create or an update | ignored entirely, both verbs, plain names and dotted paths alike | probe 024 |
| `?fields=display_type,url` on an Icon | 200 with `url` reading `""`, which is indistinguishable from no image; adding `image_data` to the same request returns the real data URI, and omitting `?fields` also returns it | `recipes/010` |
| a `list` filter value outside `valid_values` | 0 rows, no error; inside `in` the junk member is evaluated and matches nothing, so the rest of the list still returns (verified) | `field_types/list` |
| `sort` on an unsortable or unknown field | 200 in default order, identical to no sort, ascending and descending alike (verified) | probe 026, `field_types/summary`, `field_types/url` |
| `["id", "in", [...]]` | 200, id ascending; the order of the list is discarded (verified) | probe 026 |
| any filter on `PageSetting.settings_json` | 200 and the full unfiltered set, while another field on the same type filters (verified) | probe 023 |
| any filter on `EventLogEntry.audit_trail` | the same (verified) | `field_types/jsonb` |
| `filter[]` query params on `POST _search` | ignored entirely: a body filter wins and a bogus param name still returns 200, while the same param filters correctly on `GET /entity/<type>` | probe 030 |
| a batch create missing a required attribute | 200 with an id for a row that does not exist: `GET` 404s, `_search` returns 0, `DELETE` answers 204. The single-create path 400s on the same body | `recipes/002_batch` |

**Silent and destructive.** Six writes return success and either do nothing or destroy data. Not re-run
here: they are recorded, and re-proving them costs rows.

| written | answer | recorded |
|---|---|---|
| `cached_display_name` | 200, the write discarded; the field re-reads as `code` | `field_types/text`, `entity_types/Sequence` |
| `Task.splits`, any well-formed payload | 200, `null` stored | `field_types/serializable` |
| a `multi_entity` update mode spelled in the query string | 200, the whole list replaced instead of appended | `field_types/multi_entity` |
| an already-linked Shot added to a second `Sequence.shots` | 200, the first Sequence's `shots` is now `[]` | `entity_types/Sequence` |
| two `summary_fields` entries over one field | 200, the second overwrites the first, last entry wins | probe 020 |
| `PUT` a Note with `{"replies": []}` | 200, the Reply rows deleted outright | `entity_types/Note` |

**The rule.** Trust a 400: the request layer validates operator, summary type, entity name, field name
and value class, and says what it wanted. Trust nothing about the parts of a request that select or
shape data, because `?fields`, `sort`, a filter value and an update mode are all dropped at 200 when the
server does not recognise them, and a write is confirmed by re-reading the row, never by its status code.

`corpus/findings/028_loud_and_silent.md`

## 051_api_version

/api/v1 and /api/v1.1 are the same API. Across 20 read-only calls the only difference is api_version in the root document and the prefix each echoes in its own links. Any other segment is 404.

- **The two prefixes are one API.** One token authenticates both, every status matches, and every body
  matches once the prefix each echoes in its own `links` is normalised. Everything measured in this
  corpus was measured on `/api/v1` and transfers to `/api/v1.1` unchanged.

- **`links` echo the prefix you called.** A client that starts on `/api/v1.1` stays there through
  `links.next`; there is no silent downgrade to follow, and no rewriting to guard against
  (`006_pagination`).

- `api_version` in the root document reports the prefix that served the request, `1.0` or `1.1`. It is
  not a statement about the site, so it cannot be used to discover which versions a deployment offers.

- **The version is not discoverable from the API.** Both specs advertise only `/api/v1.1`, yet
  `/api/v1` serves the same 62 operations, and there is no listing of valid prefixes. `/api/v1.2` and
  `/api/v2` answer 404 code 103 with `detail` null, the same shape as any unrouted path
  (`045_webhooks`), so a probe cannot tell an unreleased version from a wrong URL.

- Comparing two versions needs two artefacts removed first. Every error body has a per-request
  `errors[].id` that changes on every call, and `/spec.json` contains the literal `/api/v1.1` under
  `servers` whichever prefix served it. Left in, both read as version differences and neither is one.

`corpus/findings/051_api_version.md`

## 062_cors

Every path under `/api/v1` answers the preflight and echoes any `Origin`, credentials true. `/internal_api` and the web paths send no CORS header, so a page on another origin proxies those. **[partial]**

not measured: what a live session cookie authenticates on /api/v1, since allow-credentials invites one, and the presigned upload host, which is not this site. A live session needs a person at a browser

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

`corpus/findings/062_cors.md`
