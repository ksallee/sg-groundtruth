"""Q: how does a status_list field read, write, clear and filter — and is hidden_values enforced?

Probe 009 settled where a project's usable statuses live (valid_values minus hidden_values). It left the
mechanics open, and the one that decides whether a client can trust the UI's list: a status HIDDEN in a
project — can REST still write it?
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
READ = _lib.sample_projects(c, env)[0]
SANDBOX = _lib.sandbox_id(c, env)
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
rows = []


def whole_error(r):
    """The entire errors[] object, `source` included. Truncating it throws away the vocabulary the API
    hands you for free (probe 017)."""
    try:
        body = r.json()
    except ValueError:
        return r.text
    return json.dumps(body.get("errors", body), indent=1)


def schema(entity, field, pid=None):
    r = c.get(f"/schema/{entity}/fields/{field}", params={"project_id": pid} if pid else None)
    return r.status_code, (r.json().get("data") if r.ok else r.text)


def prop(d, k):
    return (d.get("properties", {}) .get(k) or {}).get("value")


def top(d, k):
    return (d.get(k) or {}).get("value")


def search(entity, filt, project, fields="code,sg_status_list", size=500):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": [["project", "is", {"type": "Project", "id": project}]] + filt,
                     "fields": fields.split(","), "page": {"size": size}})
    if not r.ok:
        return f"ERR {r.status_code}", r
    return len(r.json()["data"]), r


# ---------------------------------------------------------------- schema (read-only)
rows.append("=== stock status_list fields, site scope")
for ent, fld in [("Version", "sg_status_list"), ("Shot", "sg_status_list"),
                 ("Shot", "sg_latest_vendor_status")]:
    code, d = schema(ent, fld)
    if not isinstance(d, dict):
        rows.append(f"{code} {ent}.{fld}: {d[:160]}")
        continue
    rows.append(f"{code} {ent}.{fld}  data_type={top(d, 'data_type')!r} editable={top(d, 'editable')} "
                f"mandatory={top(d, 'mandatory')} default={prop(d, 'default_value')!r} "
                f"valid_values={len(prop(d, 'valid_values') or [])} "
                f"props={sorted(d.get('properties', {}))}")

code, site = schema("Version", "sg_status_list")
code, proj = schema("Version", "sg_status_list", SANDBOX)
VALID = prop(proj, "valid_values") or []
HIDDEN = prop(proj, "hidden_values") or []
DISPLAY = prop(proj, "display_values") or {}
USABLE = [v for v in VALID if v not in HIDDEN]
rows.append(f"\n=== Version.sg_status_list in the sandbox project")
rows.append(f"  valid_values  {VALID}")
rows.append(f"  hidden_values {HIDDEN}")
rows.append(f"  usable        {USABLE}")
rows.append(f"  site-wide hidden_values {prop(site, 'hidden_values')} (probe 009: only this key moves)")

hidden_code = HIDDEN[0] if HIDDEN else None
good = "fin" if "fin" in USABLE else (USABLE[0] if USABLE else None)
label = DISPLAY.get(good)

# ---------------------------------------------------------------- read shape (read-only)
rows.append("\n=== READ: what shape comes back")
n, r = search("versions", [], READ, fields="code,sg_status_list", size=200)
if isinstance(n, int) and n:
    data = r.json()["data"]
    row = next((x for x in data if x["attributes"].get("sg_status_list")), data[0])
    _lib.note_from(row)  # only the row printed; flagging 200 Version codes buries the list
    rows.append(f"  one row: {json.dumps({k: v for k, v in row.items() if k != 'links'})[:220]}")
    rows.append(f"  attributes keys {sorted(row['attributes'])}  relationships keys "
                f"{sorted(row.get('relationships', {}))}")
    seen = {}
    for x in data:
        v = x["attributes"].get("sg_status_list")
        seen[v] = seen.get(v, 0) + 1
    rows.append(f"  distinct values over {len(data)} versions: "
                f"{json.dumps(dict(sorted(seen.items(), key=lambda kv: -kv[1])))}")
    POP = max((k for k in seen if k), key=lambda k: seen[k], default=good)
    rows.append(f"  no display label inline: reading {POP!r} needs display_values -> {DISPLAY.get(POP)!r}")
    # a status code is not an entity link; does a dotted path through it read anything?
    rr = c.get(f"/entity/versions/{row['id']}",
               params={"fields": "sg_status_list,sg_status_list.Status.name,sg_status_list.Status.bg_color"})
    rows.append(f"  dotted sg_status_list.Status.name -> {rr.status_code} "
                f"{json.dumps(rr.json()['data']['attributes'])[:150]}")
else:
    POP = good
    rows.append(f"  no versions in the read project: {n}")

# ---------------------------------------------------------------- operators (read-only)
rows.append("\n=== FILTER: ask the API for its own operator list")
n, r = search("versions", [["sg_status_list", "definitely_not_an_operator", "x"]], READ)
rows.append(f"  sg_status_list definitely_not_an_operator -> {n}")
rows.append(whole_error(r))

plain = None
vfields = c.get("/schema/Version/fields").json()["data"]
for name, d in sorted(vfields.items()):
    if top(d, "data_type") == "list":
        plain = name
        break
if plain:
    n, r = search("versions", [[plain, "definitely_not_an_operator", "x"]], READ)
    rows.append(f"\n  same on plain list field Version.{plain} -> {n}")
    rows.append(whole_error(r))

# ---------------------------------------------------------------- filter values (read-only)
rows.append("\n=== FILTER: value format per operator (positive / negative control)")
base, _ = search("versions", [], READ)
rows.append(f"  baseline versions in project: {base}")
cases = [
    ("is <code>", [["sg_status_list", "is", POP]]),
    ("is <display label>", [["sg_status_list", "is", DISPLAY.get(POP)]]),
    ("is <code not in valid_values>", [["sg_status_list", "is", "zznope"]]),
    ("is null", [["sg_status_list", "is", None]]),
    ("is_not <code>", [["sg_status_list", "is_not", POP]]),
    ("in [2 codes]", [["sg_status_list", "in", [POP, good]]]),
    ("in [2 display labels]", [["sg_status_list", "in", [DISPLAY.get(POP), label]]]),
    ("in ['zznope']", [["sg_status_list", "in", ["zznope"]]]),
    ("not_in [2 codes]", [["sg_status_list", "not_in", [POP, good]]]),
    ("contains <code[:2]>", [["sg_status_list", "contains", (POP or "xx")[:2]]]),
    ("contains 'zznope'", [["sg_status_list", "contains", "zznope"]]),
    ("starts_with <code[0]>", [["sg_status_list", "starts_with", (POP or "x")[0]]]),
    ("ends_with <code[-1]>", [["sg_status_list", "ends_with", (POP or "x")[-1]]]),
    ("is <hidden code>", [["sg_status_list", "is", hidden_code]] if hidden_code else None),
]
for lbl, filt in cases:
    if filt is None:
        continue
    n, r = search("versions", filt, READ)
    flag = "  <- IGNORED, returns baseline" if n == base and "is_not" not in lbl and "not_in" not in lbl else ""
    rows.append(f"  {lbl:<32} {json.dumps(filt[0][2])[:40]:<26} -> {n}{flag}")
    if not isinstance(n, int):
        rows.append(whole_error(r))

# ---------------------------------------------------------------- write / clear (sandbox only)
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write/clear half)")
else:
    rows.append("\n=== WRITE / CLEAR, sandbox project only")
    made = []

    def create(body, tag):
        r = c.post("/entity/versions", headers=JSON,
                   json={"project": {"type": "Project", "id": SANDBOX}, **body})
        if r.ok:
            d = r.json()["data"]
            made.append(d["id"])
            return f"  {r.status_code} {tag:<44} -> sg_status_list={d['attributes'].get('sg_status_list')!r}"
        return f"  {r.status_code} {tag:<44} ->\n{whole_error(r)}"

    rows.append(create({"code": "zzprobe_status_list"}, "create, field omitted (does default apply?)"))
    vid = made[0]
    rows.append(create({"code": "zzprobe_status_list_hidden", "sg_status_list": hidden_code},
                       f"create with HIDDEN status {hidden_code!r}"))

    def put(value, tag):
        r = c.request("PUT", f"/entity/versions/{vid}", headers=JSON, json={"sg_status_list": value})
        back = c.get(f"/entity/versions/{vid}", params={"fields": "sg_status_list"})
        got = back.json()["data"]["attributes"].get("sg_status_list") if back.ok else "?"
        line = f"  {r.status_code} PUT {tag:<40} reads back {got!r}"
        return line if r.ok else line + "\n" + whole_error(r)

    rows.append(put(good, f"{good!r} (usable code)"))
    rows.append(put(hidden_code, f"{hidden_code!r} (HIDDEN in this project)"))
    rows.append(put(label, f"{label!r} (display label, not a code)"))
    rows.append(put("zznope", "'zznope' (not in valid_values)"))
    rows.append(put(None, "null"))
    rows.append(put(good, f"{good!r} (reset before the empty-string test)"))
    rows.append(put("", "'' (empty string)"))

    n, _ = search("versions", [["sg_status_list", "is", None]], SANDBOX)
    rows.append(f"  sandbox: filter sg_status_list is null after the clears -> {n}")

    for v in made:
        c.request("DELETE", f"/entity/versions/{v}")
    rows.append(f"  cleaned up {len(made)} sandbox Versions")

_lib.emit("field_types/status_list", "\n".join(rows), env)
