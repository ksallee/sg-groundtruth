"""Q: how does a `timecode` field read, write, clear and filter — and is its frame rate recoverable?

A media pipeline reaches for timecode first and has to know two things the type name does not settle:
what the wire value is, and what rate converts it into `HH:MM:SS:FF`. Every read path returns a bare
integer, so the rate is chased through four routes: the field schema, `GET /preferences`, the rendered
`group_name` a `_summarize` grouping returns (`field_types/calculated` found the server renders units
there), and the frame-rate fields other entity types carry.

The site is swept for `data_type: timecode` across every entity type in `/schema`, so the count is
measured rather than assumed. Nothing is created in the schema: a field name is burned permanently
(probe 019). The read-only half runs ungated; everything that mutates goes into throwaway Sequences in
the sandbox and is deleted.
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
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
JSN = {"Content-Type": "application/json"}
ENT = "Sequence"
SLUG = "sequences"
FIELD = "sg_timecode"
CODE = "zzprobe_timecode"
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


# ---------------------------------------------------------------- read-only
rows.append("=== sweep: every field on the site whose data_type is timecode")
schema = c.get("/schema").json()["data"]
tc, named, rate = [], [], []
for ent in sorted(schema):
    r = c.get(f"/schema/{ent}/fields")
    if not r.ok:
        rows.append(f"  {ent} -> {r.status_code}")
        continue
    for f, v in sorted(r.json()["data"].items()):
        dt = (v.get("data_type") or {}).get("value")
        nm = ((v.get("name") or {}).get("value") or "").lower()
        if dt == "timecode":
            tc.append((ent, f, (v.get("editable") or {}).get("value")))
        elif "timecode" in f.lower() or "_tc_" in f.lower():
            named.append((ent, f, dt, (v.get("editable") or {}).get("value")))
        if any(k in f.lower() or k in nm for k in ("frame_rate", "framerate", "fps", "frame rate")):
            rate.append((ent, f, dt))
rows.append(f"  {len(schema)} entity types, {len(tc)} field(s) of data_type timecode")
for ent, f, ed in tc:
    rows.append(f"    {ent}.{f:<24} editable={ed}")
rows.append("  fields named for timecode that are NOT data_type timecode:")
for ent, f, dt, ed in named:
    rows.append(f"    {ent}.{f:<30} data_type={dt:<10} editable={ed}")

rows.append(f"\n=== rate, route 1: the field schema.  GET /schema/{ENT}/fields/{FIELD}")
d = c.get(f"/schema/{ENT}/fields/{FIELD}").json()["data"]
rows.append(f"  top-level keys: {sorted(d)}")
rows.append(f"  properties keys: {sorted(d['properties'])}")
rows.append(json.dumps(d["properties"], indent=1))

rows.append("\n=== rate, route 2: a site preference")
for path in ("/preferences", "/entity/preferences", "/settings", "/entity/settings",
             "/schema/Preference/fields"):
    r = c.get(path)
    rows.append(f"  GET {path:<26} -> {r.status_code} {r.text[:90]}")
pref = c.get("/preferences")
if pref.ok:
    keys = sorted(pref.json()["data"])
    rows.append(f"  /preferences keys ({len(keys)}): {keys}")
    rows.append(f"  of those, rate- or timecode-shaped: "
                f"{[k for k in keys if any(x in k for x in ('frame', 'fps', 'rate', 'timecode'))]}")
rows.append("  preference-shaped entity types in /schema: "
            + str([e for e in sorted(schema)
                   if any(k in e.lower() for k in ("pref", "setting", "config", "site", "global"))]))

rows.append("\n=== rate, route 3: frame-rate fields on other entity types, and whether they hold data")
for ent, f, dt in rate:
    slug = {"Cut": "cuts", "Version": "versions", "Slate": "slates",
            "SourceClip": "source_clips"}.get(ent)
    data, _ = search(slug, [[f, "is_not", None]], (f,), size=5) if slug else (None, None)
    rows.append(f"  {ent}.{f:<26} data_type={dt:<7} populated={[x['attributes'][f] for x in data or []]}")

rows.append("\n=== the API enumerates its own operators (probe 017)")
r = c.post(f"/entity/{SLUG}/_search", headers=ARR,
           json={"filters": [[FIELD, "definitely_not_an_operator", 1]],
                 "fields": ["code"], "page": {"size": 1}})
rows.append(f"  bogus relation -> {r.status_code}")
rows.append(errs(r))
m = re.search(r"Valid relations: (\[[^\]]*\])", errs(r))
VALID = json.loads(m.group(1).replace('\\"', '"')) if m else []

rows.append("\n=== read: stored values on a read-only project")
P = _lib.sample_projects(c, env)[0]
data, bad = search(SLUG, [["project", "is", {"type": "Project", "id": P}]], ("code", FIELD), size=200)
if data:
    _lib.note_from(data)
    set_ = [x for x in data if x["attributes"].get(FIELD) is not None]
    rows.append(f"  {len(data)} {ENT} rows, {len(set_)} with {FIELD} set")
    rows.append(f"  raw attributes JSON of the first row: {json.dumps(data[0]['attributes'])}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; re-run with --write for write / clear / filter / rate route 4)")
    _lib.emit("field_types/timecode", "\n".join(rows), env)
    raise SystemExit

# ---------------------------------------------------------------- writes
SANDBOX = _lib.sandbox_id(c, env)
MINE = [["project", "is", {"type": "Project", "id": SANDBOX}], ["code", "starts_with", CODE]]


def put(sid, value):
    return c.request("PUT", f"/entity/{SLUG}/{sid}", headers=JSN, json={FIELD: value})


def raw(sid):
    """The value exactly as it came over the wire — json.loads would erase an integer/string split."""
    t = c.get(f"/entity/{SLUG}/{sid}", params={"fields": FIELD}).text
    m = re.search(rf'"{FIELD}":\s*("(?:[^"\\]|\\.)*"|[^,}}]+)', t)
    return m.group(1) if m else "<absent>"


def drop(made):
    """Delete the rows made so far, so a later baseline count is not measuring them."""
    for slug, i in reversed(made.rows):
        c.request("DELETE", f"/entity/{slug}/{i}")
    made.rows.clear()


def count(label, filters, expect=None):
    data, bad = search(SLUG, filters, ("code", FIELD))
    if bad is not None:
        rows.append(f"  {label:<44} -> ERR {bad.status_code} "
                    f"{json.loads(errs(bad))[0].get('title')}")
        return
    n = len(data)
    rows.append(f"  {label:<44} -> {n}" + ("" if expect is None or n == expect else f"  <- expected {expect}"))


def group_names(made, values):
    """Write one Sequence per value, then read what the server renders as each group_name."""
    for i, v in enumerate(values):
        r = c.post(f"/entity/{SLUG}", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX},
                         "code": f"{CODE}_cal{i:02d}", FIELD: v})
        if r.ok:
            made.add(SLUG, r.json()["data"]["id"])
        else:
            rows.append(f"  create {v} -> {r.status_code} {errs(r)}")
    r = c.post(f"/entity/{SLUG}/_summarize", headers=ARR,
               json={"filters": MINE, "summary_fields": [{"field": "id", "type": "count"}],
                     "grouping": [{"field": FIELD, "type": "exact", "direction": "asc"}]})
    if not r.ok:
        rows.append(f"  _summarize -> {r.status_code} {errs(r)}")
        return {}
    return {int(g["group_value"]): g["group_name"] for g in r.json()["data"]["groups"]}


with _lib.Created(c) as made:
    rows.append("\n=== rate, route 4: _summarize renders the value in group_name")
    rows.append("  (field_types/calculated found the server states units there and nowhere else)")
    CAL = [1, 20, 21, 24, 25, 30, 48, 62, 63, 500, 812, 813, 814, 815, 979, 980, 981, 999, 1000,
           3600, 3600000, 86400000, 86400001, 2147483647, -1, -1000]
    got = group_names(made, CAL)
    for v in sorted(got):
        rows.append(f"  {v:>12} -> group_name {got[v]!r}")
    rows.append("  1000 -> one whole second, so the stored integer is milliseconds.")
    for lo, hi, fr in ((813, 814, 19.5), (980, 981, 23.5)):
        if lo in got and hi in got:
            rows.append(f"  the {fr}-frame boundary lies in ({lo}, {hi}]  ->  "
                        f"fps in [{fr * 1000 / hi:.4f}, {fr * 1000 / lo:.4f})")
    rows.append("  intersect the two bands; 24000/1001 = 23.976 sits inside, 24 / 25 / 30 do not.")
    rows.append(f"  separator is ':' in every render, so no drop frame: "
                f"{sorted({n[-3] for n in got.values()})}")
    drop(made)

    rows.append("\n=== does any read path render it, or is group_name the only one?")
    r = c.post(f"/entity/{SLUG}", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_r", FIELD: 813})
    R = made.add(SLUG, r.json()["data"]["id"])
    rows.append(f"  GET /entity/{SLUG}/<id>?fields={FIELD}   {c.get(f'/entity/{SLUG}/{R}', params={'fields': FIELD}).text[:110]}")
    for label, h in (("api3_array", ARR), ("api3_hash", HSH)):
        rr = c.post(f"/entity/{SLUG}/_search", headers=h,
                    json={"filters": [["id", "is", R]], "fields": [FIELD]})
        rows.append(f"  _search {label:<11} -> {rr.status_code} {rr.text[:110]}")
    sh = c.post("/entity/shots", headers=JSN,
                json={"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_shot",
                      "sg_sequence": {"type": "Sequence", "id": R}})
    if sh.ok:
        made.add("shots", sh.json()["data"]["id"])
        dot = f"sg_sequence.{ENT}.{FIELD}"
        rr = c.post("/entity/shots/_search", headers=ARR,
                    json={"filters": [["id", "is", sh.json()["data"]["id"]]], "fields": [dot]})
        rows.append(f"  dotted {dot} -> {rr.status_code} {rr.text[:150]}")
    rr = c.post(f"/entity/{SLUG}/_summarize", headers=ARR,
                json={"filters": MINE, "summary_fields": [{"field": FIELD, "type": "sum"},
                                                          {"field": FIELD, "type": "maximum"}]})
    rows.append(f"  _summarize sum/maximum -> {rr.status_code} {rr.text[:120]}")
    drop(made)

    rows.append("\n=== create: the accepted set, stated in the rejection")
    for label, value in [("string '01:00:00:00'", "01:00:00:00"), ("integer 3600000", 3600000)]:
        r = c.post(f"/entity/{SLUG}", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX},
                         "code": f"{CODE}_probe", FIELD: value})
        rows.append(f"  POST {label:<22} -> {r.status_code}")
        rows.append(errs(r) if not r.ok else f"  reads back {json.dumps(r.json()['data']['attributes'][FIELD])}")
        if r.ok:
            # Deleted now rather than at exit, so it cannot join the filter baseline below.
            i = made.add(SLUG, r.json()["data"]["id"])
            c.request("DELETE", f"/entity/{SLUG}/{i}")
            made.rows.pop()

    def mk(suffix, value=...):
        body = {"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_{suffix}"}
        if value is not ...:
            body[FIELD] = value
        r = c.post(f"/entity/{SLUG}", headers=JSN, json=body)
        if not r.ok:
            rows.append(f"  create {suffix} -> {r.status_code} {errs(r)}")
            return None
        return made.add(SLUG, r.json()["data"]["id"])

    A = mk("a", 3600000)
    B = mk("b", 0)
    C = mk("c")
    D = mk("d")
    rows.append(f"\n=== throwaway {ENT} rows: a(3600000) b(0) c(field omitted) d(scratch)")
    rows.append(f"  a reads back raw {raw(A)}; c, created without the field, reads raw {raw(C)}")

    rows.append(f"\n=== write: what an update accepts   (PUT /entity/{SLUG}/<id> {FIELD})")
    for label, value in [
            ("timecode '01:00:00:00'", "01:00:00:00"),
            ("drop frame '01:00:00;00'", "01:00:00;00"),
            ("short '01:00:00'", "01:00:00"),
            ("malformed 'banana'", "banana"),
            ("numeric string '3600000'", "3600000"),
            ("integer 3600000", 3600000),
            ("integer 1", 1),
            ("negative -1", -1),
            ("negative -3600000", -3600000),
            ("past 24h 86400000", 86400000),
            ("past 24h + 1ms 86400001", 86400001),
            ("float 1.5", 1.5),
            ("bool True", True),
            ("2**31-1", 2**31 - 1),
            ("2**31", 2**31),
            ("-(2**31)", -(2**31)),
            ("-(2**31)-1", -(2**31) - 1)]:
        r = put(D, value)
        detail = "" if r.ok else " " + errs(r).replace("\n", " ")
        rows.append(f"  {label:<26} -> {r.status_code} reads back {raw(D)}{detail}")

    rows.append("\n=== the ceiling fails differently on the two verbs")
    r = c.post(f"/entity/{SLUG}", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_hi", FIELD: 2**31})
    rows.append(f"  POST 2**31 -> {r.status_code}")
    rows.append(errs(r))
    if r.ok:
        made.add(SLUG, r.json()["data"]["id"])

    rows.append("\n=== clear: null, empty string, zero")
    for label, value in [("set null", None), ("set 0", 0), ("set null again", None),
                         ("set 3600000", 3600000), ("set ''", "")]:
        r = put(B, value)
        detail = "" if r.ok else " " + errs(r).replace("\n", " ")
        rows.append(f"  {label:<16} -> {r.status_code} reads back {raw(B)}{detail}")
    put(B, 0)
    rows.append(f"  the row created without the field reads {raw(C)}")

    rows.append("\n=== filter: 4 rows in scope — a=3600000 b=0 c=null d=null")
    put(D, None)
    count("baseline", MINE, expect=4)
    TESTS = [
        ("is", 3600000, 1), ("is", 0, 1), ("is", None, 2),
        ("is", "01:00:00:00", None), ("is", "3600000", None), ("is", 3600000.0, None),
        ("is_not", 3600000, 3), ("is_not", None, 2),
        ("greater_than", 0, 1), ("greater_than", -1, 2), ("greater_than", 3600000, 0),
        ("less_than", 3600000, 1), ("less_than", 1, 1),
        ("between", [0, 7200000], 2), ("between", [7200000, 9000000], 0),
        ("between", 3600000, None),
        ("in", [3600000, 0], 2), ("in", [999999999], 0), ("in", ["3600000"], None),
        ("not_in", [3600000], 3), ("not_in", [999999999], 4),
        ("contains", "3600", None), ("starts_with", "01", None), ("not_between", [0, 10], None),
    ]
    for op, val, expect in TESTS:
        tag = "" if op in VALID else "  (not in Valid relations)"
        count(f"{op} {val!r}{tag}", MINE + [[FIELD, op, val]], expect=expect)

    rows.append("\n  negative controls above that must be 0: in [999999999],"
                " between [7200000,9000000], greater_than 3600000")

    rows.append("\n=== the filter 400s, in full")
    for filt in ([FIELD, "is", "01:00:00:00"], [FIELD, "contains", "3600"],
                 [FIELD, "between", 3600000]):
        _, bad = search(SLUG, MINE + [filt], ("code", FIELD))
        rows.append(f"  {filt!r} ->")
        rows.append(errs(bad) if bad is not None else "  200 (accepted)")

_lib.emit("field_types/timecode", "\n".join(rows), env)
