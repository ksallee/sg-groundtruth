---
tags: [discovery, client, paging, protocol]
endpoints: [GET /, GET /spec.<format>, GET /entity/<type>]
phase: protocol
scope: api
measured: site-wide, 20 read-only calls made under each prefix with one token
verdict: /api/v1 and /api/v1.1 are the same API. Across 20 read-only calls the only difference is api_version in the root document and the prefix each echoes in its own links. Any other segment is 404.
---

# 051_api_version

**Q** Does `/api/v1.1` differ from `/api/v1`, and which should a client call?

**Endpoint** `GET /` and 19 other read-only calls under each prefix

**Docs claim** The reference documents `/api/v1`. The deployment's own OpenAPI document, served from
both prefixes, gives `servers[0].url` as `/api/v1.1` and never mentions `/api/v1`.

**Actual**

```
20 read-only calls, each made under both prefixes with one bearer token obtained from /api/v1:
  /, /schema, /schema/Shot, /schema/Shot/fields, /schema/Shot/fields/<field>, /preferences,
  /license_info, /spec.json, /schedule/work_day_rules, /webhook/hooks, /entity/shots,
  /entity/shots/<id>, /entity/shots/<id>/followers, /entity/shots/<id>/relationships/project,
  /entity/projects/<id>, /entity/human_users, _search x2, _summarize, _text_search

  19 identical, same status and same body once the prefix is normalised
   1 genuinely different

GET /  is the one, and the whole difference is one field:
  api_version:  v1 -> '1.0'      v1.1 -> '1.1'
  every other key identical, no key present on one and absent on the other

links echo the prefix you called, they do not rewrite it:
  called v1   -> {"self": "/api/v1/entity/shots?...",   "next": "/api/v1/entity/shots?..."}
  called v1.1 -> {"self": "/api/v1.1/entity/shots?...", "next": "/api/v1.1/entity/shots?..."}

/spec.json is byte-identical from both, and both advertise servers[0].url as /api/v1.1.
operations: v1 62, v1.1 62, identical sets True

/api/v1.2  /api/v2  /api/v0  /api/v1.10  /api/version  /api   -> all 404 code 103, detail null
```

**Teaches**

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
