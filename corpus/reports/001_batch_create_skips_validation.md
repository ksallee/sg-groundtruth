---
evidence: [recipes/002_batch, findings/028_loud_and_silent]
endpoints: [POST /entity/_batch]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: sandbox project, one Version created and deleted
summary: A create inside POST /entity/_batch skips the required-attribute validation the single-create path applies, and answers 200 with the id of a row no read can reach.
---

# 001_batch_create_skips_validation

**Expected** A `create` request inside a batch is validated the way `POST /entity/<type>` validates the
same body, and every id in a 200 response addresses a row `GET` can read.

**Actual**

`POST /entity/versions` with no `project` is rejected:

```
400  API create() missing 'project' attribute: {"code" => "v001"}
```

The same create inside a batch is not:

| call | answer |
|---|---|
| `POST /entity/_batch`, one `create`, no `project` | `200`, `id` 29932, a create row with no `project` relationship |
| `GET /entity/versions/29932` | `404 Version: 29932 not found` |
| `POST /entity/versions/_search` on its `code`, site-wide | `200`, 0 rows |
| `DELETE /entity/versions/29932` | `204` |

The row exists. The id from the create response is the only thing that reaches it, and only to delete it.

**Reproduce**

```
curl -sS -X POST "$SITE/api/v1/entity/_batch" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"requests":[{"request_type":"create","entity":"Version","data":{"code":"v001"}}]}'
# 200. Take data[0].id

curl -sS -o /dev/null -w '%{http_code}\n' "$SITE/api/v1/entity/versions/<id>" \
  -H "Authorization: Bearer $TOKEN"
# 404

curl -sS -X POST "$SITE/api/v1/entity/versions" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"code":"v001"}'
# 400, the same body on the single-create path
```

**Impact** A client that writes through `_batch` records ids that no later read resolves. The rows are
invisible to `_search`, so a reconciliation pass finds nothing to clean up and the only handle on them is
a create response the client has already discarded. The two paths disagree, so a client that validates
against the single-create contract is still wrong inside a batch.

**Proposed change** Run the same attribute validation for a batch `create` as for
`POST /entity/<type>`, and reject the batch with the 400 that path already returns. The endpoint rolls
the whole batch back on any other rejection, so the behaviour is already there for every failure but
this one.
