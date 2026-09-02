"""Q: how does a `number` field read, write, clear and filter?

Field-type matrix entry. Stock editable number fields on Version: sg_first_frame, sg_last_frame,
frame_count — nothing here creates a schema field, because a name is burned permanently (probe 019).

The read-only half (schema, the operator list the API enumerates, the fill-rate reading of 0) runs
ungated. Everything that mutates is behind --write and goes only into the sandbox project.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
FIELD = "sg_first_frame"
RANGE_FIELD = "frame_count"
CODE = "zzprobe_number"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"), indent=1)
    except ValueError:
        return r.text


def search(filters, fields=("code", FIELD), size=200):
    r = c.post("/entity/versions/_search", headers=ARR,
               json={"filters": list(filters), "fields": list(fields), "page": {"size": size}})
    if not r.ok:
        return None, r
    return r.json()["data"], None


def count(label, filters, expect=None):
    data, bad = search(filters)
    if bad is not None:
        first = json.loads(errs(bad))[0]
        rows.append(f"  {label:<44} -> ERR {bad.status_code} {first.get('title')}")
        return None
    n = len(data)
    flag = "" if expect is None or n == expect else f"   <- expected {expect}"
    rows.append(f"  {label:<44} -> {n}{flag}")
    return n


# ---------------------------------------------------------------- read-only
SAMPLE = _lib.sample_projects(c, env)[0]
PROJ = ["project", "is", {"type": "Project", "id": SAMPLE}]

rows.append("=== schema: every number field on Version")
sch = c.get("/schema/Version/fields").json()["data"]
nums = {f: d for f, d in sch.items() if (d.get("data_type") or {}).get("value") == "number"}
for f, d in sorted(nums.items()):
    rows.append(f"  {f:<28} editable={str((d.get('editable') or {}).get('value')):<5} "
                f"name={(d.get('name') or {}).get('value')!r}")
rows.append(f"\nfull schema entry for {FIELD} (does it declare a range?):")
rows.append(json.dumps(nums.get(FIELD), indent=1))

rows.append("\n=== the API enumerates its own operators (probe 017)")
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [[FIELD, "definitely_not_an_operator", 1]],
                 "fields": ["code"], "page": {"size": 1}})
rows.append(f"  [[{FIELD!r}, 'definitely_not_an_operator', 1]] -> {r.status_code}")
rows.append(errs(r))
m = re.search(r"Valid relations: (\[[^\]]*\])", errs(r))
VALID = json.loads(m.group(1).replace('\\"', '"')) if m else []
rows.append(f"  parsed: {VALID}")

rows.append("\n=== read: shape of the value on a real project")
base = count("baseline versions on the sample project", [PROJ])
STOCK = [FIELD, "sg_last_frame", RANGE_FIELD]
for f in STOCK:
    count(f"{f} is_not None", [PROJ, [f, "is_not", None]])
    count(f"{f} is 0", [PROJ, [f, "is", 0]])
for f in STOCK:
    data, bad = search([PROJ, [f, "is_not", None]], fields=("code", *STOCK), size=2)
    if bad is None and data:
        _lib.note_from(data)
        for row in data:
            a = row["attributes"]
            rows.append(f"  id={row['id']} " + " ".join(
                f"{k}={a.get(k)!r}({type(a.get(k)).__name__})" for k in STOCK))
        rows.append(f"  raw attributes JSON: {json.dumps(data[0]['attributes'])}")
        break
else:
    rows.append("  no Version on the sample project carries any number value — the shape comes"
                " from the sandbox writes below")

# ---------------------------------------------------------------- writes
if not _lib.writes_allowed():
    rows.append("\n(read-only run; re-run with --write for write / clear / range / filter formats)")
    _lib.emit("field_types/number", "\n".join(rows), env)
    raise SystemExit

SANDBOX = _lib.sandbox_id(c, env)
SPROJ = ["project", "is", {"type": "Project", "id": SANDBOX}]
MINE = [SPROJ, ["code", "starts_with", CODE]]


def put(vid, field, value):
    return c.request("PUT", f"/entity/versions/{vid}", headers=JSN, json={field: value})


def readback(vid, field):
    return c.get(f"/entity/versions/{vid}", params={"fields": field}).json()["data"]["attributes"].get(field)


def make(suffix, attrs=None):
    body = {"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_{suffix}"}
    body.update(attrs or {})
    r = c.post("/entity/versions", headers=JSN, json=body)
    if not r.ok:
        rows.append(f"  create {suffix} -> {r.status_code} {errs(r)}")
        return None
    return made.add("versions", r.json()["data"]["id"])


with _lib.Created(c) as made:
    rows.append("\n=== throwaway Versions in the sandbox")
    A = make("a", {FIELD: 1001, "sg_last_frame": 1100, RANGE_FIELD: 100})
    B = make("b", {FIELD: 0})
    C = make("c")
    D = make("d")
    rows.append(f"  a(first=1001) b(first=0) c(untouched) d(scratch) -> {[A, B, C, D]}")

    rows.append("\n=== write: what an update accepts   (PUT /entity/versions/<id>)")
    for label, value in [("int 42", 42), ("numeric string '42'", "42"), ("string '42abc'", "42abc"),
                         ("float 3.7", 3.7), ("float 3.2", 3.2), ("float -3.7", -3.7),
                         ("negative int -7", -7), ("bool True", True), ("empty string ''", ""),
                         ("null", None)]:
        r = put(D, RANGE_FIELD, value)
        back = readback(D, RANGE_FIELD) if r.ok else "-"
        detail = "" if r.ok else " " + errs(r).replace("\n", " ")
        rows.append(f"  {label:<22} -> {r.status_code} reads back {back!r}"
                    f"({type(back).__name__}){detail}")

    rows.append("\n=== range: where does a number stop being a number?")
    LAND = {}
    for label, value in [("2**31-1", 2**31 - 1), ("2**31", 2**31), ("2**32-1", 2**32 - 1),
                         ("2**63-1", 2**63 - 1), ("2**63", 2**63),
                         ("-(2**31)", -(2**31)), ("-(2**31)-1", -(2**31) - 1), ("-(2**63)", -(2**63))]:
        r = put(D, RANGE_FIELD, value)
        back = readback(D, RANGE_FIELD) if r.ok else None
        LAND[value] = r.ok and back == value
        rows.append(f"  {label:<12} {value:<21} -> {r.status_code} reads back {back!r}"
                    f"{'' if LAND[value] else '   <- NOT round-tripped'}")

    def boundary(lo, hi):
        """lo round-trips, hi does not. Narrow to the exact edge."""
        while abs(hi - lo) > 1:
            mid = (lo + hi) // 2
            r = put(D, RANGE_FIELD, mid)
            if r.ok and readback(D, RANGE_FIELD) == mid:
                lo = mid
            else:
                hi = mid
        return lo, hi

    good = max((v for v, ok in LAND.items() if ok and v > 0), default=0)
    bad = min((v for v, ok in LAND.items() if not ok and v > 0), default=2**63)
    hi_lo, hi_hi = boundary(good, bad)
    rows.append(f"  positive edge: {hi_lo} accepted, {hi_hi} rejected  ({hi_lo} == 2**31-1: {hi_lo == 2**31 - 1})")
    r = put(D, RANGE_FIELD, hi_hi)
    rows.append(f"  the error at the edge, PUT {RANGE_FIELD}={hi_hi} -> {r.status_code}")
    rows.append(errs(r))

    r = c.post("/entity/versions", headers=JSN, json={"project": {"type": "Project", "id": SANDBOX},
                                                     "code": "zzprobe_num_over", RANGE_FIELD: hi_hi})
    if r.ok:
        made.add("versions", r.json()["data"]["id"])
    rows.append(f"  the same value on CREATE, POST /entity/versions -> {r.status_code}")
    rows.append(errs(r))
    r = put(D, RANGE_FIELD, str(hi_hi))
    rows.append(f"  the same value as a numeric STRING {str(hi_hi)!r} -> {r.status_code}"
                f" — a string does not route around the ceiling")

    ngood = min((v for v, ok in LAND.items() if ok and v < 0), default=0)
    nbad = max((v for v, ok in LAND.items() if not ok and v < 0), default=-(2**63))
    lo_hi, lo_lo = boundary(ngood, nbad)
    rows.append(f"  negative edge: {lo_hi} accepted, {lo_lo} rejected  ({lo_hi} == -(2**31): {lo_hi == -(2**31)})")

    rows.append("\n=== clear: 0 and null are different values")
    put(D, RANGE_FIELD, None)
    for label, value in [("set 0", 0), ("set null", None), ("set 0 again", 0),
                         ("set empty string", "")]:
        r = put(B, RANGE_FIELD, value)
        rows.append(f"  {label:<18} -> {r.status_code} reads back {readback(B, RANGE_FIELD)!r}"
                    f"{'' if r.ok else ' ' + errs(r).replace(chr(10), ' ')}")
    put(B, RANGE_FIELD, None)
    rows.append(f"  a Version created without the field at all reads {readback(C, FIELD)!r}")
    rows.append(f"  the row holding 0 reads {readback(B, FIELD)!r}")

    rows.append("\n=== does `is None` match a row holding 0?   (4 rows: 1001, 0, null, null)")
    count(f"{FIELD} is None", MINE + [[FIELD, "is", None]], expect=2)
    count(f"{FIELD} is_not None", MINE + [[FIELD, "is_not", None]], expect=2)
    count(f"{FIELD} is 0", MINE + [[FIELD, "is", 0]], expect=1)

    rows.append("\n=== filter value formats, per operator the API listed")
    TESTS = [
        ("is", 1001, 1), ("is", 0, 1), ("is", "1001", None), ("is", None, 2),
        ("is_not", 1001, 3), ("is_not", None, 2),
        ("less_than", 1, None), ("less_than", 1001, None),
        ("greater_than", 0, 1), ("greater_than", -1, None),
        ("in", [1001, 0], 2), ("in", ["1001"], None), ("in", [999999], 0),
        ("not_in", [1001], None), ("not_in", [999999], None),
        ("between", [0, 2000], 2), ("between", [2000, 3000], 0), ("between", 1001, None),
        ("not_between", [0, 2000], None),
        ("contains", "100", None), ("starts_with", "10", None),
    ]
    for op, val, expect in TESTS:
        tag = "" if op in VALID else "  (NOT in Valid relations)"
        count(f"{FIELD} {op} {val!r}{tag}", MINE + [[FIELD, op, val]], expect=expect)

    rows.append("\n  negative controls above that must be 0: in [999999], between [2000,3000]")

    rows.append("\n=== the two filter 400s, in full")
    for filt in ([FIELD, "between", 1001], [FIELD, "contains", "100"]):
        _, bad = search(MINE + [filt])
        rows.append(f"  {filt!r} ->")
        rows.append(errs(bad))

_lib.emit("field_types/number", "\n".join(rows), env)
