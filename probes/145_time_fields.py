"""Q: what precision does a `date_time` field keep on create, update and inside `_batch`; and what
does a `timecode` and a `duration` field created over REST take, return and declare, and how does
`01:00:00:12` at 24 and at 23.976 fps round-trip?

`field_types/date_time` measured a stock field by `PUT` (sub-second dropped, offset normalised to
UTC); `field_types/timecode` measured the one stock timecode field (integer milliseconds, a rate of
23.976 solved from `_summarize` group names); `field_types/duration` a stock duration (integer
minutes). Not yet measured, and measured here on the first enabled custom slot with three fields
created for it, `sg_zzprobe_145_dt`, `_tc` and `_dur`:

  a. date_time: milliseconds and offsets sent by single `POST`, `PUT` and `_batch` create
  b. the schema a new timecode and duration field declares, and the property names a create takes
     (a bogus property makes the 400 list them, probe 142)
  c. timecode: the integers `01:00:00:12` maps to at 24 and at 23.976 fps, written, read, and
     rendered by `_summarize` group names; whether a new field renders at the same rate as the stock one
  d. duration: the write table's edges on a new field

Writes in the sandbox, behind `--write`. Rows `zzprobe_145_*` deleted on exit; the three fields
retired.

    python probes/145_time_fields.py --write
"""
import json

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 145 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
schema = c.get("/schema").json()["data"]
CE = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[0]
SLUG = f"custom_entity{CE[12:]}s"
DT, TC, DUR = "sg_zzprobe_145_dt", "sg_zzprobe_145_tc", "sg_zzprobe_145_dur"
rows = []
made_fields = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        e = r.json()["errors"][0]
        return f"code {e.get('code')} {e.get('title')[:300]}"
    except (ValueError, KeyError, IndexError, TypeError):
        return repr(r.text[:300])


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


def ensure(name, dtype, display):
    if c.get(f"/schema/{CE}/fields/{name}").ok:
        out(f"  {name} live from an interrupted run; reused")
        made_fields.append(name)
        return
    r = c.post(f"/schema/{CE}/fields", json={"data_type": dtype, "properties": prop(name=display)})
    got = r.json()["links"]["self"].rsplit("/", 1)[-1] if r.status_code == 201 else None
    out(f"  POST {dtype} -> {r.status_code} {got or errs(r)}")
    if got:
        made_fields.append(got)


def read(rid, f):
    return c.get(f"/entity/{SLUG}/{rid}", params={"fields": f}).json()["data"]["attributes"][f]


try:
    with _lib.Created(c) as made:
        out("===== b. the fields")
        for name, dt, disp in ((DT, "date_time", "zzprobe 145 dt"), (TC, "timecode", "zzprobe 145 tc"),
                               (DUR, "duration", "zzprobe 145 dur")):
            ensure(name, dt, disp)
        for name in (TC, DUR, DT):
            d = c.get(f"/schema/{CE}/fields/{name}").json()["data"]
            out(f"  {name}: properties {json.dumps({k: v.get('value') for k, v in d['properties'].items()})}")
        for dt in ("timecode", "duration"):
            r = c.post(f"/schema/{CE}/fields", json={"data_type": dt, "properties": prop(
                name=f"zzprobe 145 {dt} fps", frame_rate=24)})
            out(f"  POST {dt} with frame_rate 24 -> {r.status_code} {errs(r) if not r.ok else 'ACCEPTED'}")
            if r.status_code == 201:
                made_fields.append(r.json()["links"]["self"].rsplit("/", 1)[-1])

        def new(code, **kw):
            r = c.post(f"/entity/{SLUG}", json={"project": P, "code": code, **kw})
            if r.status_code == 201:
                return made.add(SLUG, r.json()["data"]["id"]), r
            return None, r

        out("\n===== a. date_time precision: single POST, PUT, _batch create")
        vals = ["2026-11-11T14:22:05.999Z", "2026-11-11T14:22:05.5Z", "2026-11-11T14:22:05.123456Z",
                "2026-11-11T09:22:05.999-05:00", "2026-11-11T14:22:05,5Z", "2026-11-11T14:22:05Z"]
        out(f"  {'sent':<34} {'POST':<26} {'PUT':<26} _batch")
        for i, v in enumerate(vals):
            rid, r = new(f"zzprobe_145_dt{i}", **{DT: v})
            post = read(rid, DT) if rid else f"{r.status_code} {errs(r)[:60]}"
            if not rid:
                rid, _ = new(f"zzprobe_145_dt{i}")
            u = c.put(f"/entity/{SLUG}/{rid}", json={DT: v})
            put = read(rid, DT) if u.ok else f"{u.status_code} {errs(u)[:60]}"
            b = c.post("/entity/_batch", json={"requests": [{"request_type": "create", "entity": CE, "data": {
                "project": P, "code": f"zzprobe_145_dtb{i}", DT: v}}]})
            if b.ok:
                bid = b.json()["data"][0]["data"]["id"]
                made.add(SLUG, bid)
                bat = read(bid, DT)
            else:
                bat = f"{b.status_code} {errs(b)[:60]}"
            out(f"  {v:<34} {str(post):<26} {str(put):<26} {bat}")
        rid, _ = new("zzprobe_145_dtf", **{DT: "2026-11-11T14:22:05.999Z"})
        for op, v in (("is", "2026-11-11T14:22:05Z"), ("is", "2026-11-11T14:22:05.999Z"),
                      ("is", "2026-11-11T14:22:06Z")):
            q = c.post(f"/entity/{SLUG}/_search", headers=ARR, json={
                "filters": [["id", "is", rid], [DT, op, v]], "fields": ["id"]})
            out(f"  stored from .999Z; filter {op} {v} -> {len(q.json()['data']) if q.ok else errs(q)}")

        out("\n===== c. timecode: 01:00:00:12")
        cases = [("01:00:00:12 at 24 fps, ms = 3600000 + 12*1000/24", 3600500),
                 ("01:00:00:12 at 23.976 fps, ms = 3600000 + 12*1001/24", 3600500.5),
                 ("  the same, rounded", 3600501),
                 ("01:00:00:12 at 23.976 as a frame count, (86400+12)*1001/24 ms", 3603603.5),
                 ("  the same, rounded", 3603604),
                 ("11 frames at 24 (458.3 ms), rounded", 3600458),
                 ("13 frames at 24 (541.7 ms), rounded", 3600542),
                 ("01:00:00:12 as a string", "01:00:00:12")]
        tc_ids = []
        for label, v in cases:
            rid, r = new("zzprobe_145_tc", **{TC: v})
            out(f"  {label:<62} sent {v!r:<14} -> " + (f"201, reads {read(rid, TC)!r}" if rid else f"{r.status_code} {errs(r)[:140]}"))
            if rid:
                tc_ids.append(rid)
        sm = c.post(f"/entity/{SLUG}/_summarize", headers=ARR, json={
            "filters": [["project", "is", P], ["code", "is", "zzprobe_145_tc"]],
            "summary_fields": [{"field": "id", "type": "count"}],
            "grouping": [{"field": TC, "type": "exact", "direction": "asc"}]})
        if sm.ok:
            for g in sm.json()["data"]["groups"]:
                out(f"    _summarize group_value {g['group_value']!r:<10} group_name {g['group_name']!r}")
        else:
            out(f"    _summarize -> {sm.status_code} {errs(sm)}")

        out("\n===== d. duration on a new field")
        for v in (90, "90", 1.5, 1.9, "1.5", "01:30", -30):
            rid, r = new("zzprobe_145_dur", **{DUR: v})
            out(f"  sent {v!r:<8} -> " + (f"201, reads {read(rid, DUR)!r}" if rid else f"{r.status_code} {errs(r)[:160]}"))
        _lib.emit("145_time_fields", "\n".join(rows), env)
finally:
    for name in made_fields:
        r = c.delete(f"/schema/{CE}/fields/{name}")
        print(f"  retired /schema/<custom slot>/fields/{name} -> {r.status_code}")
