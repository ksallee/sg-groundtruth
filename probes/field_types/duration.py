"""Q: how does a `duration` field read, write, clear and filter — and what unit is the stored number?

`duration` exists as a separate data_type from `number` only because it has a unit, so the unit is the
question. `docs/quirks.md` claims minutes stored, hours or days displayed, with hours-per-day a site
setting. This settles the API half: what a write stores, and whether the schema names a unit at all.

Stock editable duration fields, nothing created here — a field name is burned permanently (probe 019).
The read-only half (schema, the operator list the API enumerates, the unit evidence already on the site)
runs ungated; everything that mutates goes into a throwaway Shot in the sandbox and is deleted.
"""
import functools
import json
import math
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
FIELD = "sg_bid___total"
SECOND = "sg_bid___ani"
NUM = "sg_cut_duration"  # a stock `number` field on Shot, for the operator side-by-side
CODE = "zzprobe_duration"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"), indent=1)
    except ValueError:
        return r.text


def search(entity, filters, fields, size=200):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": list(filters), "fields": list(fields), "page": {"size": size}})
    return (r.json()["data"], None) if r.ok else (None, r)


def count(label, filters, expect=None):
    data, bad = search("shots", filters, ("code", FIELD))
    if bad is not None:
        rows.append(f"  {label:<46} -> ERR {bad.status_code} {json.loads(errs(bad))[0].get('title')}")
        return None
    n = len(data)
    rows.append(f"  {label:<46} -> {n}" + ("" if expect is None or n == expect else f"   <- expected {expect}"))
    return n


# ---------------------------------------------------------------- read-only
rows.append("=== schema: every duration field on the entities that carry one")
for ent in ("Shot", "Task", "TimeLog"):
    sch = c.get(f"/schema/{ent}/fields").json()["data"]
    d = {f: v for f, v in sch.items() if (v.get("data_type") or {}).get("value") == "duration"}
    for f, v in sorted(d.items()):
        rows.append(f"  {ent}.{f:<20} editable={str((v.get('editable') or {}).get('value')):<5} "
                    f"name={(v.get('name') or {}).get('value')!r}")

rows.append(f"\n=== does the schema name a unit?  GET /schema/Shot/fields/{FIELD} — every key in properties")
d = c.get(f"/schema/Shot/fields/{FIELD}").json()["data"]
rows.append(f"  properties keys: {sorted(d['properties'])}")
rows.append(json.dumps(d["properties"], indent=1))
for path in ("Task/fields/duration", "Task/fields/est_in_mins", "TimeLog/fields/duration"):
    p = c.get(f"/schema/{path}").json()["data"]["properties"]
    rows.append(f"  {path:<28} properties={json.dumps({k: v['value'] for k, v in p.items()})}")

rows.append("\n=== the API enumerates its own operators (probe 017), duration next to number")
VALID = []
for label, ent, field in [("duration", "shots", FIELD), ("number  ", "shots", NUM)]:
    r = c.post(f"/entity/{ent}/_search", headers=ARR,
               json={"filters": [[field, "definitely_not_an_operator", 1]],
                     "fields": ["code"], "page": {"size": 1}})
    rows.append(f"  {label} {field} -> {r.status_code}")
    rows.append(errs(r))
    m = re.search(r"Valid relations: (\[[^\]]*\])", errs(r))
    got = json.loads(m.group(1).replace('\\"', '"')) if m else []
    if not VALID:
        VALID = got
    else:
        rows.append(f"  identical to the duration list: {got == VALID}")

rows.append("\n=== read: the shape of a stored duration, on a read-only project")
P = _lib.sample_projects(c, env)[0]
PROJ = ["project", "is", {"type": "Project", "id": P}]
data, bad = search("tasks", [PROJ, ["duration", "is_not", None]],
                   ("content", "duration", "est_in_mins", "start_date", "due_date", "time_logs_sum"), size=3)
if data:
    _lib.note_from(data)
    for row in data:
        a = row["attributes"]
        rows.append("  " + " ".join(f"{k}={a.get(k)!r}({type(a.get(k)).__name__})"
                                    for k in ("duration", "est_in_mins", "time_logs_sum")))
    rows.append(f"  raw attributes JSON: {json.dumps(data[0]['attributes'])}")

rows.append("\n=== unit evidence the site already holds (no write needed)")
data, _ = search("tasks", [PROJ, ["duration", "is_not", None]], ("duration", "est_in_mins"), size=500)
if data:
    dur = [x["attributes"]["duration"] for x in data]
    est = [x["attributes"]["est_in_mins"] for x in data if x["attributes"]["est_in_mins"]]
    rows.append(f"  {len(dur)} Task.duration values, gcd {functools.reduce(math.gcd, dur)}, "
                f"distinct {sorted(set(dur))[:11]}")
    rows.append(f"  {len(est)} Task.est_in_mins values, gcd {functools.reduce(math.gcd, est)}"
                "   <- the stock field names its own unit: est_in_mins")

data, _ = search("tasks", [PROJ, ["time_logs_sum", "greater_than", 0]], ("time_logs_sum",), size=3)
for t in data or []:
    logs, _ = search("time_logs", [["entity", "is", {"type": "Task", "id": t["id"]}]], ("duration",), size=200)
    ds = [x["attributes"]["duration"] for x in logs or []]
    rows.append(f"  Task.time_logs_sum={t['attributes']['time_logs_sum']} vs sum(TimeLog.duration)"
                f"={sum(ds)} from {ds}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; re-run with --write for write / clear / filter formats)")
    _lib.emit("field_types/duration", "\n".join(rows), env)
    raise SystemExit

# ---------------------------------------------------------------- writes
SANDBOX = _lib.sandbox_id(c, env)
SPROJ = ["project", "is", {"type": "Project", "id": SANDBOX}]
MINE = [SPROJ, ["code", "starts_with", CODE]]
made = []


def make(suffix, attrs=None):
    body = {"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_{suffix}"}
    body.update(attrs or {})
    r = c.post("/entity/shots", headers=JSN, json=body)
    if not r.ok:
        rows.append(f"  create {suffix} -> {r.status_code} {errs(r)}")
        return None
    made.append(r.json()["data"]["id"])
    return made[-1]


def put(sid, field, value):
    return c.request("PUT", f"/entity/shots/{sid}", headers=JSN, json={field: value})


def readback(sid, field):
    return c.get(f"/entity/shots/{sid}", params={"fields": field}).json()["data"]["attributes"].get(field)


def raw(sid, field):
    """The value exactly as it came over the wire — json.loads would erase an integer/string split."""
    t = c.get(f"/entity/shots/{sid}", params={"fields": field}).text
    m = re.search(rf'"{field}":\s*("(?:[^"\\]|\\.)*"|[^,}}]+)', t)
    return m.group(1) if m else "<absent>"


try:
    A = make("a", {FIELD: 480, SECOND: 90})
    B = make("b", {FIELD: 0})
    C = make("c")
    D = make("d")
    rows.append(f"\n=== throwaway Shots in the sandbox: a(480) b(0) c(untouched) d(scratch) -> {made}")
    rows.append(f"  on create, {FIELD}=480 reads back raw {raw(A, FIELD)}   {SECOND}={raw(A, SECOND)}")

    rows.append(f"\n=== write: what an update accepts   (PUT /entity/shots/<id> {FIELD})")
    for label, value in [("int 90", 90), ("int 1440 (24h)", 1440), ("numeric string '90'", "90"),
                         ("padded string ' 90 '", " 90 "), ("negative int -30", -30),
                         ("float 1.5", 1.5), ("float 90.0", 90.0),
                         ("clock string '2:30'", "2:30"), ("unit string '90m'", "90m"),
                         ("unit string '1h'", "1h"), ("day string '1d'", "1d"),
                         ("bool True", True), ("empty string ''", ""), ("null", None),
                         ("2**31-1", 2**31 - 1), ("2**31", 2**31)]:
        r = put(D, FIELD, value)
        back = raw(D, FIELD) if r.ok else "-"
        detail = "" if r.ok else " " + errs(r).replace("\n", " ")
        rows.append(f"  {label:<24} -> {r.status_code} reads back {back}{detail}")

    rows.append("\n=== a Float is accepted where `number` 400s — rounded, truncated, or floored?")
    for value in (1.5, 90.4, 90.5, 90.6, 90.9, -1.5, -90.6, 0.4):
        r = put(D, FIELD, value)
        rows.append(f"  {value!r:<8} -> {r.status_code} reads back {raw(D, FIELD)}")

    rows.append("\n=== clear: 0 and null")
    put(D, FIELD, None)
    for label, value in [("set 0", 0), ("set null", None), ("set 0 again", 0), ("set ''", "")]:
        r = put(B, FIELD, value)
        rows.append(f"  {label:<14} -> {r.status_code} reads back {readback(B, FIELD)!r}"
                    f"{'' if r.ok else ' ' + errs(r).replace(chr(10), ' ')}")
    put(B, FIELD, 0)
    rows.append(f"  a Shot created without the field at all reads {readback(C, FIELD)!r}")
    rows.append(f"  the row holding 0 reads {readback(B, FIELD)!r}")

    rows.append(f"\n=== filter: 4 rows in scope — _a={480} _b=0 _c=null _d=null")
    count("baseline", MINE, expect=4)
    TESTS = [
        ("is", 480, 1), ("is", 0, 1), ("is", "480", None), ("is", None, 2),
        ("is", 480.0, None), ("is", 480.6, None), ("is", 8.0, None), ("is", "8:00", None),
        ("is_not", 480, 3), ("is_not", None, 2),
        ("greater_than", 0, 1), ("greater_than", -1, None), ("greater_than", 480, 0),
        ("less_than", 480, 1), ("less_than", 1, None),
        ("between", [0, 600], 2), ("between", [600, 900], 0), ("between", 480, None),
        ("in", [480, 0], 2), ("in", ["480"], None), ("in", [999999], 0),
        ("not_in", [480], None), ("not_in", [999999], None),
        ("contains", "48", None), ("not_between", [0, 600], None),
    ]
    for op, val, expect in TESTS:
        tag = "" if op in VALID else "  (NOT in Valid relations)"
        count(f"{op} {val!r}{tag}", MINE + [[FIELD, op, val]], expect=expect)

    rows.append("\n  negative controls above that must be 0: in [999999], between [600,900],"
                " greater_than 480")

    rows.append("\n=== the filter 400s, in full")
    for filt in ([FIELD, "between", 480], [FIELD, "contains", "48"], [FIELD, "is", "8:00"]):
        _, bad = search("shots", MINE + [filt], ("code", FIELD))
        rows.append(f"  {filt!r} ->")
        rows.append(errs(bad) if bad is not None else "  200 (accepted)")
finally:
    for sid in made:
        r = c.request("DELETE", f"/entity/shots/{sid}")
        rows.append(f"  DELETE /entity/shots/<id> -> {r.status_code}")

_lib.emit("field_types/duration", "\n".join(rows), env)
