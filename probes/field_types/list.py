"""Q: how does a plain `list` field read, write, clear and filter, and is /schema valid_values authoritative?

Probed on stock editable fields — Version.sg_version_type, Shot.sg_shot_type, Version.viewed_by_current_user.
Never creates a schema field: a name is burned permanently (probe 019).

The crux is the third block. A filter editor that builds a dropdown from /schema is only correct if the API
refuses everything else; if an out-of-schema write is accepted, valid_values is a suggestion, not a contract.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
FIELD = "sg_version_type"
rows = []


def err(r):
    """Whole errors[] object, source included. Truncating it throws away the operator vocabulary."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def schema(entity, field, project=None):
    p = {"project_id": project} if project else None
    return c.get(f"/schema/{entity}/fields/{field}", params=p)


def props(entity, field, project=None):
    r = schema(entity, field, project)
    d = r.json()["data"]
    return {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items()}, d


def search(entity, filt, fields=None, size=500, project=True):
    body = {"filters": ([["project", "is", {"type": "Project", "id": PROJECT}]] if project else []) + filt,
            "fields": fields or ["code"], "page": {"size": size}}
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    return (len(r.json()["data"]), r.json()["data"]) if r.ok else (f"ERR {r.status_code}", err(r))


rows.append("=== schema shape: a list vs a status_list (probe 009)")
for entity, field in (("Version", FIELD), ("Shot", "sg_shot_type"),
                      ("Version", "viewed_by_current_user"), ("Version", "sg_status_list")):
    flat, raw = props(entity, field)
    pkeys = sorted(raw.get("properties", {}))
    rows.append(f"  {entity}.{field}")
    rows.append(f"    data_type={flat.get('data_type')} editable={flat.get('editable')} "
                f"mandatory={flat.get('mandatory')} unique={flat.get('unique')}")
    rows.append(f"    property keys: {pkeys}")
    p = {k: v.get("value") for k, v in raw.get("properties", {}).items()}
    rows.append(f"    valid_values={p.get('valid_values')} default_value={p.get('default_value')!r}")

rows.append("\n=== is a list project-scoped the way a status_list is?")
for entity, field in (("Version", FIELD), ("Version", "sg_status_list")):
    site, _ = props(entity, field)
    scoped, raw_s = props(entity, field, PROJECT)
    ps = {k: v.get("value") for k, v in raw_s.get("properties", {}).items()}
    rows.append(f"  {entity}.{field} project-scoped property keys: {sorted(raw_s.get('properties', {}))}")
    rows.append(f"    valid_values same as site-wide: "
                f"{ps.get('valid_values') == {k: v.get('value') for k, v in props(entity, field)[1]['properties'].items()}.get('valid_values')}"
                f"  hidden_values={ps.get('hidden_values')!r}")

rows.append("\n=== read: where does the value land, and what shape is it?")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                      "fields": f"code,{FIELD},viewed_by_current_user,sg_status_list",
                                      "page[size]": 3})
data = r.json()["data"]
_lib.note_from(data)
for d in data:
    rows.append(f"  attributes: {json.dumps(d['attributes'])}")
    rows.append(f"  relationships keys: {sorted(d.get('relationships', {}))}")
    break
seen = {}
page = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT,
                                         "fields": FIELD, "page[size]": 500}).json()["data"]
for d in page:
    v = d["attributes"].get(FIELD)
    seen[repr(v)] = seen.get(repr(v), 0) + 1
rows.append(f"  {len(page)} rows, distinct {FIELD} values in the data: {seen}")
rows.append(f"  python type of a non-null value: "
            f"{ {type(d['attributes'].get(FIELD)).__name__ for d in page if d['attributes'].get(FIELD) is not None} }")

rows.append("\n=== the API enumerates its own operators (probe 017)")
n, e = search("versions", [[FIELD, "definitely_not_an_operator", None]])
rows.append(f"  {FIELD} definitely_not_an_operator null -> {n}")
rows.append(e if isinstance(e, str) else "")

VALID = props("Version", FIELD)[1]["properties"]["valid_values"]["value"]
GOOD, OTHER = VALID[0], VALID[1]
BOGUS = "zzprobe_list_not_a_valid_value"
base, _ = search("versions", [])
rows.append(f"\n=== filter value formats  (baseline {base} versions in project)")
rows.append(f"  valid_values = {VALID};  good={GOOD!r}  other={OTHER!r}  bogus={BOGUS!r}")
for label, filt in [
    (f"is {GOOD!r}",                 [[FIELD, "is", GOOD]]),
    (f"is {BOGUS!r} (neg control)",  [[FIELD, "is", BOGUS]]),
    (f"is {GOOD.lower()!r} (case)",  [[FIELD, "is", GOOD.lower()]]),
    ("is null",                      [[FIELD, "is", None]]),
    (f"is_not {GOOD!r}",             [[FIELD, "is_not", GOOD]]),
    ("is_not null",                  [[FIELD, "is_not", None]]),
    (f"in [{GOOD!r}, {OTHER!r}]",    [[FIELD, "in", [GOOD, OTHER]]]),
    (f"in [{GOOD!r}] (one real, alone)", [[FIELD, "in", [GOOD]]]),
    (f"in [{BOGUS!r}] (neg control)", [[FIELD, "in", [BOGUS]]]),
    (f"in [{GOOD!r}, {BOGUS!r}] (one real, one junk)", [[FIELD, "in", [GOOD, BOGUS]]]),
    (f"in {GOOD!r} (bare, not a list)", [[FIELD, "in", GOOD]]),
    (f"not_in [{GOOD!r}]",           [[FIELD, "not_in", [GOOD]]]),
    (f"contains {GOOD[2:5]!r}",      [[FIELD, "contains", GOOD[2:5]]]),
    ("contains 'ZZZNOPE' (neg control)", [[FIELD, "contains", "ZZZNOPE"]]),
    (f"not_contains {GOOD[2:5]!r}",  [[FIELD, "not_contains", GOOD[2:5]]]),
    (f"starts_with {GOOD[:2]!r}",    [[FIELD, "starts_with", GOOD[:2]]]),
    (f"ends_with {GOOD[-2:]!r}",     [[FIELD, "ends_with", GOOD[-2:]]]),
]:
    n, e = search("versions", filt)
    flag = "  <- IGNORED, returns baseline" if isinstance(n, int) and n == base else ""
    rows.append(f"  {label:<40} -> {n}{flag}")
    if isinstance(n, str):
        rows.append(f"      {e}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the write / clear half)")
else:
    # A probe leaves no trace: every Version it makes is deleted on the way out.
    with _lib.Created(c) as made:
        SANDBOX = _lib.sandbox_id(c, env)
        rows.append(f"\n=== write, into the sandbox project only  (valid_values before: {VALID})")
        r = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                             "code": "zzprobe_list"})
        vid = made.add("versions", r.json()["data"]["id"]) if r.ok else None
        fresh = c.get(f"/entity/versions/{vid}", params={"fields": FIELD}).json()["data"]["attributes"]
        rows.append(f"  create Version zzprobe_list, field omitted -> {r.status_code} id={vid} "
                    f"reads {json.dumps(fresh)}  (default_value={VALID[0]!r} applied? "
                    f"{fresh.get(FIELD) is not None})")
        rb = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                              "code": "zzprobe_list_bogus", FIELD: BOGUS})
        rows.append(f"  create with an out-of-schema value -> {rb.status_code} "
                    f"{err(rb) if not rb.ok else 'ACCEPTED id=' + str(rb.json()['data']['id'])}")
        if rb.ok:
            made.add("versions", rb.json()["data"]["id"])

        def put(value, field=FIELD):
            rr = c.request("PUT", f"/entity/versions/{vid}", json={field: value},
                           headers={"Content-Type": "application/json"})
            if not rr.ok:
                return rr.status_code, err(rr)
            back = c.get(f"/entity/versions/{vid}", params={"fields": field}).json()["data"]["attributes"]
            return rr.status_code, f"read back {json.dumps(back)}"

        for label, value in [
            (f"valid value {GOOD!r}",           GOOD),
            (f"different casing {GOOD.lower()!r}", GOOD.lower()),
            (f"upper {GOOD.upper()!r}",         GOOD.upper()),
            (f"trailing space {GOOD + ' '!r}",  GOOD + " "),
            (f"a status_list code 'apr'",       "apr"),
            (f"out of valid_values {BOGUS!r}",  BOGUS),
            (f"a LIST of two valid values",     [GOOD, OTHER]),
            ("an integer index 0",              0),
        ]:
            code, info = put(value)
            rows.append(f"  {label:<38} -> {code} {info}")
            after = props("Version", FIELD)[1]["properties"]["valid_values"]["value"]
            if after != VALID:
                rows.append(f"      !! valid_values WIDENED to {after}")

        rows.append("\n=== is /schema valid_values authoritative after all that?")
        after = props("Version", FIELD)[1]["properties"]["valid_values"]["value"]
        rows.append(f"  valid_values now: {after}")
        rows.append(f"  unchanged: {after == VALID}")

        rows.append("\n=== clear: null vs empty string  (the row is matched by id, so 1 = matched, 0 = not)")
        for label, value in [(f"set {GOOD!r} (control)", GOOD), ("null", None), ('empty string ""', "")]:
            code, info = put(value)
            n, _e = search("versions", [["id", "is", vid], [FIELD, "is", None]], project=False)
            n2, _e2 = search("versions", [["id", "is", vid], [FIELD, "is", ""]], project=False)
            rows.append(f"  {label:<22} -> {code} {info}")
            rows.append(f"      matched by  is None -> {n}   is '' -> {n2}")

        rows.append("\n=== viewed_by_current_user: flagged editable, but is it? (probe 007)")
        code, info = put("read", "viewed_by_current_user")
        rows.append(f"  write 'read' -> {code} {info}")

        rows.append(f"\nvalid_values at the end of the run: {after}")

actual = "\n".join(rows)
_lib.emit("field_types/list", actual, env)
