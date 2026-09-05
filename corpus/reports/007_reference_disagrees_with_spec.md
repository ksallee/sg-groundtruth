---
evidence: [findings/042_spec_coverage]
endpoints: [GET /spec.<format>]
kind: docs
status: unreported
scope: api
confirmed: 2026-09-04
measured: site-wide, one fetch of /spec.json and /spec.yaml
summary: Four calls in the published REST reference exist under no spelling in the deployment's own OpenAPI document, which names two of them differently.
---

# 007_reference_disagrees_with_spec

**Expected** The published reference and the OpenAPI document the deployment serves at `/spec.json`
describe the same API.

**Actual** `GET /spec.json` returns 191452 bytes of OpenAPI v3 advertising 62 operations. Four calls the
reference documents are in it under no spelling:

| the reference documents | the site's spec has |
|---|---|
| `PUT /entity/{entity}/{record_id}/_revive` | nothing under that path |
| `POST .../_upload_complete` | nothing under that path |
| `PATCH /schema/{entity}/fields/{field}` | `PUT /schema/<type>/fields/<field>` |
| `PATCH /preferences` | `PUT /preferences/update` |

The `PUT` on a schema field was measured working. `servers[0].url` in the spec ends in `/api/v1.1` while
the reference documents `/api/v1`; a sweep of 20 read-only calls under both prefixes found the same API,
differing only in `api_version` in the root document and the prefix each echoes in its own `links`.

**Reproduce**

```
curl -sS "$SITE/api/v1/spec.json" -H "Authorization: Bearer $TOKEN" \
  | python3 -c 'import json,sys; print("\n".join(sorted(json.load(sys.stdin)["paths"])))'
# No _revive, no _upload_complete. Schema fields and preferences are PUT, not PATCH
```

**Impact** A client written from the reference has four calls that do not exist, and two of them are
spelled closely enough to look like a typo on the caller's side rather than a documentation error. The
prefix mismatch sends anyone comparing the two looking for a version difference that is not there.

**Proposed change** Correct the four paths in the reference to the spellings the deployment serves, and
say in the reference that `/spec.{format}` is the authority for a given deployment. No API change is
needed for any of it.
