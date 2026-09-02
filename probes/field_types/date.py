"""Q: how does a `date` field read, write, clear and filter — and where does it diverge from `date_time`?

Stock editable date fields live on Shot. The read-only half (schema, the operator list the API
enumerates for itself, and the value-shape matrix for every operator) runs without --write; only the
write/clear half touches the sandbox project.
"""
import datetime
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
FIELD = "sg_turnover_date"
FIELD2 = "sg_client_turnover_date"
rows = []


def err(r):
    """Whole errors[] object, source included. Truncating it throws away the operator list."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def search(filt, entity="shots", fields=None, size=1, project=PROJECT):
    body = {"filters": [["project", "is", {"type": "Project", "id": project}]] + filt,
            "fields": fields or ["code", FIELD], "page": {"size": size}}
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return None, f"{r.status_code}\n{err(r)}"
    return r.json()["data"], None


def count(filt, project=PROJECT):
    """Row count for a filter, or an error string. size 500 is enough to distinguish from baseline."""
    d, e = search(filt, size=500, project=project)
    return e if e else len(d)


# --- schema: what distinguishes date from date_time ------------------------------------------------
rows.append("=== schema (site scope)")
for et, name in [("Shot", FIELD), ("Shot", FIELD2), ("Shot", "sg_date_next_version_expected"),
                 ("Shot", "created_at"), ("Shot", "updated_at")]:
    f = c.get(f"/schema/{et}/fields/{name}").json()["data"]
    p = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in f.get("properties", {}).items()}
    g = lambda k: (f.get(k) or {}).get("value")  # noqa: E731
    rows.append(f"  {et}.{name:<32} data_type={g('data_type'):<10} editable={g('editable')} "
                f"properties={json.dumps(p)}")

# --- the API enumerates its own operators (probe 017) -----------------------------------------------
rows.append("\n=== bogus operator -> Valid relations")
_, e = search([[FIELD, "definitely_not_an_operator", None]])
rows.append(e or "  no error?!")
rows.append("\n=== same, on a date_time field, for comparison")
_, e = search([["created_at", "definitely_not_an_operator", None]])
rows.append(e or "  no error?!")

# --- read: the serialised shape ---------------------------------------------------------------------
rows.append("\n=== read shape")
base = count([])
rows.append(f"  baseline shots in project: {base}")
filled, e = search([[FIELD, "is_not", None]], fields=["code", FIELD, FIELD2, "created_at", "updated_at"],
                   size=3)
rows.append(f"  {FIELD} is_not None -> {count([[FIELD, 'is_not', None]])} rows")
if filled:
    _lib.note_from(filled)
    rows.append("  raw row (attributes only):")
    rows.append(json.dumps({k: v for k, v in filled[0].items() if k != "links"}, indent=1))
    SAMPLE = filled[0]["attributes"].get(FIELD)
else:
    rows.append("  no shot in this project has the field set; filter matrix uses a synthetic date")
    SAMPLE = None
rows.append(f"  sample value from the site: {SAMPLE!r}  (type {type(SAMPLE).__name__})")

# --- filter value shapes, read-only ------------------------------------------------------------------
# A date filter that silently matches everything is the dangerous failure, so every operator gets a
# negative control that must return 0 (or the complement, for a negating operator).
D = SAMPLE or "2026-09-02"
y, mo, dy = (int(x) for x in D.split("-")) if D.count("-") == 2 else (2026, 9, 2)
day = datetime.date(y, mo, dy)
FAR = "1901-01-01"

rows.append(f"\n=== filter value shapes  (baseline {base}; a negative control must not equal it)")
rows.append(f"  probe date {D!r}")
cases = [
    ("is <date>",                      [[FIELD, "is", D]]),
    ("is <far past>  (neg control)",   [[FIELD, "is", FAR]]),
    ("is null",                        [[FIELD, "is", None]]),
    ("is ''",                          [[FIELD, "is", ""]]),
    ("is <timestamp>",                 [[FIELD, "is", f"{D}T00:00:00Z"]]),
    ("is <US 09/02/2026>",             [[FIELD, "is", day.strftime("%m/%d/%Y")]]),
    ("is <epoch int>",                 [[FIELD, "is", int(datetime.datetime(y, mo, dy).timestamp())]]),
    ("is_not <date>",                  [[FIELD, "is_not", D]]),
    ("greater_than <far past>",        [[FIELD, "greater_than", FAR]]),
    ("greater_than <far future>",      [[FIELD, "greater_than", "2999-01-01"]]),
    ("less_than <far past> (neg)",     [[FIELD, "less_than", FAR]]),
    ("between [far past, far future]", [[FIELD, "between", [FAR, "2999-01-01"]]]),
    ("between far past..far past-1",   [[FIELD, "between", ["1900-01-01", FAR]]]),
    ("between two scalars (no list)",  [[FIELD, "between", FAR, "2999-01-01"]]),
    ("in [<date>]",                    [[FIELD, "in", [D]]]),
    ("in [<far past>]  (neg control)", [[FIELD, "in", [FAR]]]),
    ("not_in [<date>]",                [[FIELD, "not_in", [D]]]),
    ("in_last 1 bare int",             [[FIELD, "in_last", 1]]),
    ("in_last [1]",                    [[FIELD, "in_last", [1]]]),
    ("in_last [100, DAY]",             [[FIELD, "in_last", [100, "DAY"]]]),
    ("in_last [100, 'DAY'] lower",     [[FIELD, "in_last", [100, "day"]]]),
    ("in_last [100000, DAY]",          [[FIELD, "in_last", [100000, "DAY"]]]),
    ("in_last [100, YEAR]",            [[FIELD, "in_last", [100, "YEAR"]]]),
    ("in_last ['DAY', 100] reversed",  [[FIELD, "in_last", ["DAY", 100]]]),
    ("in_next [100000, DAY]",          [[FIELD, "in_next", [100000, "DAY"]]]),
    ("in_next [1, DAY] (neg-ish)",     [[FIELD, "in_next", [1, "DAY"]]]),
    ("in_calendar_day 0",              [[FIELD, "in_calendar_day", 0]]),
    ("in_calendar_day [0]",            [[FIELD, "in_calendar_day", [0]]]),
    ("in_calendar_week 0",             [[FIELD, "in_calendar_week", 0]]),
    ("in_calendar_month 0",            [[FIELD, "in_calendar_month", 0]]),
    ("in_calendar_year 0",             [[FIELD, "in_calendar_year", 0]]),
    ("in_calendar_year -50",           [[FIELD, "in_calendar_year", -50]]),
    ("contains (text op)",             [[FIELD, "contains", D[:4]]]),
    ("starts_with (text op)",          [[FIELD, "starts_with", D[:4]]]),
]
for label, filt in cases:
    rows.append(f"  {label:<34} -> {count(filt)}")

rows.append("\n=== the same value shapes on a date_time field (created_at), for the diff")
for label, filt in [
    ("is <date-only>",        [["created_at", "is", D]]),
    ("is <timestamp>",        [["created_at", "is", f"{D}T00:00:00Z"]]),
    ("greater_than <date>",   [["created_at", "greater_than", FAR]]),
    ("in_last [100000, DAY]", [["created_at", "in_last", [100000, "DAY"]]]),
    ("in_calendar_day 0",     [["created_at", "in_calendar_day", 0]]),
]:
    rows.append(f"  {label:<34} -> {count(filt)}")

# --- write / clear, sandbox only ---------------------------------------------------------------------
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write/clear half)")
else:
    # A probe leaves no trace: both throwaway Shots are deleted on the way out.
    with _lib.Created(c) as made:
        SANDBOX = _lib.sandbox_id(c, env)
        CODE, CODE_NULL = "zzprobe_date", "zzprobe_date_null"

        def throwaway(code):
            found, _ = search([["code", "is", code]], project=SANDBOX)
            if found:
                return found[0]["id"]
            r = c.post("/entity/shots", headers=JSON,
                       json={"project": {"type": "Project", "id": SANDBOX}, "code": code})
            rows.append(f"  create throwaway Shot {code} -> {r.status_code}")
            return made.add("shots", r.json()["data"]["id"])

        sid, sid_null = throwaway(CODE), throwaway(CODE_NULL)
        # Siblings write into the same sandbox, so every count is scoped to these two rows: one carries
        # the probe date, one is permanently null. Positive = 1, negative = 0, no baseline drift.
        PAIR = ["code", "in", [CODE, CODE_NULL]]
        c.request("PUT", f"/entity/shots/{sid_null}", headers=JSON, json={FIELD: None})
        rows.append(f"\n=== write formats  (PUT /entity/shots/<id>, {FIELD})")

        def put(value):
            r = c.request("PUT", f"/entity/shots/{sid}", headers=JSON, json={FIELD: value})
            if not r.ok:
                return f"{r.status_code}\n{err(r)}"
            return repr(r.json()["data"]["attributes"].get(FIELD))

        def readback():
            r = c.get(f"/entity/shots/{sid}", params={"fields": FIELD})
            return repr(r.json()["data"]["attributes"].get(FIELD))

        writes = [
            ("ISO date '2026-09-02'",        "2026-09-02"),
            ("datetime.date(...)",           str(datetime.date(2026, 9, 3))),
            ("datetime.datetime isoformat",  datetime.datetime(2026, 9, 4, 13, 45, 6).isoformat()),
            ("full ISO 8601 w/ Z",           "2026-09-05T13:45:06Z"),
            ("ISO w/ offset",                "2026-09-06T13:45:06+02:00"),
            ("US style '09/07/2026'",        "09/07/2026"),
            ("EU style '08/09/2026'",        "08/09/2026"),
            ("epoch int",                    1757000000),
            ("epoch as string",              "1757000000"),
            ("short '2026-9-8'",             "2026-9-8"),
            ("slashes '2026/09/09'",         "2026/09/09"),
            ("nonsense 'tomorrow'",          "tomorrow"),
            ("out of range '2026-02-30'",    "2026-02-30"),
            ("bool True",                    True),
        ]
        for label, v in writes:
            rows.append(f"  {label:<30} {json.dumps(v, default=str):<28} -> {put(v)}  read back {readback()}")

        rows.append("\n=== clear")
        put("2026-09-02")
        rows.append(f"  null   -> {put(None)}  read back {readback()}")
        put("2026-09-02")
        rows.append(f"  ''     -> {put('')}  read back {readback()}")
        put("2026-09-02")
        rows.append(f"  false  -> {put(False)}  read back {readback()}")

        def n(filt):
            return count([PAIR] + filt, project=SANDBOX)

        put(None)
        rows.append("\n=== both rows cleared (of 2)")
        for label, filt in [("is null", [[FIELD, "is", None]]), ("is ''", [[FIELD, "is", ""]]),
                            ("is_not null", [[FIELD, "is_not", None]]),
                            ("is_not ''", [[FIELD, "is_not", ""]])]:
            rows.append(f"  {label:<12} -> {n(filt)}")

        # A known date is the only way to get a positive: nothing on this site has a date set.
        TODAY = datetime.date.today()

        # Where the value lands, and how a date_time on the same row serialises next to it.
        put(TODAY.isoformat())
        raw = c.get(f"/entity/shots/{sid}", params={"fields": f"{FIELD},created_at,updated_at"}).json()["data"]
        rows.append("\n=== raw row, date and date_time side by side")
        rows.append(json.dumps({k: v for k, v in raw.items() if k != "links"}, indent=1))

        def matrix(label, when, cases):
            rows.append(f"\n=== {label}: {CODE}.{FIELD} = {when.isoformat()}, {CODE_NULL} null"
                        "   (2 rows; positive 1, negative 0, 2 = matched the null row too)")
            put(when.isoformat())
            for lab, filt in cases:
                rows.append(f"  {lab:<36} -> {n(filt)}")

        def d(offset):
            return (TODAY + datetime.timedelta(days=offset)).isoformat()

        matrix("today", TODAY, [
            ("is today",                    [[FIELD, "is", d(0)]]),
            ("is tomorrow (neg)",           [[FIELD, "is", d(1)]]),
            ("is_not today",                [[FIELD, "is_not", d(0)]]),
            ("is null (neg)",               [[FIELD, "is", None]]),
            ("is '' (neg)",                 [[FIELD, "is", ""]]),
            ("greater_than yesterday",      [[FIELD, "greater_than", d(-1)]]),
            ("greater_than today",          [[FIELD, "greater_than", d(0)]]),
            ("less_than tomorrow",          [[FIELD, "less_than", d(1)]]),
            ("less_than today",             [[FIELD, "less_than", d(0)]]),
            ("between [today, today]",      [[FIELD, "between", [d(0), d(0)]]]),
            ("between [-1, +1]",            [[FIELD, "between", [d(-1), d(1)]]]),
            ("between [+1, +2] (neg)",      [[FIELD, "between", [d(1), d(2)]]]),
            ("between reversed [+1, -1]",   [[FIELD, "between", [d(1), d(-1)]]]),
            ("between [today, null]",       [[FIELD, "between", [d(0), None]]]),
            ("in [today]",                  [[FIELD, "in", [d(0)]]]),
            ("in [today, +1]",              [[FIELD, "in", [d(0), d(1)]]]),
            ("in [+1] (neg)",               [[FIELD, "in", [d(1)]]]),
            ("in today (bare scalar)",      [[FIELD, "in", d(0)]]),
            ("not_in [today]",              [[FIELD, "not_in", [d(0)]]]),
            ("in_last [1, DAY]",            [[FIELD, "in_last", [1, "DAY"]]]),
            ("in_last [1, MONTH]",          [[FIELD, "in_last", [1, "MONTH"]]]),
            ("in_next [1, DAY]",            [[FIELD, "in_next", [1, "DAY"]]]),
            ("in_next [1, MONTH]",          [[FIELD, "in_next", [1, "MONTH"]]]),
            ("in_last [1, HOUR]",           [[FIELD, "in_last", [1, "HOUR"]]]),
            ("not_in_last [1, MONTH]",      [[FIELD, "not_in_last", [1, "MONTH"]]]),
            ("not_in_next [1, MONTH]",      [[FIELD, "not_in_next", [1, "MONTH"]]]),
            ("in_calendar_day 0",           [[FIELD, "in_calendar_day", 0]]),
            ("in_calendar_day -1 (neg)",    [[FIELD, "in_calendar_day", -1]]),
            ("in_calendar_day 1 (neg)",     [[FIELD, "in_calendar_day", 1]]),
            ("in_calendar_day [0]",         [[FIELD, "in_calendar_day", [0]]]),
            ("in_calendar_week 0",          [[FIELD, "in_calendar_week", 0]]),
            ("in_calendar_week -1 (neg)",   [[FIELD, "in_calendar_week", -1]]),
            ("in_calendar_week 1 (neg)",    [[FIELD, "in_calendar_week", 1]]),
            ("in_calendar_month 0",         [[FIELD, "in_calendar_month", 0]]),
            ("in_calendar_month -1 (neg)",  [[FIELD, "in_calendar_month", -1]]),
            ("in_calendar_year 0",          [[FIELD, "in_calendar_year", 0]]),
            ("in_calendar_year -1 (neg)",   [[FIELD, "in_calendar_year", -1]]),
            ("in_calendar_year 1 (neg)",    [[FIELD, "in_calendar_year", 1]]),
        ])
        matrix("5 days ago", TODAY - datetime.timedelta(days=5), [
            ("in_last [10, DAY]",           [[FIELD, "in_last", [10, "DAY"]]]),
            ("in_last [2, DAY] (neg)",      [[FIELD, "in_last", [2, "DAY"]]]),
            ("in_next [10, DAY] (neg)",     [[FIELD, "in_next", [10, "DAY"]]]),
            ("not_in_last [10, DAY]",       [[FIELD, "not_in_last", [10, "DAY"]]]),
            ("in_calendar_day -5",          [[FIELD, "in_calendar_day", -5]]),
            ("in_calendar_day 0 (neg)",     [[FIELD, "in_calendar_day", 0]]),
            # does HOUR mean anything on a field with no time part?
            ("in_last [1, HOUR]",           [[FIELD, "in_last", [1, "HOUR"]]]),
            ("in_last [200, HOUR]",         [[FIELD, "in_last", [200, "HOUR"]]]),
            ("in_last [-10, DAY]",          [[FIELD, "in_last", [-10, "DAY"]]]),
            ("in_calendar_month 0",         [[FIELD, "in_calendar_month", 0]]),
        ])
        matrix("in 5 days", TODAY + datetime.timedelta(days=5), [
            ("in_next [10, DAY]",           [[FIELD, "in_next", [10, "DAY"]]]),
            ("in_next [2, DAY] (neg)",      [[FIELD, "in_next", [2, "DAY"]]]),
            ("in_last [10, DAY] (neg)",     [[FIELD, "in_last", [10, "DAY"]]]),
            ("in_calendar_day 5",           [[FIELD, "in_calendar_day", 5]]),
        ])
        put(None)
        rows.append(f"\ncleared before deleting the throwaway shots: {readback()}")

actual = "\n".join(rows)
_lib.emit("field_types/date", actual, env)
