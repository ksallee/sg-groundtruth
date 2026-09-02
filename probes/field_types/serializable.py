"""Q: how does a `serializable` field read, write, clear and filter?

Field-type matrix entry. A one-off scan of all 114 entity types on this site found exactly six
serializable fields, so the probe checks that list rather than looping /schema/<Type>/fields (probe 002):

    EventLogEntry.meta         not editable    Task.splits            editable
    Project.tracking_settings  editable        Task.split_durations   not editable
    RvLicense.meta             editable        SavedFilter.filters    editable

Project.tracking_settings is a live site-wide configuration object; it is read here and never written.
SavedFilter and RvLicense have no `project` field, so a write to either would land outside the sandbox.
That leaves Task.splits as the only project-scoped editable serializable field on this site, and every
write below goes to a throwaway Task in the sandbox project which is deleted at the end of the run.

The read-only half — schema, the operator list, and the shape of two real stored values — runs ungated.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
FIELD = "splits"
CONTENT = "zzprobe_serializable"
KNOWN = [("Task", ("splits", "split_durations")), ("Project", ("tracking_settings",)),
         ("EventLogEntry", ("meta",)), ("SavedFilter", ("filters",)), ("RvLicense", ("meta",))]
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
    if not r.ok:
        return None, r
    return r.json()["data"], None


# ---------------------------------------------------------------- read-only
SAMPLE = _lib.sample_projects(c, env)[0]

rows.append("=== schema: every serializable field on this site")
for etype, fields in KNOWN:
    sch = c.get(f"/schema/{etype}/fields").json()["data"]
    for f in fields:
        d = sch[f]
        rows.append(f"  {etype}.{f:<20} editable={str((d.get('editable') or {}).get('value')):<5} "
                    f"properties={json.dumps(d.get('properties'), default=str)}")

rows.append("\n=== the operator list the API enumerates for this type (probe 017)")
for entity, field in (("tasks", FIELD), ("projects", "tracking_settings")):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": [[field, "definitely_not_an_operator", None]],
                     "fields": ["id"], "page": {"size": 1}})
    rows.append(f"  [[{field!r}, 'definitely_not_an_operator', None]] on /{entity} -> {r.status_code}")
    rows.append(errs(r))

rows.append("\n=== does any ordinary operator work on a serializable field?")
for op, val in [("is", None), ("is_not", None), ("is", {}), ("contains", "x"), ("in", [[]])]:
    _, bad = search("tasks", [["project", "is", {"type": "Project", "id": SAMPLE}], [FIELD, op, val]],
                    fields=("id",), size=1)
    rows.append(f"  {FIELD} {op} {val!r} -> {'200' if bad is None else bad.status_code}"
                f"{'' if bad is None else '  ' + json.loads(errs(bad))[0]['title']}")

rows.append("\n=== read: Project.tracking_settings, verbatim (configuration, not user data)")
r = c.get(f"/entity/projects/{SAMPLE}", params={"fields": "tracking_settings"})
body = r.json()
rows.append(f"  GET /entity/projects/<id>?fields=tracking_settings -> {r.status_code}")
rows.append(f"  raw response body: {r.text}")
ts = body["data"]["attributes"].get("tracking_settings")
rows.append(f"  python type of the value: {type(ts).__name__}"
            f"{'  <- a STRING holding JSON' if isinstance(ts, str) else '  <- a JSON object'}")
rows.append(f"  keys in `relationships`: {sorted((body['data'].get('relationships') or {}).keys())}")

rows.append("\n=== read: EventLogEntry.meta — a stored value with mixed types")
data, bad = search("event_log_entries", [["event_type", "is", "Shotgun_Task_Change"]],
                   fields=("meta",), size=1)
if bad is not None:
    rows.append(errs(bad))
else:
    meta = data[0]["attributes"]["meta"]
    _lib.note_from(meta)
    rows.append(f"  python type: {type(meta).__name__}")
    rows.append(f"  value: {json.dumps(meta, indent=1)}")
    rows.append("  per-key python types: " + ", ".join(
        f"{k}:{type(v).__name__}" for k, v in meta.items()))

rows.append("\n=== read: Task.splits on the sample project")
data, bad = search("tasks", [["project", "is", {"type": "Project", "id": SAMPLE}]],
                   fields=("id", FIELD, "split_durations"), size=3)
for row in data or []:
    a = row["attributes"]
    rows.append(f"  id=<id> splits={a.get(FIELD)!r}({type(a.get(FIELD)).__name__}) "
                f"split_durations={a.get('split_durations')!r}")

# ---------------------------------------------------------------- writes
if not _lib.writes_allowed():
    rows.append("\n(read-only run; re-run with --write for write / round trip / size / clear)")
    _lib.emit("field_types/serializable", "\n".join(rows), env)
    raise SystemExit

SANDBOX = _lib.sandbox_id(c, env)


def put(tid, value, field=FIELD):
    return c.request("PUT", f"/entity/tasks/{tid}", headers=JSN, json={field: value})


def readback(tid, field=FIELD):
    return c.get(f"/entity/tasks/{tid}", params={"fields": field}).json()["data"]["attributes"].get(field)


rows.append("\n=== throwaway Task in the sandbox, with dates so a split has something to divide")
existing, _ = search("tasks", [["project", "is", {"type": "Project", "id": SANDBOX}],
                               ["content", "is", CONTENT]], fields=("id",), size=1)
if existing:
    TID = existing[0]["id"]
else:
    r = c.post("/entity/tasks", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "content": CONTENT,
                     "start_date": "2026-01-01", "due_date": "2026-01-10", "duration": 4800})
    if not r.ok:
        rows.append(f"  create -> {r.status_code}")
        rows.append(errs(r))
        _lib.emit("field_types/serializable", "\n".join(rows), env)
        raise SystemExit
    TID = r.json()["data"]["id"]
rows.append(f"  Task {CONTENT!r} created; an untouched serializable field reads {readback(TID)!r}")

rows.append("\n=== write: what does the type layer accept, and what does it store?")
CASES = [
    ("array of hashes, split keys", [{"start_date": "2026-01-01", "end_date": "2026-01-02",
                                      "duration": 480}]),
    ("array of hashes, arbitrary keys", [{"foo": "bar"}]),
    ("array of hashes, empty hash", [{}]),
    ("empty array", []),
    ("two hashes in the array", [{"start_date": "2026-01-01", "end_date": "2026-01-02",
                                  "duration": 480},
                                 {"start_date": "2026-01-05", "end_date": "2026-01-06",
                                  "duration": 480}]),
    ("top-level object", {"a": {"b": [1, 2, 3]}}),
    ("array of ints", [1, 2, 3]),
    ("array of mixed scalars", [1, "two", None, True]),
    ("non-ASCII value", [{"note": "café 日本語 ✓"}]),
    ("non-ASCII key", [{"clé": 1}]),
    ("nested 12 levels", json.loads("[" * 12 + "1" + "]" * 12)),
    ("scalar int", 42),
    ("scalar float", 2.5),
    ("scalar bool", True),
    ("scalar string", "hello"),
    ("a STRING holding JSON", '[{"a": 1}]'),
]
for label, value in CASES:
    r = put(TID, value)
    back = readback(TID)
    verdict = "stored" if r.ok and back == value else (
        "accepted, stored nothing" if r.ok else "rejected")
    rows.append(f"  {label:<33} -> {r.status_code} {verdict}, reads back "
                f"{json.dumps(back, ensure_ascii=False)}")
    if not r.ok:
        rows.append(errs(r))

rows.append("\n=== round trip fidelity: a structure with mixed types")
MIXED = [{"z_int": 7, "a_float": 2.5, "m_float_whole": 1.0, "bool_t": True, "bool_f": False,
          "nul": None, "nested_list": [1, [2, [3]], {"k": "v"}], "empty_obj": {}, "empty_list": [],
          "unicode": "café 日本語 ✓", "big_int": 2 ** 40, "empty_str": "",
          "zero": 0}]
r = put(TID, MIXED)
back = readback(TID)
rows.append(f"  PUT -> {r.status_code}")
rows.append(f"  sent: {json.dumps(MIXED, ensure_ascii=False)}")
rows.append(f"  read: {json.dumps(back, ensure_ascii=False)}")
rows.append(f"  identical byte for byte: {json.dumps(MIXED) == json.dumps(back)}")
if not r.ok:
    rows.append(errs(r))

rows.append("\n=== size: how large a body does the endpoint take?   (one hash, one long value)")
for n in (1_000, 100_000, 1_000_000, 5_000_000):
    payload = [{"note": "x" * n}]
    nbytes = len(json.dumps({FIELD: payload}))
    t = time.time()
    r = put(TID, payload)
    rows.append(f"  {nbytes:>9} bytes -> {r.status_code} in {time.time() - t:.1f}s,"
                f" reads back {json.dumps(readback(TID))}")
    if not r.ok:
        rows.append(errs(r))
        break
else:
    rows.append("  no ceiling found up to the largest body tried")
rows.append("  a payload of many hashes fails on the setter, not on size:")
r = put(TID, [{"start_date": "2026-01-01", "end_date": "2026-01-02", "duration": 480}] * 100)
rows.append(f"  100 well-formed split hashes, 7312 bytes -> {r.status_code}")
rows.append(errs(r))

rows.append("\n=== clear: null, empty object, empty array, empty string")
for label, value in [("null", None), ("empty object {}", {}), ("empty array []", []),
                     ("empty string ''", "")]:
    r = put(TID, value)
    rows.append(f"  {label:<18} -> {r.status_code} reads back {readback(TID)!r}")
    if not r.ok:
        rows.append(errs(r))

rows.append("\n=== cleanup")
r = c.request("DELETE", f"/entity/tasks/{TID}")
rows.append(f"  DELETE /entity/tasks/<id> -> {r.status_code}")

_lib.emit("field_types/serializable", "\n".join(rows), env)
