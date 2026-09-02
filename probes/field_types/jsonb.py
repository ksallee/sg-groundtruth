"""Q: how does a `jsonb` field read, write, clear and filter, and how does it differ from `serializable`?

Field-type matrix entry. A sweep of /schema/<Type>/fields across every entity type in /schema finds the
jsonb fields; on this site there are two, both declared `editable: false`:

    EventLogEntry.audit_trail        Note.meta

Note.meta turns out to be writable on create and refused on update, so the write half creates a throwaway
Note per case in the sandbox project and deletes every one. EventLogEntry.audit_trail is a site-wide audit
log and is only read here.

The read-only half — the sweep, the operator list, and the filter behaviour of both fields — runs ungated.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
SUBJECT = "zzprobe_jsonb"
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors"), indent=1)
    except ValueError:
        return r.text


def search(entity, filters, fields=("id",), size=500):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": list(filters), "fields": list(fields), "page": {"size": size}})
    if not r.ok:
        return None, r
    return r.json()["data"], None


# ---------------------------------------------------------------- read-only
SAMPLE = _lib.sample_projects(c, env)[0]

rows.append("=== sweep /schema/<Type>/fields for data_type jsonb")
types = sorted(c.get("/schema").json()["data"].keys())
found = []
for etype in types:
    r = c.get(f"/schema/{etype}/fields")
    if not r.ok:
        continue
    for name, d in r.json()["data"].items():
        if (d.get("data_type") or {}).get("value") == "jsonb":
            found.append((etype, name, d))
rows.append(f"  {len(types)} entity types scanned, {len(found)} jsonb fields")
for etype, name, d in found:
    rows.append(f"  {etype}.{name:<14} editable={str((d.get('editable') or {}).get('value')):<5} "
                f"properties={json.dumps(d.get('properties'), default=str)}")

rows.append("\n=== the operator list the API enumerates for this type (probe 017)")
for entity, field in (("notes", "meta"), ("event_log_entries", "audit_trail")):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": [[field, "definitely_not_an_operator", None]],
                     "fields": ["id"], "page": {"size": 1}})
    rows.append(f"  [[{field!r}, 'definitely_not_an_operator', None]] on /{entity} -> {r.status_code}")
    rows.append(errs(r))

rows.append("\n=== read: Note.meta on the sample project")
data, bad = search("notes", [["project", "is", {"type": "Project", "id": SAMPLE}]],
                   fields=("meta", "subject"), size=3)
if bad is not None:
    rows.append(errs(bad))
for row in data or []:
    _lib.note_from(row)
    m = row["attributes"].get("meta")
    rows.append(f"  id=<id> meta={m!r} ({type(m).__name__}) "
                f"relationships={sorted((row.get('relationships') or {}).keys())}")

rows.append("\n=== read: EventLogEntry.audit_trail, asked for by name")
r = c.post("/entity/event_log_entries/_search", headers=ARR,
           json={"filters": [], "fields": ["audit_trail", "event_type"], "page": {"size": 2}})
rows.append(f"  fields=audit_trail,event_type -> {r.status_code}")
for row in r.json()["data"]:
    rows.append(f"  attributes keys returned: {sorted(row['attributes'].keys())}")

rows.append("\n=== does the filter narrow anything?   (500 is the page cap, not a total)")
for entity, field in (("notes", "meta"), ("event_log_entries", "audit_trail")):
    base, _ = search(entity, [])
    for op in ("is", "is_not"):
        got, bad = search(entity, [[field, op, None]])
        rows.append(f"  {entity}.{field} {op} null -> "
                    f"{len(got) if bad is None else errs(bad)} of {len(base)} unfiltered")

rows.append("\n=== filter values the operators refuse")
for op, val in [("is", "x"), ("contains", "x"), ("contains", None), ("in", None), ("is", [])]:
    _, bad = search("notes", [["meta", op, val]], size=1)
    rows.append(f"  meta {op} {val!r} -> {'200' if bad is None else bad.status_code}")
    if bad is not None:
        rows.append(errs(bad))

# ---------------------------------------------------------------- writes
if not _lib.writes_allowed():
    rows.append("\n(read-only run; re-run with --write for write / round trip / filter / clear)")
    _lib.emit("field_types/jsonb", "\n".join(rows), env)
    raise SystemExit

SANDBOX = _lib.sandbox_id(c, env)
BASE = [["project", "is", {"type": "Project", "id": SANDBOX}], ["subject", "is", SUBJECT]]

CASES = [
    ("nested object", {"a": {"b": [1, 2, 3]}, "c": True, "d": None}),
    ("array of hashes", [{"x": 1}, {"y": 2}]),
    ("array of scalars", [1, "two", None, True]),
    ("empty object", {}),
    ("empty array", []),
    ("non-ASCII key and value", {"clé": "café 日本語 ✓"}),
    ("mixed types, unsorted keys", {"z": 1, "a": 2, "m_float_whole": 1.0, "f": 2.5, "big": 2 ** 40,
                                    "t": True, "n": None, "eo": {}, "el": [], "es": "", "zero": 0}),
    ("null", None),
    ("scalar int", 42),
    ("scalar float", 2.5),
    ("scalar bool", True),
    ("scalar string", "hello"),
    ("a STRING holding JSON", '{"a": 1}'),
    ("empty string", ""),
]

with _lib.Created(c) as made:
    rows.append("\n=== write: PUT on an existing Note")
    r = c.post("/entity/notes", headers=JSN,
               json={"project": {"type": "Project", "id": SANDBOX}, "subject": SUBJECT,
                     "content": "zzprobe", "meta": {"k": "v"}})
    if not r.ok:
        rows.append(errs(r))
        _lib.emit("field_types/jsonb", "\n".join(rows), env)
        raise SystemExit
    NID = made.add("notes", r.json()["data"]["id"])
    pr = c.request("PUT", f"/entity/notes/{NID}", headers=JSN, json={"meta": {"k": "v2"}})
    back = c.get(f"/entity/notes/{NID}",
                 params={"fields": "meta"}).json()["data"]["attributes"].get("meta")
    rows.append(f"  PUT meta -> {pr.status_code}, still reads {json.dumps(back)}")
    rows.append(errs(pr))

    rows.append("\n=== write: POST /entity/notes with meta set, then read the row back")
    stored = []
    for label, value in CASES:
        r = c.post("/entity/notes", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "subject": SUBJECT,
                         "content": "zzprobe", "meta": value})
        if not r.ok:
            rows.append(f"  {label:<27} -> {r.status_code}")
            rows.append(errs(r))
            continue
        nid = made.add("notes", r.json()["data"]["id"])
        got = c.get(f"/entity/notes/{nid}",
                    params={"fields": "meta"}).json()["data"]["attributes"].get("meta")
        stored.append((label, value, got))
        rows.append(f"  {label:<27} -> {r.status_code} reads back "
                    f"{json.dumps(got, ensure_ascii=False)}, equal={got == value}")

    rows.append("\n=== round trip fidelity")
    for label, value, got in stored:
        sent_j = json.dumps(value, ensure_ascii=False)
        back_j = json.dumps(got, ensure_ascii=False)
        rows.append(f"  {label:<27} value equal={got == value} bytes equal={sent_j == back_j}")
        if sent_j != back_j:
            rows.append(f"    sent: {sent_j}")
            rows.append(f"    read: {back_j}")

    rows.append("\n=== filter: what each operator matches, against the rows just written")
    FILTERS = [
        ("is", {"a": {"b": [1, 2, 3]}, "c": True, "d": None}),
        ("is", {"c": True, "d": None, "a": {"b": [1, 2, 3]}}),
        ("is", {"a": {"b": [1, 2, 3]}}),
        ("is", {}),
        ("is", [[]]),
        ("is", None),
        ("is_not", None),
        ("contains", {"c": True}),
        ("contains", {"a": {"b": [1]}}),
        ("contains", {"clé": "café 日本語 ✓"}),
        ("contains", {"m_float_whole": 1}),
        ("contains", {}),
        ("contains", {"x": 1}),
        ("contains", [{"x": 1}]),
        ("not_contains", {"c": True}),
    ]
    for op, val in FILTERS:
        got, bad = search("notes", BASE + [["meta", op, val]], fields=("meta",), size=50)
        if bad is not None:
            rows.append(f"  meta {op} {json.dumps(val, ensure_ascii=False)} -> {bad.status_code}")
            rows.append(errs(bad))
            continue
        vals = json.dumps([g["attributes"]["meta"] for g in got], ensure_ascii=False)
        rows.append(f"  meta {op} {json.dumps(val, ensure_ascii=False):<46} -> {len(got)} rows "
                    f"{vals[:150]}")

    rows.append("\n=== clear: can a stored value be emptied on the row that holds it?")
    for label, value in [("null", None), ("empty object {}", {}), ("empty array []", []),
                         ("empty string ''", "")]:
        pr = c.request("PUT", f"/entity/notes/{NID}", headers=JSN, json={"meta": value})
        got = c.get(f"/entity/notes/{NID}",
                    params={"fields": "meta"}).json()["data"]["attributes"].get("meta")
        rows.append(f"  PUT {label:<18} -> {pr.status_code}, reads back {json.dumps(got)}")
        if not pr.ok:
            rows.append(errs(pr))

_lib.emit("field_types/jsonb", "\n".join(rows), env)
