---
evidence: [findings/entity_types/Note, findings/entity_types/Reply, findings/028_loud_and_silent]
endpoints: [PUT /entity/<type>/<id>]
kind: api
status: unreported
scope: api
confirmed: 2026-09-04
measured: sandbox project, one Note and its Reply rows written and deleted
summary: A write to Note.replies deletes the Reply rows rather than unlinking them, so PUT with an empty list destroys a thread at 200.
---

# 005_writing_replies_deletes_rows

**Expected** Writing a reverse `multi_entity` view unlinks. `Note.replies` is the reverse of
`Reply.entity`, so a write to it sets or clears that link and leaves the rows.

**Actual**

```
PUT /entity/notes/<id>  {"replies": []}   -> 200
GET the Reply rows that were in the thread -> 404. They are gone, not unlinked
```

The rows are deleted outright. The other reverse pair on the same site behaves the other way:

| field | is the reverse of | writing it |
|---|---|---|
| `Note.replies` | `Reply.entity` | deletes the Reply rows |
| `Sequence.shots` | `Shot.sg_sequence` | moves the link, the Shot rows stay |

Nothing in the request says `delete`, and a `200` with no body change is the only signal.

**Reproduce**

```
# A Note with one Reply on it
curl -sS -X POST "$SITE/api/v1/entity/replies" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"entity":{"type":"Note","id":<note>},"content":"keep me"}'
# 201. Take the Reply id

curl -sS -X PUT "$SITE/api/v1/entity/notes/<note>" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"replies":[]}'
# 200

curl -sS -o /dev/null -w '%{http_code}\n' "$SITE/api/v1/entity/replies/<reply>" \
  -H "Authorization: Bearer $TOKEN"
# 404. The row was deleted, not unlinked
```

**Impact** A client rewriting a Note destroys its thread. The pattern that causes it is ordinary: read a
row, change one field, `PUT` the object back. Any client that round-trips a Note with `replies` in the
payload empties the thread and is told the update succeeded. The rows are not recoverable through the
API, and the two reverse fields on the same site disagree, so a client that learned the safe behaviour
from `Sequence.shots` is wrong here.

**Proposed change** Make a write to `Note.replies` set `Reply.entity`, the way a write to
`Sequence.shots` sets `Shot.sg_sequence`. Failing that, reject writes to the field so the deletion has
to be asked for on `Reply` itself.
