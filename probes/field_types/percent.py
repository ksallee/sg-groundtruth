"""Q: how does a `percent` field read, write, clear and filter — and is 50% stored as 50 or as 0.5?

The scale is the one thing a caller cannot guess, and a bound is the second: if the store accepts 1000
then no client may treat the value as a fraction of a whole. Everything before `--write` is read-only;
the mutations happen on throwaway Shots in the sandbox project only.
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
PCTS = ["sg_vendor_percentage_complete", "sg___complete"]
F = PCTS[0]
CODE = "zzprobe_percent"
rows = []


def raw(text, key):
    """The value exactly as it came over the wire — json.loads would erase the string/number split."""
    m = re.search(rf'"{key}":\s*("(?:[^"\\]|\\.)*"|[^,}}]+)', text)
    return m.group(1) if m else "<absent>"


def search(filters, fields, size=20, entity="shots"):
    return c.post(f"/entity/{entity}/_search", headers=ARR,
                  json={"filters": filters, "fields": fields, "page": {"size": size}})


# ---------------------------------------------------------------- read-only
rows.append("=== schema  (GET /schema/Shot/fields/<field>)")
for f in PCTS:
    d = c.get(f"/schema/Shot/fields/{f}").json()["data"]
    rows.append(f"  {f:<30} data_type={d['data_type']['value']:<8} editable={d['editable']['value']} "
                f"properties={json.dumps({k: v['value'] for k, v in d['properties'].items()})}")

rows.append("\n=== the API enumerates its own operators (bogus relation -> 400, whole errors[])")
for label, entity, field in [("percent", "shots", F),
                             ("number ", "versions", "frame_count"),
                             ("float  ", "versions", "sg_movie_aspect_ratio")]:
    r = search([[field, "definitely_not_an_operator", None]], [field], entity=entity)
    rows.append(f"  {label} {field} -> {r.status_code}")
    rows.append(f"    {json.dumps(r.json()['errors'][0], indent=2)}")

rows.append("\n=== read: how a stored percent is serialised, in the read-only projects")
for P in _lib.sample_projects(c, env):
    for f in PCTS:
        r = search([["project", "is", {"type": "Project", "id": P}], [f, "is_not", None]], PCTS, size=3)
        n = len(r.json().get("data", []))
        rows.append(f"  {f} is_not None -> {r.status_code} {n} rows" + (f"  {r.text[:200]}" if n else ""))

if not _lib.writes_allowed():
    rows.append("\n(read-only; re-run with --write for the scale / write / clear / filter half)")
    _lib.emit("field_types/percent", "\n".join(rows), env)
    sys.exit(0)

# ---------------------------------------------------------------- write half
SANDBOX = _lib.sandbox_id(c, env)
SB = ["project", "is", {"type": "Project", "id": SANDBOX}]
MINE = [SB, ["code", "starts_with", CODE]]
made = []


def make(suffix):
    r = c.post("/entity/shots", json={"project": {"type": "Project", "id": SANDBOX},
                                      "code": f"{CODE}_{suffix}"})
    made.append(r.json()["data"]["id"])
    return made[-1]


A, B, C = (make(s) for s in "abc")
rows.append(f"\n=== sandbox Shots {CODE}_a/_b/_c created -> {len(made)}")


def put(sid, value, field=F):
    r = c.request("PUT", f"/entity/shots/{sid}", json={field: value})
    if not r.ok:
        return r.status_code, json.dumps(r.json()["errors"][0])
    back = c.get(f"/entity/shots/{sid}", params={"fields": field})
    return r.status_code, raw(back.text, field)


rows.append(f"\n=== scale: is 50% written as 50 or as 0.5?  ({F})")
for value in (50, 0.5, 1, 100):
    st, got = put(A, value)
    rows.append(f"  {repr(value):<8}{st}  reads {got}")

rows.append("\n=== bounds: does the store clamp, reject or accept?")
for value in (-1, 0, 101, 1000, 1000000, -1000, 2147483647, 2147483648):
    st, got = put(A, value)
    rows.append(f"  {repr(value):<12}{st}  {got}")

rows.append("\n=== write: input -> status, then the value re-read raw")
rows.append(f"  {'input (python repr)':<24}{'st':<5}read-back raw")
for value in (42, 42.5, "42", " 42 ", "50%", "abc", "", True, None, 0.001):
    st, got = put(A, value)
    rows.append(f"  {repr(value):<24}{st:<5}{got}")

rows.append("\n=== create: the same values on POST /entity/shots, not PUT")
for value in (50, "50%", 2147483648):
    r = c.post("/entity/shots", json={"project": {"type": "Project", "id": SANDBOX},
                                      "code": f"{CODE}_new", F: value})
    if r.ok:
        made.append(r.json()["data"]["id"])
        rows.append(f"  {repr(value):<12}{r.status_code}  {raw(r.text, F)}")
    else:
        rows.append(f"  {repr(value):<12}{r.status_code}  {json.dumps(r.json()['errors'][0])}")

rows.append("\n=== clear: 0 vs null (three rows, one value each)")
for sid, label, value in [(A, "_a", 0), (B, "_b", None), (C, "_c", 50)]:
    st, got = put(sid, value)
    rows.append(f"  {label} <- {repr(value):<6} {st}  reads {got}")
untouched = make("d")
rows.append(f"  a Shot created without the field ever set reads "
            f"{raw(c.get(f'/entity/shots/{untouched}', params={'fields': F}).text, F)}")


def count(filt, fields=(F,)):
    r = search(MINE + [filt], list(fields), size=50)
    if not r.ok:
        return f"ERR {r.status_code} " + json.dumps(r.json()["errors"][0])
    return len(r.json()["data"])


base = count(["id", "is_not", None])
rows.append(f"\n=== filter: _a=0  _b=null  _c=50  _new=50  _d=never set   (baseline {base})")
for label, filt in [
    ("is 50       (int)     ", [F, "is", 50]),
    ("is 50.0     (float)   ", [F, "is", 50.0]),
    ("is '50'     (string)  ", [F, "is", "50"]),
    ("is 0.5      (float)   ", [F, "is", 0.5]),
    ("is 0                  ", [F, "is", 0]),
    ("is None               ", [F, "is", None]),
    ("is_not None           ", [F, "is_not", None]),
    ("is_not 50             ", [F, "is_not", 50]),
    ("greater_than 0        ", [F, "greater_than", 0]),
    ("greater_than -1       ", [F, "greater_than", -1]),
    ("less_than 1           ", [F, "less_than", 1]),
    ("less_than 100         ", [F, "less_than", 100]),
    ("between [0, 100]      ", [F, "between", [0, 100]]),
    ("between [0, 0.9]      ", [F, "between", [0, 0.9]]),
    ("in [50, 0]            ", [F, "in", [50, 0]]),
    ("not_in [50]           ", [F, "not_in", [50]]),
    ("NEG is 99999          ", [F, "is", 99999]),
    ("NEG in [99999]        ", [F, "in", [99999]]),
    ("NEG between [200, 300]", [F, "between", [200, 300]]),
    ("NEG greater_than 1e9  ", [F, "greater_than", 1e9]),
    ("between 50 (not a list)", [F, "between", 50]),
    ("contains '5'          ", [F, "contains", "5"]),
]:
    rows.append(f"  {label} -> {count(filt)}")

gone = [c.request("DELETE", f"/entity/shots/{i}").status_code for i in made]
rows.append(f"\ncleanup: DELETE {len(made)} probe Shots -> {sorted(set(gone))}")

_lib.emit("field_types/percent", "\n".join(rows), env)
