"""Q: in a `_batch` create on a custom entity, is a numeric string accepted in a float field, and is
`created_at` honoured, as they are on a single `POST`?

`field_types/float` measured `"1.0"` accepted and an Integer refused on a single write to a stock
field; probe 070 measured `created_at` set by a create body on Note, Task and Version. sg-onset
creates captures in batches on a custom entity and stamps the capture time. Report 001 says a batch
create skips validation a single create applies, so each value is sent both ways.

On the first enabled custom slot, with one float field `sg_zzprobe_137_float` created for it.
Every create is sent once as a single `POST` and once as a one-request `_batch` (a batch rolls back
whole, recipe 002, so a refusal would hide its neighbours).

Writes in the sandbox, behind `--write`. Rows `zzprobe_137_*` deleted on exit; the field retired.

    python probes/137_batch_create_coercion.py --write
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 137 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
SLUG = f"custom_entity{CE[12:]}s"
F = "sg_zzprobe_137_float"
rows = []

CASES = [
    ("float \"1.5\"", {F: "1.5"}),
    ("float \" 2.25 \"", {F: " 2.25 "}),
    ("float \"3\"", {F: "3"}),
    ("float 1.5", {F: 1.5}),
    ("float 1 (Integer)", {F: 1}),
    ("float \"abc\"", {F: "abc"}),
    ("float \"1e3\"", {F: "1e3"}),
    ("created_at Z", {"created_at": "2020-01-02T03:04:05Z"}),
    ("created_at +05:00, .123", {"created_at": "2020-01-02T03:04:05.123+05:00"}),
    ("created_at and updated_at", {"created_at": "2020-01-02T03:04:05Z", "updated_at": "2020-01-03T00:00:00Z"}),
    ("created_at \"bogus\"", {"created_at": "bogus"}),
]


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        e = r.json()["errors"][0]
        return f"code {e.get('code')} {e.get('title')[:260]}"
    except (ValueError, KeyError, IndexError, TypeError):
        return repr(r.text[:300])


def readback(rid, keys):
    a = c.get(f"/entity/{SLUG}/{rid}", params={"fields": ",".join(keys)}).json()["data"]["attributes"]
    return {k: a.get(k) for k in keys}


field_made = False
with _lib.Created(c) as made:
    try:
        if c.get(f"/schema/{CE}/fields/{F}").ok:
            out(f"{F} live from an interrupted run; reused")
            field_made = True
        else:
            r = c.post(f"/schema/{CE}/fields", json={"data_type": "float", "properties": [
                {"property_name": "name", "value": "zzprobe 137 float"}]})
            out(f"POST /schema/<custom slot>/fields float -> {r.status_code} "
                + (r.json()["links"]["self"].rsplit("/", 1)[-1] if r.ok else errs(r)))
            field_made = r.status_code == 201
        out(f"\n{'sent':<28} {'single POST':<46} _batch create")
        for i, (label, extra) in enumerate(CASES):
            body = {"project": P, "code": f"zzprobe_137_{i:02d}", **extra}
            keys = list(extra)
            s = c.post(f"/entity/{SLUG}", json=body)
            if s.status_code == 201:
                made.add(SLUG, s.json()["data"]["id"])
                sres = f"201 {json.dumps(readback(s.json()['data']['id'], keys))}"
            else:
                sres = f"{s.status_code} {errs(s)}"
            b = c.post("/entity/_batch", json={"requests": [
                {"request_type": "create", "entity": CE, "data": {**body, "code": body["code"] + "b"}}]})
            if b.ok:
                bid = b.json()["data"][0]["data"]["id"]
                made.add(SLUG, bid)
                bres = f"{b.status_code} {json.dumps(readback(bid, keys))}"
            else:
                bres = f"{b.status_code} {errs(b)}"
            out(f"{label:<28} {sres}\n{'':<28} batch: {bres}")
        r = c.post("/entity/_batch", json={"requests": [
            {"request_type": "create", "entity": CE, "data": {"project": P, "code": "zzprobe_137_bulk",
                                                               F: "4.5", "created_at": "2020-01-02T03:04:05Z"}}] * 3})
        if r.ok:
            for x in r.json()["data"]:
                made.add(SLUG, x["data"]["id"])
        out(f"\none _batch, three creates with float \"4.5\" and created_at -> {r.status_code}: "
            + (json.dumps([readback(x['data']['id'], [F, 'created_at']) for x in r.json()['data']]) if r.ok else errs(r)))
    finally:
        _lib.emit("137_batch_create_coercion", "\n".join(rows), env)
        if field_made:
            # inside the finally: a crash in the cases must not leave the field live
            r = c.delete(f"/schema/{CE}/fields/{F}")
            print(f"  retired /schema/<custom slot>/fields/{F} -> {r.status_code}")
