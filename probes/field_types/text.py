"""Q: how does a `text` field read, write, clear and filter?

`text` is the type every other type gets compared against, so the matrix starts here. The read-only half
— schema, read shape, and the operator list the API enumerates for itself — runs without --write.

The one that bites: a client that cannot tell "unset" from "empty string" shows the wrong thing, so the
write half sets up four rows (a value, "", explicit null, field omitted) and runs every operator over them.
"""
import json
import sys
import time

sys.path.insert(0, __file__.rsplit("/", 2)[0])
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
FIELD = "sg_department"          # stock, editable, plain text
CANDIDATES = ("sg_department", "client_code", "description", "cached_display_name", "code")
rows = []


def err(r):
    """Whole errors[] object. Probe 017 lost the legal-operator list for months to a [:120] slice."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def search(project, filt, fields=("code", FIELD), size=200):
    r = c.post("/entity/versions/_search", headers=ARR,
               json={"filters": [["project", "is", {"type": "Project", "id": project}]] + filt,
                     "fields": list(fields), "page": {"size": size}})
    return r


rows.append("=== schema: which stock Version text fields are real, editable text")
schema = c.get("/schema/Version/fields").json()["data"]
rows.append(f"{'field':<22}{'data_type':<12}{'editable':<10}{'mandatory':<11}unique")
for f in CANDIDATES:
    d = schema[f]
    g = lambda k: (d.get(k) or {}).get("value")  # noqa: E731
    rows.append(f"{f:<22}{str(g('data_type')):<12}{str(g('editable')):<10}"
                f"{str(g('mandatory')):<11}{g('unique')}")

rows.append("\n=== the API enumerates its own operators: send one that cannot exist")
r = search(PROJECT, [[FIELD, "definitely_not_an_operator", None]])
rows.append(f"[[{FIELD!r}, 'definitely_not_an_operator', None]] -> {r.status_code}")
rows.append(err(r))

rows.append("\n=== read: where a text value lands, and its exact shape")
got = search(PROJECT, [], fields=("code", FIELD, "description", "cached_display_name"), size=100)
data = got.json()["data"]
_lib.note_from(data)
filled = [d for d in data if d["attributes"].get(FIELD)]
sample = (filled or data)[:1]
for d in sample:
    rows.append(f"  keys on the row: {sorted(d)}")
    rows.append(f"  attributes: {json.dumps(d['attributes'])}")
    rows.append(f"  relationships: {sorted(d.get('relationships', {}))}  <- text never lands here")
    rows.append(f"  python types: {[(k, type(v).__name__) for k, v in d['attributes'].items()]}")
empties = {"null": 0, "empty string": 0, "value": 0}
for d in data:
    v = d["attributes"].get(FIELD)
    empties["null" if v is None else ("empty string" if v == "" else "value")] += 1
rows.append(f"  over {len(data)} rows, {FIELD} is: {empties}")
same = sum(1 for d in data if d["attributes"].get("cached_display_name") == d["attributes"].get("code"))
rows.append(f"  cached_display_name == code on {same}/{len(data)} rows  <- it mirrors code, not free text")

if not _lib.writes_allowed():
    rows.append("\n(read-only run: write, clear and the filter matrix need --write)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    RUN = f"zzprobe_text_{int(time.time()) % 100000}"
    made = []

    def create(code, body=None):
        r = c.post("/entity/versions",
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": code, **(body or {})})
        if r.ok:
            made.append(r.json()["data"]["id"])
            return r.json()["data"]["id"], None
        return None, err(r)

    def put(vid, value):
        r = c.request("PUT", f"/entity/versions/{vid}", json={FIELD: value},
                      headers={"Content-Type": "application/json"})
        return r

    def read(vid, field=FIELD):
        a = c.get(f"/entity/versions/{vid}", params={"fields": field}).json()["data"]["attributes"]
        return a.get(field, "<key absent>")

    rows.append("\n=== write: what a text field accepts, and what it rejects")
    vid, e = create(f"{RUN}_scratch", {FIELD: "lighting"})
    rows.append(f"  create with {FIELD}='lighting' -> id={vid} {e or ''}")
    rows.append(f"  reads back {read(vid)!r} ({type(read(vid)).__name__})")
    rows.append(f"  {'input':<34}{'status':<8}reads back as")
    for label, val in [
        ("'  padded  '",           "  padded  "),
        ("'   ' (whitespace only)", "   "),
        ("'line1\\nline2'",        "line1\nline2"),
        ("'h\\u00e9llo \\u2728 \\u6f22\\u5b57'", "héllo ✨ 漢字"),
        ("'<b>&amp;</b> \"q\" \\'s\\''", "<b>&amp;</b> \"q\" 's'"),
        ("'x' * 5000",             "x" * 5000),
        ("'x' * 100000",           "x" * 100000),
        ("12345 (int)",            12345),
        ("True (bool)",            True),
        ("['a','b'] (list)",       ["a", "b"]),
        ("{'a': 1} (dict)",        {"a": 1}),
    ]:
        r = put(vid, val)
        back = read(vid)
        shown = (repr(back)[:40] + f"... len={len(back)}") if isinstance(back, str) and len(back) > 60 \
            else repr(back)
        rows.append(f"  {label:<34}{r.status_code:<8}{shown}")
        if not r.ok:
            rows.append("   " + err(r).replace("\n", "\n   "))

    rows.append("\n=== cached_display_name says editable:True in the schema — does a write stick?")
    cid, e = create(f"{RUN}_cdn", {"cached_display_name": "ZZZ_NOT_THE_CODE"})
    rows.append(f"  create code={RUN}_cdn with cached_display_name='ZZZ_NOT_THE_CODE' -> {e or 'ok'}")
    rows.append(f"  reads back {read(cid, 'cached_display_name')!r}  <- the code wins")
    r = c.request("PUT", f"/entity/versions/{cid}", json={"cached_display_name": "ZZZ_STILL_NOT"})
    rows.append(f"  PUT cached_display_name -> {r.status_code}, reads back "
                f"{read(cid, 'cached_display_name')!r}")
    r = c.request("PUT", f"/entity/versions/{cid}", json={"code": f"{RUN}_cdn_renamed"})
    rows.append(f"  PUT code -> {r.status_code}, cached_display_name now "
                f"{read(cid, 'cached_display_name')!r}  <- it tracks code")

    rows.append("\n=== clear: null vs empty string, on the same field")
    for label, val in [("null", None), ("empty string", "")]:
        put(vid, "lighting")
        r = put(vid, val)
        back = read(vid)
        rows.append(f"  PUT {label:<14} -> {r.status_code}  reads back {back!r}")
    # The field must hold a value first, or omission and a clear look identical.
    put(vid, "lighting")
    r = c.request("PUT", f"/entity/versions/{vid}", json={"description": "untouched"})
    rows.append(f"  PUT missing key over a set field ({FIELD}='lighting', body carries description only)"
                f" -> {r.status_code}  {FIELD} reads back {read(vid)!r}  <- omission is not a clear")

    rows.append("\n=== four rows that differ only in how the field was left")
    ROWS = [("value", {FIELD: "lighting"}), ("empty", {FIELD: ""}),
            ("null", {FIELD: None}), ("omitted", {})]
    ids = {}
    for label, body in ROWS:
        i, e = create(f"{RUN}_row_{label}", body)
        ids[i] = label
        rows.append(f"  {label:<9} created id={i} {e or ''} -> reads back {read(i)!r}")

    PRE = [["code", "starts_with", f"{RUN}_row"]]

    def which(filt):
        r = search(SANDBOX, PRE + filt)
        if not r.ok:
            return f"ERR {r.status_code} " + err(r).replace("\n", " ")[:400]
        return sorted(ids.get(d["id"], f"?{d['id']}") for d in r.json()["data"]) or "[]"

    rows.append("\n=== filter matrix: which of the four rows each filter returns")
    for label, filt in [
        ("is 'lighting'",              [[FIELD, "is", "lighting"]]),
        ("is 'LIGHTING'",              [[FIELD, "is", "LIGHTING"]]),
        ("is None",                    [[FIELD, "is", None]]),
        ("is ''",                      [[FIELD, "is", ""]]),
        ("is_not 'lighting'",          [[FIELD, "is_not", "lighting"]]),
        ("is_not None",                [[FIELD, "is_not", None]]),
        ("is_not ''",                  [[FIELD, "is_not", ""]]),
        ("contains 'ight'",            [[FIELD, "contains", "ight"]]),
        ("contains 'IGHT'",            [[FIELD, "contains", "IGHT"]]),
        ("contains ''",                [[FIELD, "contains", ""]]),
        ("not_contains 'ight'",        [[FIELD, "not_contains", "ight"]]),
        ("starts_with 'light'",        [[FIELD, "starts_with", "light"]]),
        ("ends_with 'ing'",            [[FIELD, "ends_with", "ing"]]),
        ("in ['lighting','comp']",     [[FIELD, "in", ["lighting", "comp"]]]),
        ("in 'lighting' (bare str)",   [[FIELD, "in", "lighting"]]),
        ("in ['']",                    [[FIELD, "in", [""]]]),
        ("in [None]",                  [[FIELD, "in", [None]]]),
        ("not_in ['lighting']",        [[FIELD, "not_in", ["lighting"]]]),
        ("NEG is 'ZZZNOPE'",           [[FIELD, "is", "ZZZNOPE"]]),
        ("NEG contains 'ZZZNOPE'",     [[FIELD, "contains", "ZZZNOPE"]]),
        ("NEG starts_with 'ZZZNOPE'",  [[FIELD, "starts_with", "ZZZNOPE"]]),
        ("NEG in ['ZZZNOPE']",         [[FIELD, "in", ["ZZZNOPE"]]]),
        ("no filter (baseline)",       []),
    ]:
        rows.append(f"  {label:<28}-> {which(filt)}")

    rows.append("\n=== a second text field, left untouched on all four rows")
    rows.append(f"  description is None    -> {which([['description', 'is', None]])}")
    rows.append(f"  description is ''      -> {which([['description', 'is', '']])}")

    rows.append("\n=== `in` with a bare string: one whole value, or one per character?")
    ch, e = create(f"{RUN}_row_char", {FIELD: "g"})
    ids[ch] = "char"
    rows.append(f"  fifth row holds {FIELD}='g', a single character of 'lighting' {e or ''}")
    rows.append(f"  is 'g'                     -> {which([[FIELD, 'is', 'g']])}")
    rows.append(f"  in ['lighting']            -> {which([[FIELD, 'in', ['lighting']]])}")
    rows.append(f"  in 'lighting' (bare str)   -> {which([[FIELD, 'in', 'lighting']])}"
                "   <- 'char' present means per character")

    rows.append("\n=== cleanup")
    gone = [c.request("DELETE", f"/entity/versions/{i}").status_code for i in made]
    rows.append(f"  DELETE {len(made)} probe Versions -> {sorted(set(gone))}")
    rows.append(f"  filter after delete -> {which([])}  <- retired rows drop out of _search")

report = "\n".join(str(x) for x in rows)
_lib.emit("field_types/text", report, env)
