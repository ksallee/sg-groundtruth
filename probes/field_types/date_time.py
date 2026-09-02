"""Q: how does a date_time field read, write, clear and filter — and where does it differ from date?

date_time is the timestamp type. Almost every instance of it on a site is server-managed
(created_at, updated_at), so the probe first separates the editable ones from the rest, then does the
read/write/clear/filter matrix on an editable stock field. The trap it is hunting: a write that
silently converts to another zone, and a filter value format that differs from the write format.
"""
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

from sg_groundtruth.schema import Schema, val  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
CODE = "zzprobe_date_time"
TYPES = ["Version", "Project", "Shot", "Task", "Note"]
rows = []


def errs(r):
    """The WHOLE errors[] object. The 400 is the documentation (probe 017); never slice it."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def one_line(r):
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} {e.get('title', '')} | source={json.dumps(e.get('source'))}"
    except Exception:
        return f"{r.status_code} {r.text[:200]}"


def search(entity, filters, fields=("code",), size=500):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": list(filters), "fields": list(fields), "page": {"size": size}})
    return (r.json()["data"], None) if r.ok else (None, r)


def count(entity, filters, size=500):
    d, r = search(entity, filters, size=size)
    return len(d) if d is not None else one_line(r)


def parse_iso(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


# --- 1. schema: every date_time on this site, and the editable flag that separates them ----------
rows.append("=== 1. schema — date_time fields and their `editable` flag")
sc = Schema(c, project_id=None)
n_total = n_edit = 0
editable_fields = []
for t in TYPES:
    for name, f in sorted(sc.fields(t).items()):
        if val(f.get("data_type", {})) != "date_time":
            continue
        n_total += 1
        e = val(f.get("editable", {}), False)
        n_edit += bool(e)
        if e:
            editable_fields.append(f"{t}.{name}")
        rows.append(f"  {t + '.' + name:<44} editable={str(bool(e)):<5} {val(f.get('name', {}), '')}")
rows.append(f"  -> {n_edit} of {n_total} editable across {TYPES}; editable = {editable_fields}")

# --- 2. operators, straight out of a bogus relation (probe 017) ----------------------------------
rows.append("\n=== 2. operators — the API enumerates them in the 400")
valid_ops = []
for field in ("created_at", "client_approved_at"):
    _, r = search("versions", [[field, "definitely_not_an_operator", None]], size=1)
    if r is None:
        rows.append(f"  Version.{field}: bogus operator ACCEPTED (no 400) — operators are not validated")
        continue
    body = errs(r)
    m = re.search(r'Valid relations: (\[[^\]]*\])', body)
    ops = json.loads(m.group(1).replace('\\"', '"')) if m else []
    if field == "created_at":
        rows.append(f"  Version.created_at, full errors[] verbatim:\n{body}")
    else:
        rows.append(f"  Version.client_approved_at -> same list: {ops == valid_ops}  ({len(ops)} relations)")
    valid_ops = valid_ops or ops
rows.append(f"  Valid relations = {json.dumps(valid_ops)}")
# The sibling `date` type: same relations, or fewer? One read-only 400 settles it.
_, r = search("shots", [["sg_turnover_date", "definitely_not_an_operator", None]], size=1)
m = re.search(r'Valid relations: (\[[^\]]*\])', errs(r)) if r is not None else None
date_ops = json.loads(m.group(1).replace('\\"', '"')) if m else []
rows.append(f"  contrast, Shot.sg_turnover_date ('date'): identical={date_ops == valid_ops} "
            f"{json.dumps(date_ops)}")

# --- 3. read: the serialised shape and its zone ---------------------------------------------------
rows.append("\n=== 3. read — exact serialised shape")
now_utc = datetime.now(timezone.utc)
local_off = datetime.now().astimezone().utcoffset()
rows.append(f"  client clock: utc={now_utc.isoformat()}  local utcoffset={local_off}")

g = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": "code,created_at,updated_at", "page[size]": 3}).json()
_lib.note_from(g)
for row in g["data"][:3]:
    a = row["attributes"]
    rows.append(f"  GET  attributes: created_at={a.get('created_at')!r}  updated_at={a.get('updated_at')!r}")
s, _ = search("versions", [["project", "is", {"type": "Project", "id": PROJECT}]],
              fields=("created_at",), size=2)
if s:
    _lib.note_from(s)
    rows.append(f"  POST _search attributes: {json.dumps(s[0]['attributes'])}")
    rows.append(f"  lands in attributes (not relationships); keys present: {sorted(s[0])}")

# newest updated_at in the project vs the client's UTC clock — a lag, not a zone shift, if UTC
newest = None
r = c.post("/entity/versions/_search", headers=ARR,
           json={"filters": [["project", "is", {"type": "Project", "id": PROJECT}]],
                 "fields": ["updated_at"], "sort": "-updated_at", "page": {"size": 1}})
if r.ok and r.json()["data"]:
    newest = r.json()["data"][0]["attributes"]["updated_at"]
    d = parse_iso(newest)
    rows.append(f"  newest updated_at in project = {newest!r}  ({(now_utc - d).total_seconds() / 3600:.2f}h "
                f"before client UTC now)")
else:
    rows.append(f"  sort by -updated_at -> {one_line(r)}")

# --- 4-7. writes -----------------------------------------------------------------------------------
FIELD = "client_approved_at"
BASE = datetime(2026, 3, 4, 5, 6, 7, tzinfo=timezone.utc)
EPOCH = int(BASE.timestamp())

if not _lib.writes_allowed():
    rows.append("\n(read-only run; write / clear / read-only-field / filter-on-a-known-value need --write)")
else:
    # A probe leaves no trace: the throwaway Version is deleted on the way out.
    with _lib.Created(c) as created:
        SANDBOX = _lib.sandbox_id(c, env)
        scope = [["project", "is", {"type": "Project", "id": SANDBOX}], ["code", "is", CODE]]
        existing, _ = search("versions", scope, size=10)
        if existing:
            vid = existing[0]["id"]
        else:
            t0 = datetime.now(timezone.utc)
            cr = c.post("/entity/versions", headers=JSN,
                        json={"project": {"type": "Project", "id": SANDBOX}, "code": CODE})
            t1 = datetime.now(timezone.utc)
            vid = created.add("versions", cr.json()["data"]["id"])
            back = c.get(f"/entity/versions/{vid}", params={"fields": "created_at"}).json()["data"]
            made = back["attributes"]["created_at"]
            rows.append(f"\n  created a Version at client UTC {t0.isoformat()}..{t1.isoformat()}")
            rows.append(f"  server created_at = {made!r} -> {(parse_iso(made) - t0).total_seconds():+.1f}s "
                        f"from the client's UTC clock")
        rows.append(f"\n  throwaway Version {CODE} id={vid} in the sandbox project")

        def put(value):
            return c.request("PUT", f"/entity/versions/{vid}", headers=JSN, json={FIELD: value})

        def read_back():
            return c.get(f"/entity/versions/{vid}",
                         params={"fields": FIELD}).json()["data"]["attributes"].get(FIELD)

        rows.append("\n=== 4. write — which input formats are accepted, and what comes back")
        for label, v in [
            ("ISO Z",                 "2026-03-04T05:06:07Z"),
            ("ISO +05:00",            "2026-03-04T05:06:07+05:00"),
            ("ISO -08:00",            "2026-03-04T05:06:07-08:00"),
            ("ISO no zone",           "2026-03-04T05:06:07"),
            ("space, no zone",        "2026-03-04 05:06:07"),
            ("fractional seconds",    "2026-03-04T05:06:07.123Z"),
            ("date only",             "2026-03-04"),
            ("epoch int",             EPOCH),
            ("epoch string",          str(EPOCH)),
            ("garbage",               "not-a-time"),
        ]:
            r = put(v)
            if r.ok:
                got = read_back()
                same = "SAME" if got == v else "NORMALISED"
                rows.append(f"  {label:<20} {json.dumps(v):<30} -> {r.status_code} read back {got!r}  {same}")
            else:
                rows.append(f"  {label:<20} {json.dumps(v):<30} -> {one_line(r)}")
                if label in ("date only", "epoch int"):
                    rows.append(f"    full errors[]:\n{errs(r)}")

        rows.append("\n=== 5. clear")
        for label, v in [("null", None), ('""', "")]:
            put("2026-03-04T05:06:07Z")
            r = put(v)
            if r.ok:
                rows.append(f"  {FIELD} = {label:<6} -> {r.status_code} read back {read_back()!r}")
            else:
                rows.append(f"  {FIELD} = {label:<6} -> {one_line(r)}\n{errs(r)}")

        rows.append("\n=== 6. writing a server-managed timestamp")
        r = c.request("PUT", f"/entity/versions/{vid}", headers=JSN,
                      json={"created_at": "2020-01-01T00:00:00Z"})
        rows.append(f"  PUT created_at -> {r.status_code}\n{errs(r)}")

        # --- 7. filters, one row of ground truth ------------------------------------------------------
        rows.append("\n=== 7. filter — value format for every relation the API named")
        KNOWN = "2026-03-04T05:06:07Z"
        put(KNOWN)
        stored = read_back()
        rows.append(f"  ground truth: exactly 1 Version in sandbox with {FIELD} = {stored!r}")
        EARLIER, LATER = "2026-03-04T00:00:00Z", "2026-03-05T00:00:00Z"
        DAY, NEXTDAY = "2026-03-04", "2026-03-05"

        cand = {
            "is":            [("stored value", stored), ("date-only same day", DAY), ("null", None),
                              ("NEG far future", "2099-01-01T00:00:00Z")],
            "is_not":        [("stored value", stored)],
            "less_than":     [("later instant", LATER), ("date-only same day", DAY),
                              ("NEG earlier instant", EARLIER)],
            "greater_than":  [("earlier instant", EARLIER), ("date-only same day", DAY),
                              ("NEG later instant", LATER)],
            "between":       [("[earlier, later]", [EARLIER, LATER]),
                              ("[date-only, date-only]", [DAY, NEXTDAY]),
                              ("NEG [1970, 1971]", ["1970-01-01T00:00:00Z", "1971-01-01T00:00:00Z"])],
            "not_between":   [("[earlier, later]", [EARLIER, LATER])],
            "in":            [("[stored]", [stored]), ("NEG [far future]", ["2099-01-01T00:00:00Z"])],
            "not_in":        [("[stored]", [stored])],
            "in_last":       [("[100, YEAR]", [100, "YEAR"]), ("[1, DAY]", [1, "DAY"])],
            "not_in_last":   [("[100, YEAR]", [100, "YEAR"])],
            "in_next":       [("[100, YEAR]", [100, "YEAR"]), ("[1, DAY]", [1, "DAY"])],
            "not_in_next":   [("[100, YEAR]", [100, "YEAR"])],
            "in_calendar_day":   [("0 (today)", 0)],
            "in_calendar_week":  [("0 (this week)", 0)],
            "in_calendar_month": [("0 (this month)", 0)],
            "in_calendar_year":  [("0 (this year)", 0), ("NEG -50", -50)],
            "is_null":       [("null", None)],
            "is_not_null":   [("null", None)],
            "type_is":       [("null", None)],
            "type_is_not":   [("null", None)],
        }
        for op in valid_ops:
            for label, v in cand.get(op, [("<not exercised>", None)]):
                n = count("versions", scope + [[FIELD, op, v]])
                rows.append(f"  {op:<18} {label:<24} {json.dumps(v):<46} -> {n}")

        rows.append("\n  --- in_last/in_next units: ask the API ---")
        _, r = search("versions", scope + [[FIELD, "in_last", [1, "FORTNIGHT"]]])
        rows.append(errs(r) if r is not None else "  a bogus unit was ACCEPTED")

        rows.append("\n  --- which midnight is a date-only filter value, and whose calendar day? ---")
        today = now_utc.date().isoformat()
        for v in (f"2026-03-03T23:30:00Z", f"2026-03-04T00:00:00Z", f"2026-03-04T00:30:00Z"):
            put(v)
            rows.append(f"  stored {v} -> is '{DAY}' {count('versions', scope + [[FIELD, 'is', DAY]])}"
                        f" | greater_than '{DAY}' {count('versions', scope + [[FIELD, 'greater_than', DAY]])}"
                        f" | less_than '{DAY}' {count('versions', scope + [[FIELD, 'less_than', DAY]])}")
        for v in (f"{today}T00:30:00Z", f"{today}T23:30:00Z"):
            put(v)
            rows.append(f"  stored {v} -> in_calendar_day 0/-1/+1 = "
                        f"{count('versions', scope + [[FIELD, 'in_calendar_day', 0]])}/"
                        f"{count('versions', scope + [[FIELD, 'in_calendar_day', -1]])}/"
                        f"{count('versions', scope + [[FIELD, 'in_calendar_day', 1]])}"
                        f" | in_last [1,DAY] {count('versions', scope + [[FIELD, 'in_last', [1, 'DAY']]])}"
                        f" | in_next [1,DAY] {count('versions', scope + [[FIELD, 'in_next', [1, 'DAY']]])}"
                        f" | in_calendar_week/month/year 0 = "
                        f"{count('versions', scope + [[FIELD, 'in_calendar_week', 0]])}/"
                        f"{count('versions', scope + [[FIELD, 'in_calendar_month', 0]])}/"
                        f"{count('versions', scope + [[FIELD, 'in_calendar_year', 0]])}")
        put(None)
        rows.append(f"\n  cleared; final read back {read_back()!r}"
                    f" | is null -> {count('versions', scope + [[FIELD, 'is', None]])}"
                    f" | is_not null -> {count('versions', scope + [[FIELD, 'is_not', None]])}")

actual = "\n".join(rows)
_lib.emit("field_types/date_time", actual, env)
