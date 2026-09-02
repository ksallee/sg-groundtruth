"""Q: how does a `float` field read, write, clear and filter — and where does it differ from `number`?

The trap this exists to find: a float does not arrive as a JSON number, so a client that round-trips a
value through json.loads/json.dumps can quietly change its type or lose digits. Everything before
`--write` is read-only; the mutations happen on throwaway Versions in the sandbox project only.
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
FLOATS = ["sg_movie_aspect_ratio", "sg_frames_aspect_ratio", "uploaded_movie_duration"]
F = FLOATS[0]
NUM = "frame_count"  # a stock `number` field, for the side-by-side only
CODE = "zzprobe_float"
rows = []


def raw(text, key):
    """The value exactly as it came over the wire — json.loads would erase the string/number split."""
    m = re.search(rf'"{key}":\s*("(?:[^"\\]|\\.)*"|[^,}}]+)', text)
    return m.group(1) if m else "<absent>"


def search(filters, fields, size=20, entity="versions"):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": filters, "fields": fields, "page": {"size": size}})
    return r


def relations(field):
    r = search([[field, "definitely_not_an_operator", None]], [field])
    return r


# ---------------------------------------------------------------- read-only
rows.append("=== schema  (GET /schema/Version/fields/<field>)")
for f in FLOATS:
    d = c.get(f"/schema/Version/fields/{f}").json()["data"]
    rows.append(f"  {f:<26} data_type={d['data_type']['value']:<8} editable={d['editable']['value']} "
                f"properties={json.dumps({k: v['value'] for k, v in d['properties'].items()})}")

rows.append("\n=== the API enumerates its own operators (bogus relation -> 400, whole errors[])")
for label, field in [("float ", F), ("number", NUM)]:
    r = relations(field)
    err = r.json()["errors"][0]
    rows.append(f"  {label} {field} -> {r.status_code}")
    rows.append(f"    {json.dumps(err, indent=2)}")

rows.append("\n=== read: how a stored float is serialised, next to a number, in a read-only project")
P = _lib.sample_projects(c, env)[0]
r = search([["project", "is", {"type": "Project", "id": P}], ["uploaded_movie_duration", "is_not", None]],
           FLOATS + ["sg_uploaded_movie_frame_rate", NUM], size=2)
rows.append("  " + r.text[:260])  # the `number` side-by-side is in the --write control below

if not _lib.writes_allowed():
    rows.append("\n(read-only; re-run with --write for the write / clear / filter half)")
    _lib.emit("field_types/float", "\n".join(rows), env)
    sys.exit(0)

# ---------------------------------------------------------------- write half
SANDBOX = _lib.sandbox_id(c, env)
SB = ["project", "is", {"type": "Project", "id": SANDBOX}]
MINE = [SB, ["code", "starts_with", CODE]]


def ensure(suffix):
    r = c.post("/entity/versions",
               json={"project": {"type": "Project", "id": SANDBOX}, "code": f"{CODE}_{suffix}"})
    return made.add("versions", r.json()["data"]["id"])


with _lib.Created(c) as made:
    A, B, C = (ensure(s) for s in "abc")
    rows.append(f"\n=== sandbox Versions {CODE}_a/_b/_c created")

    def put(vid, value, field=F):
        r = c.request("PUT", f"/entity/versions/{vid}", json={field: value})
        if not r.ok:
            return r.status_code, json.dumps(r.json()["errors"][0])
        back = c.get(f"/entity/versions/{vid}", params={"fields": field})
        return r.status_code, raw(back.text, field)


    rows.append(f"\n=== write: input -> status, then the value re-read raw  ({F})")
    rows.append(f"  {'input (python repr)':<34}{'st':<5}read-back raw")
    for value in [2, 2.5, "3.75", " 4.5 ", "abc", "", 1.23456789012345, 1.2345678901234567890123456789,
                  123456789.123456789, -1.5, 1e20, 1e-9, True]:
        st, got = put(A, value)
        rows.append(f"  {repr(value):<34}{st:<5}{got}")

    rows.append("\n=== clear: 0.0 vs null (three rows, one value each)")
    for vid, label, value in [(A, "_a", 0.0), (B, "_b", None), (C, "_c", 1.0)]:
        st, got = put(vid, value)
        rows.append(f"  {label} <- {repr(value):<6} {st}  reads {got}")


    def count(filt, fields=(F,)):
        r = search(MINE + [filt], list(fields), size=50)
        if not r.ok:
            return f"ERR {r.status_code} " + json.dumps(r.json()["errors"][0])
        return len(r.json()["data"])

    def summarize(kind="sum"):
        r = c.post("/entity/versions/_summarize", headers=ARR,
                   json={"filters": MINE, "summary_fields": [{"field": F, "type": kind}]})
        return r.status_code, (raw(r.text, F) if r.ok else json.dumps(r.json()["errors"][0]))

    rows.append(f"\n=== filter: 3 rows in scope — _a=0.0  _b=null  _c=1.0   (baseline {count(['id', 'is_not', None])})")
    for label, filt in [
        ("is 1.0      (float)   ", [F, "is", 1.0]),
        ("is '1.0'    (string)  ", [F, "is", "1.0"]),
        ("is 0.0      (float)   ", [F, "is", 0.0]),
        ("is None               ", [F, "is", None]),
        ("is_not None           ", [F, "is_not", None]),
        ("greater_than 0.0      ", [F, "greater_than", 0.0]),
        ("less_than 2.0         ", [F, "less_than", 2.0]),
        ("between [0.0, 2.0]    ", [F, "between", [0.0, 2.0]]),
        ("in [1.0, 0.0]         ", [F, "in", [1.0, 0.0]]),
        ("not_in [1.0]          ", [F, "not_in", [1.0]]),
        ("NEG is 99999.5        ", [F, "is", 99999.5]),
        ("NEG in [99999.5]      ", [F, "in", [99999.5]]),
        ("NEG greater_than 1e9  ", [F, "greater_than", 1e9]),
        ("is 1        (int)     ", [F, "is", 1]),
        ("greater_than 0  (int) ", [F, "greater_than", 0]),
        ("in [1]      (int)     ", [F, "in", [1]]),
    ]:
        rows.append(f"  {label} -> {count(filt)}")

    rows.append("\n=== filter: equality against a long decimal (does the stored precision defeat `is`?)")
    LONG = 1.23456789012345
    st, got = put(C, LONG)
    rows.append(f"  _c <- {LONG!r}  {st}  reads {got}")
    for label, v in [("is exact", LONG), ("is float(read-back)", None), ("is 1.2345678901", 1.2345678901),
                     ("is 1.23", 1.23), ("between [1.2, 1.3]", [1.2, 1.3])]:
        if v is None:
            v = float(got.strip('"'))
            label = f"is {v!r} (round-tripped)"
        rows.append(f"  {label:<34} -> {count([F, 'between' if isinstance(v, list) else 'is', v])}")

    rows.append("\n=== how coarse is the comparison? _c holds exactly 1.5")
    st, got = put(C, 1.5)
    rows.append(f"  _c <- 1.5  {st}  reads {got}")
    for v in (1.5, 1.5000004, 1.500001, 1.4999999):
        rows.append(f"  is {v!r:<18} -> {count([F, 'is', v])}")

    rows.append("\n=== underflow: 1e-9 read back as 0.0 — does it then filter as zero, or as null?")
    st, got = put(C, 1e-9)
    rows.append(f"  _c <- 1e-09  {st}  reads {got}   is 0.0 -> {count([F, 'is', 0.0])}"
                f"   is None -> {count([F, 'is', None])}")

    rows.append("\n=== is the 6dp rounding applied on write, or only on read? sum the three rows")
    for vid, label in [(A, "_a"), (B, "_b"), (C, "_c")]:
        st, got = put(vid, 1.0)
        rows.append(f"  {label} <- 1.0        {st}  reads {got}")
    rows.append(f"  _summarize sum          -> {summarize()}   <- control, three exact values")
    SUB = 1.0000004  # the 7th decimal: each row reads back 1.0, three of them cannot sum past 3.0
    for vid, label in [(A, "_a"), (B, "_b"), (C, "_c")]:
        st, got = put(vid, SUB)
        rows.append(f"  {label} <- {SUB!r}  {st}  reads {got}")
    rows.append(f"  _summarize sum          -> {summarize()}   <- 3.0 means the write rounded;"
                f" {3 * SUB!r} means only the read does")

    rows.append("\n=== BigDecimal is in the accepted set — can a JSON body send one?")
    LIT = "1.00000000000000000000000000000000000001"
    r = c.request("PUT", f"/entity/versions/{C}", headers={"Content-Type": "application/json"},
                  data=('{"%s": %s}' % (F, LIT)).encode())
    back = c.get(f"/entity/versions/{C}", params={"fields": F})
    rows.append(f"  raw body literal {LIT} -> {r.status_code} reads {raw(back.text, F)}")

    st, got = put(C, 1.0)
    rows.append(f"\n  reset _c <- 1.0  {st}  reads {got}")

    rows.append(f"\n=== control: the same inputs into the stock `number` field {NUM}, on the same row")
    for value in (2, 2.5, "3"):
        st, got = put(C, value, field=NUM)
        rows.append(f"  {repr(value):<8}{st}  {got if st == 200 else json.loads(got)['title']}")
    put(C, None, field=NUM)

_lib.emit("field_types/float", "\n".join(rows), env)
