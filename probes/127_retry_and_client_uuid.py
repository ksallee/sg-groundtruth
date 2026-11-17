"""Q: after a create times out on the client, how does it learn what committed, and does a client
UUID field, stock or `unique`, stop the retry from duplicating the row?

Recipe 002 found that a batch whose client gave up at its read timeout had committed every row, and
that no request id lets a client ask. sg-onset retries from a flaky set network, so it needs a key it
can look up before it re-sends. Measured here:

  1. a batch of Version creates abandoned by the client after 10 ms: what committed, and when it
     became readable
  2. an `Idempotency-Key` header on two identical creates: honoured or ignored
  3. a client UUID in the stock text field `description`: the lookup, and the duplicate on retry
  4. the same in a custom text field created with `unique: true` (probe 116 found the property is
     accepted at create and fixed after): single creates, a batch, two in one batch, case changes

Writes: Versions `zzprobe_127_*` in the sandbox, all deleted, and one schema field
`sg_zzprobe_127_client_uuid` on Version, retired before exit. The retired name stays spent until
the Trash page is emptied in the web interface (probe 019).

    python probes/127_retry_and_client_uuid.py --write
"""
import json
import time
import uuid

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
if not _lib.writes_allowed():
    raise SystemExit("127_retry_and_client_uuid writes to the site; re-run with --write")
SB = _lib.sandbox_id(c, env)
PROJ = {"type": "Project", "id": SB}
RUN = uuid.uuid4().hex[:8]
FIELD = "sg_zzprobe_127_client_uuid"
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:500]
    except ValueError:
        return repr(r.text[:300])


def find(filters):
    r = c.post("/entity/versions/_search", headers=ARR, json={
        "filters": [["project", "is", PROJ]] + filters, "fields": ["code"], "page": {"size": 200}})
    return [x["id"] for x in r.json().get("data", [])] if r.ok else errs(r)


field_made = False
with _lib.Created(c) as made:
    def keep(ids):
        for i in ids:
            if ("versions", i) not in made.rows:
                made.add("versions", i)

    # ------------------------------------------------ 1. abandoned batch
    out("===== 1. POST /entity/_batch, 20 creates, client read timeout 10 ms")
    prefix = f"zzprobe_127_{RUN}_batch_"
    body = {"requests": [{"request_type": "create", "entity": "Version",
                          "data": {"project": PROJ, "code": f"{prefix}{i:02d}"}} for i in range(20)]}
    c.get("/entity/versions", params={"page[size]": 1})  # a fresh bearer, so the batch is the timed call
    t0 = time.time()
    try:
        requests.post(f"{c.site}/api/v1/entity/_batch", json=body, timeout=(10, 0.01),
                      headers={"Authorization": f"Bearer {c._token}", "Accept": "application/json"})
        out("  the response arrived inside 10 ms; the timeout did not fire")
    except requests.exceptions.ReadTimeout as e:
        out(f"  client raised {type(e).__name__} after {time.time() - t0:.2f}s")
    except Exception as e:  # noqa: BLE001
        out(f"  client raised {type(e).__name__}: {str(e)[:200]}")
    for wait in (0, 1, 3, 10, 30):
        time.sleep(wait)
        got = find([["code", "starts_with", prefix]])
        out(f"  +{time.time() - t0:5.1f}s rows readable with that code prefix: {len(got) if isinstance(got, list) else got}")
        if isinstance(got, list):
            keep(got)
            if len(got) == 20:
                break

    # ------------------------------------------------ 2. Idempotency-Key
    out("\n===== 2. two identical creates carrying the same Idempotency-Key header")
    key = str(uuid.uuid4())
    ids = []
    for _ in range(2):
        r = c.post("/entity/versions", json={"project": PROJ, "code": f"zzprobe_127_{RUN}_idem"},
                   headers={"Idempotency-Key": key, "X-Idempotency-Key": key})
        out(f"  -> {r.status_code} id {r.json()['data']['id'] if r.ok else errs(r)}")
        if r.ok:
            ids.append(r.json()["data"]["id"])
    keep(ids)
    out(f"  distinct rows: {len(set(ids))}; x-request-id on the response: "
        f"{'x-request-id' in {k.lower() for k in r.headers}}")

    # ------------------------------------------------ 3. stock text field
    out("\n===== 3. client UUID in the stock text field Version.description")
    u = str(uuid.uuid4())
    r = c.post("/entity/versions", json={"project": PROJ, "code": f"zzprobe_127_{RUN}_desc",
                                         "description": u})
    keep([r.json()["data"]["id"]])
    out(f"  create -> {r.status_code}; lookup straight after, description is <uuid>: {len(find([['description', 'is', u]]))}")
    out(f"  lookup with the uuid uppercased: {len(find([['description', 'is', u.upper()]]))}")
    r = c.post("/entity/versions", json={"project": PROJ, "code": f"zzprobe_127_{RUN}_desc",
                                         "description": u})
    keep([r.json()["data"]["id"]])
    out(f"  the same create again -> {r.status_code}; rows holding the uuid now: {len(find([['description', 'is', u]]))}")

    # ------------------------------------------------ 4. unique text field
    out(f"\n===== 4. a custom text field created with unique: true, {FIELD}")
    try:
        r = c.post("/schema/Version/fields", json={"data_type": "text", "properties": [
            {"property_name": "name", "value": "zzprobe 127 client uuid"},
            {"property_name": "unique", "value": True}]})
        if r.status_code == 400 and "retired" in r.text:
            r = c.post(f"/schema/Version/fields/{FIELD}", params={"revive": "true"})
            out(f"  {FIELD} retired by an earlier run; revive -> {r.status_code}")
        else:
            out(f"  POST /schema/Version/fields text unique -> {r.status_code} "
                + (r.json()["links"]["self"].rsplit("/", 1)[-1] if r.status_code == 201 else errs(r)))
        field_made = r.status_code in (201, 204)
        if field_made:
            f = c.get(f"/schema/Version/fields/{FIELD}").json()["data"]
            out(f"  unique reads {json.dumps(f['unique'])}")
            u = str(uuid.uuid4())

            def create(val, label):
                r = c.post("/entity/versions", json={"project": PROJ, "code": f"zzprobe_127_{RUN}_u",
                                                     FIELD: val})
                if r.ok:
                    keep([r.json()["data"]["id"]])
                out(f"  {label:<44} -> {r.status_code} {'' if r.ok else errs(r)}")

            create(u, "create with <uuid>")
            create(u, "the same create again")
            create(u.upper(), "the uuid uppercased")
            create(" " + u, "the uuid with a leading space")
            r = c.post("/entity/_batch", json={"requests": [
                {"request_type": "create", "entity": "Version",
                 "data": {"project": PROJ, "code": f"zzprobe_127_{RUN}_ub", FIELD: u}}]})
            out(f"  {'a batch create with <uuid>':<44} -> {r.status_code} {'' if r.ok else errs(r)}")
            if r.ok:
                keep([x["id"] for x in r.json()["data"] if isinstance(x, dict) and "id" in x])
            u2 = str(uuid.uuid4())
            r = c.post("/entity/_batch", json={"requests": [
                {"request_type": "create", "entity": "Version",
                 "data": {"project": PROJ, "code": f"zzprobe_127_{RUN}_ub2", FIELD: u2}}] * 2})
            out(f"  {'one batch, two creates with a new uuid':<44} -> {r.status_code} {'' if r.ok else errs(r)}")
            if r.ok:
                keep([x["id"] for x in r.json()["data"] if isinstance(x, dict) and "id" in x])
            out(f"  rows holding <uuid>: {len(find([[FIELD, 'is', u]]))}; holding the batch uuid: "
                f"{len(find([[FIELD, 'is', u2]]))}")
            mine = find([["code", "starts_with", f"zzprobe_127_{RUN}_u"]])
            keep(mine if isinstance(mine, list) else [])
            out(f"  an update setting a second row to <uuid>: ", )
            others = [i for i in (mine if isinstance(mine, list) else [])
                      if c.get(f"/entity/versions/{i}", params={"fields": FIELD}).json()["data"]["attributes"][FIELD] != u]
            if others:
                r = c.put(f"/entity/versions/{others[0]}", json={FIELD: u})
                rows[-1] += f"{r.status_code} {'' if r.ok else errs(r)}"
    finally:
        _lib.emit("127_retry_and_client_uuid", "\n".join(rows), env)

if field_made:
    r = c.delete(f"/schema/Version/fields/{FIELD}")
    print(f"  retired /schema/Version/fields/{FIELD} -> {r.status_code}")
