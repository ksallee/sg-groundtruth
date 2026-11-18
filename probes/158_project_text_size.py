"""Q: a custom text field on Project holding a JSON document: is a long string stored byte for byte,
newlines included, and up to what size?

sg-onset keeps two settings lists as JSON in text fields on Project (sg-onset #110).
`field_types/text` measured 100,000 characters on `Version.sg_department` and both ends stripped.
This writes JSON to a custom text field on the sandbox Project and reads it back by `GET` and by
`_search`, comparing length and SHA-256:

- shapes first, about 2 KB each: compact (`JSON.stringify(x)`), pretty with `\\n`, with `\\r\\n`,
  with a literal tab, with a trailing newline and with a leading space; non-ASCII and escapes in each;
- then 100,000, 500,000 and 1,000,000 characters of pretty JSON, stopping at the first refusal;
- with the largest stored value in place, what a `GET` of the Project and of the project listing
  costs when it names no `fields`, since probe 157 found a new field is returned by default.

Writes behind `--write`: the field `sg_zzprobe_158_json` on Project, set on the sandbox Project, set
back to null and retired before exit.

    python probes/158_project_text_size.py --write
"""
import hashlib
import json
import time

import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 158 writes; run with --write")
SB = _lib.sandbox_id(c, env)
rows = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:2000]
    return json.dumps(j.get("errors", j))


def sha(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:12] if isinstance(s, str) else repr(s)


def doc(n_items):
    """A settings list shaped like sg-onset's: templates with names, kinds and free text."""
    return [{"id": f"zzprobe-158-{i:06d}", "name": f"Template {i} é 日本 🎬",
             "kinds": ["wide", "close", "insert"], "note": 'quote " backslash \\ slash / end',
             "order": i, "on": i % 2 == 0, "extra": None} for i in range(n_items)]


def exact(n):
    """Pretty JSON of exactly n characters: a document, then a pad key filled to length."""
    base = json.dumps({"items": doc(max(1, n // 400)), "pad": ""}, indent=2, ensure_ascii=False)
    while len(base) > n - 10:
        items = json.loads(base)["items"][:-1]
        base = json.dumps({"items": items, "pad": ""}, indent=2, ensure_ascii=False)
    return base.replace('"pad": ""', '"pad": "' + "x" * (n - len(base)) + '"')


def roundtrip(label, value, field):
    t = time.time()
    r = c.put(f"/entity/projects/{SB}", json={field: value})
    dt = time.time() - t
    if not r.ok:
        out(f"  {label}: PUT -> {r.status_code} in {dt:.1f} s {errs(r)}")
        return False
    g = c.get(f"/entity/projects/{SB}", params={"fields": field}).json()["data"]["attributes"][field]
    s = c.post("/entity/projects/_search", headers=ARR, json={
        "filters": [["id", "is", SB]], "fields": [field]}).json()["data"][0]["attributes"][field]
    echo = r.json()["data"]["attributes"].get(field)
    out(f"  {label}: PUT -> {r.status_code} in {dt:.1f} s; sent {len(value)} chars, "
        f"{len(value.encode('utf-8'))} bytes, sha {sha(value)}")
    out(f"    GET     {len(g) if isinstance(g, str) else g!r} chars, sha {sha(g)}, equal {g == value}")
    out(f"    _search equal {s == value}; PUT echo equal {echo == value}")
    if g != value and isinstance(g, str):
        i = next((k for k, (a, b) in enumerate(zip(g, value)) if a != b), min(len(g), len(value)))
        out(f"    first difference at {i}: sent {value[max(0, i - 5):i + 5]!r}, read {g[max(0, i - 5):i + 5]!r}")
    return True


field = None
try:
    # A rerun finds the name retired by the last run (probe 019) and revives it (probe 040), so the
    # probe spends one name however often it runs.
    r = c.post("/schema/Project/fields", json={"data_type": "text", "properties": [
        {"property_name": "name", "value": "zzprobe 158 json"}]})
    if r.status_code == 201:
        field = r.json()["links"]["self"].rsplit("/", 1)[-1]
        out(f"POST /schema/Project/fields text 'zzprobe 158 json' -> 201 {field}")
    else:
        rv = c.post("/schema/Project/fields/sg_zzprobe_158_json", json={"revive": True})
        out(f"POST /schema/Project/fields -> {r.status_code} {errs(r)}\n  revive sg_zzprobe_158_json -> {rv.status_code}")
        if not rv.ok:
            raise SystemExit(errs(r) + " " + errs(rv))
        field = "sg_zzprobe_158_json"

    small = doc(6)
    pretty = json.dumps(small, indent=2, ensure_ascii=False)
    out("\n===== shapes, about 2 KB each")
    for label, value in (
        ("compact, ensure_ascii", json.dumps(small, separators=(",", ":"))),
        ("compact, raw unicode", json.dumps(small, separators=(",", ":"), ensure_ascii=False)),
        ("pretty, \\n", pretty),
        ("pretty, \\r\\n", pretty.replace("\n", "\r\n")),
        ("pretty, a literal tab per line", pretty.replace("\n  ", "\n\t")),
        ("pretty + trailing \\n", pretty + "\n"),
        ("leading space + pretty", " " + pretty),
    ):
        roundtrip(label, value, field)

    out("\n===== size, pretty JSON with \\n, stopping at the first refusal")
    for n in (100_000, 500_000, 1_000_000):
        if not roundtrip(f"{n:,} chars", exact(n), field):
            break
    else:
        n = 1_000_000

    out("\n===== cost of a read that names no fields, with the largest value stored")
    for label, path, params in (
        ("GET /entity/projects/<sandbox>", f"/entity/projects/{SB}", None),
        ("GET /entity/projects/<sandbox>?fields=name", f"/entity/projects/{SB}", {"fields": "name"}),
        ("GET /entity/projects?page[size]=100", "/entity/projects", {"page[size]": 100}),
        ("GET /entity/projects?page[size]=100&fields=name", "/entity/projects",
         {"page[size]": 100, "fields": "name"}),
    ):
        t = time.time()
        r = c.get(path, params=params)
        d = r.json()["data"]
        first = d[0] if isinstance(d, list) else d
        out(f"  {label} -> {r.status_code}, {len(r.content):,} bytes in {time.time() - t:.2f} s; "
            f"{len(d) if isinstance(d, list) else 1} rows, {len(first['attributes'])} attributes and "
            f"{len(first['relationships'])} relationships on the first")
finally:
    if field:
        r = c.put(f"/entity/projects/{SB}", json={field: None})
        out(f"\n  PUT {field} null on the sandbox Project -> {r.status_code}")
        r = c.delete(f"/schema/Project/fields/{field}")
        out(f"  retired Project.{field} -> {r.status_code}")
    left = [k for k in c.get("/schema/Project/fields").json()["data"] if "zzprobe_158" in k]
    out(f"  zzprobe_158 fields live on Project at exit: {left}")
    _lib.emit("158_project_text_size", "\n".join(rows), env)
