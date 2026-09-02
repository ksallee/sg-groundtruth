"""Q: how does a `checkbox` field read, write, clear and filter?

Two findings already point at this type from opposite sides. Probe 007: a checkbox reads 100% filled in
a fill-rate scan because False is not null. Probe 020: a checkbox cannot be filtered `is_not None` at
all. Both hinge on one unsettled question — is a checkbox two-state or three-state at rest? — so this
settles it on a row nobody has ever touched, then on a row created seconds ago.

Read-only half runs ungated. Writes need --write and go only into the sandbox project.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
FIELDS = ["flagged", "sg_movie_has_slate", "sg_frames_have_slate", "client_approved"]
rows = []


def search(filt, entity="versions", size=500, fields=None):
    """Row count, or the whole errors[] object. Never a slice — the 400 is the teaching content."""
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": filt, "fields": fields or ["code"], "page": {"size": size}})
    if not r.ok:
        return None, json.dumps(r.json().get("errors"), indent=1)
    return len(r.json()["data"]), None


def summarize(body, entity="versions"):
    r = c.post(f"/entity/{entity}/_summarize", headers=ARR, json=body)
    return r


# --------------------------------------------------------------- schema
schema = c.get("/schema/Version/fields").json()["data"]
boxes = sorted(f for f, d in schema.items() if d["data_type"]["value"] == "checkbox")
rows.append(f"=== schema: Version checkbox fields ({len(boxes)} of {len(schema)})")
for f in boxes:
    d = schema[f]
    rows.append(f"  {f:<22} editable={d['editable']['value']!s:<5} "
                f"mandatory={d['mandatory']['value']!s:<5} {d['name']['value']!r}")
rows.append(f"  properties exposed for 'flagged': {sorted(schema['flagged'])}")
rows.append("  no default_value, no valid_values — the schema says nothing about a null state")

# --------------------------------------------------- operators, from the API
rows.append("\n=== the API enumerates its own operators (probe 017)")
_, err = search([PROJ, ["flagged", "definitely_not_an_operator", None]])
rows.append(err)

# ------------------------------------------------------------------- read
rows.append("\n=== read: value and JSON type, 100 newest rows on the sample project")
r = c.get("/entity/versions", params={"filter[project.Project.id]": PROJECT, "page[size]": 100,
                                      "fields": ",".join(FIELDS), "sort": "-created_at"})
newest = r.json()["data"]
for f in FIELDS:
    seen = {}
    for row in newest:
        v = row["attributes"].get(f)
        seen[f"{v!r} ({type(v).__name__})"] = seen.get(f"{v!r} ({type(v).__name__})", 0) + 1
    rows.append(f"  {f:<22} {', '.join(f'{k} x{n}' for k, n in sorted(seen.items()))}")

rows.append("\n=== read: the OLDEST rows on the site, never touched since creation")
r = c.get("/entity/versions", params={"page[size]": 20, "fields": ",".join(FIELDS),
                                      "sort": "created_at"})
old = r.json()["data"]
created = c.get("/entity/versions", params={"page[size]": 1, "fields": "created_at",
                                            "sort": "created_at"}).json()["data"]
rows.append(f"  oldest Version created {created[0]['attributes']['created_at'] if created else '?'}")
for f in FIELDS:
    vals = {repr(row["attributes"].get(f)) for row in old}
    rows.append(f"  {f:<22} distinct over {len(old)} oldest rows: {sorted(vals)}")

rows.append("\n=== read: same question on another entity type, site-wide (probe 018's checkboxes)")
r = c.get("/entity/projects", params={"page[size]": 200,
                                      "fields": "is_template,is_demo,archived"})
projs = r.json()["data"]
for f in ("is_template", "is_demo", "archived"):
    vals = {repr(p["attributes"].get(f)) for p in projs}
    rows.append(f"  Project.{f:<13} distinct over {len(projs)} projects: {sorted(vals)}")

rows.append("\n=== read: _summarize grouping shows every distinct value, empties under '' (probe 020)")
for f in ("flagged", "sg_movie_has_slate", "sg_version_type"):
    g = summarize({"filters": [PROJ], "summary_fields": [{"field": "id", "type": "count"}],
                   "grouping": [{"field": f, "type": "exact", "direction": "asc"}]})
    if g.ok:
        groups = [(str(x["group_name"]), x["summaries"]["id"]) for x in g.json()["data"]["groups"]]
        _lib.note_names(*[n for n, _ in groups])   # group names are real values
        rows.append(f"  {f:<22} {groups}")
    else:
        rows.append(f"  {f:<22} {g.status_code} {json.dumps(g.json().get('errors'))}")
rows.append("  (sg_version_type is a list field, shown as the control: a real '' group exists there)")

# ----------------------------------------------------------------- filter
rows.append("\n=== filter: what the operators do, with negative controls")
base, _ = search([PROJ])
rows.append(f"  baseline {base} Versions in the sample project")
counts = {}
for label, filt in [
    ("flagged is True",            ["flagged", "is", True]),
    ("flagged is False",           ["flagged", "is", False]),
    ("flagged is None",            ["flagged", "is", None]),
    ("flagged is_not True",        ["flagged", "is_not", True]),
    ("flagged is_not False",       ["flagged", "is_not", False]),
    ("flagged is 'true' (string)", ["flagged", "is", "true"]),
    ("flagged is 'false'",         ["flagged", "is", "false"]),
    ("flagged is '1'",             ["flagged", "is", "1"]),
    ("flagged is '0'",             ["flagged", "is", "0"]),
    ("flagged is 1 (int)",         ["flagged", "is", 1]),
    ("flagged in [True, False]",   ["flagged", "in", [True, False]]),
]:
    n, err = search([PROJ, filt])
    counts[label] = n
    rows.append(f"  {label:<28} -> {n if err is None else 'ERR'}")
    if err:
        rows.append(err)
rows.append(f"  is True + is False = {counts['flagged is True']} + {counts['flagged is False']} "
            f"= {(counts['flagged is True'] or 0) + (counts['flagged is False'] or 0)} "
            f"vs baseline {base} — the two states partition every row, nothing is left over")

rows.append("\n=== filter: the is_not None 400 in full (probe 020 saw it from _summarize)")
n, err = search([PROJ, ["flagged", "is_not", None]])
rows.append(f"  _search  flagged is_not None -> {n if err is None else 'ERR'}")
if err:
    rows.append(err)
s = summarize({"filters": [PROJ, ["flagged", "is_not", None]],
               "summary_fields": [{"field": "id", "type": "count"}]})
rows.append(f"  _summarize flagged is_not None -> {s.status_code}")
if not s.ok:
    rows.append(json.dumps(s.json().get("errors"), indent=1))

# ------------------------------------------------------------------ write
if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for create / update / clear)")
else:
    # A probe leaves no trace: every Version it makes is deleted on the way out.
    with _lib.Created(c) as made:
        SANDBOX = _lib.sandbox_id(c, env)
        rows.append("\n=== write: create a Version with NO checkbox field set, then read it back")
        STAMP = int(time.time())
        r = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                             "code": f"zzprobe_checkbox_{STAMP}"})
        rows.append(f"  POST /entity/versions (no checkbox in body) -> {r.status_code}")
        vid = made.add("versions", r.json()["data"]["id"]) if r.ok else None
        if vid:
            echoed = {f: r.json()["data"]["attributes"].get(f, "<absent>") for f in FIELDS}
            rows.append(f"  201 response echoes: {echoed}")
            back = c.get(f"/entity/versions/{vid}", params={"fields": ",".join(FIELDS)}) \
                    .json()["data"]["attributes"]
            rows.append(f"  read back:           {back}")
            rows.append("  -> a never-written checkbox is already False, not null")

            n, _ = search([["id", "is", vid], ["flagged", "is", False]])
            rows.append(f"  and the brand-new row already matches `flagged is False`: {n} row "
                        f"(`is None` cannot be asked at all — it 400s, above)")

            rows.append("\n=== write: what the field accepts on the way in")
            rows.append(f"  {'sent':<22}{'code':<6}read back")
            for label, val in [("True", True), ("False", False), ("None", None), ("'true'", "true"),
                               ("'false'", "false"), ("'1'", "1"), ("'0'", "0"), ("1", 1), ("0", 0),
                               ("'yes'", "yes"), ("''", ""), ("'checked'", "checked")]:
                u = c.request("PUT", f"/entity/versions/{vid}", json={"flagged": val},
                              headers={"Content-Type": "application/json"})
                if u.ok:
                    got = c.get(f"/entity/versions/{vid}", params={"fields": "flagged"}) \
                           .json()["data"]["attributes"]["flagged"]
                    rows.append(f"  {label:<22}{u.status_code:<6}{got!r} ({type(got).__name__})")
                else:
                    rows.append(f"  {label:<22}{u.status_code:<6}"
                                f"{json.dumps(u.json().get('errors'))}")

            rows.append("\n=== clear: can it get back to null once it is True?")
            c.request("PUT", f"/entity/versions/{vid}", json={"flagged": True},
                      headers={"Content-Type": "application/json"})
            for label, body in [("PUT {flagged: null}", {"flagged": None}),
                                ("PUT {flagged: false}", {"flagged": False}),
                                ("PUT {flagged: ''}", {"flagged": ""})]:
                u = c.request("PUT", f"/entity/versions/{vid}", json=body,
                              headers={"Content-Type": "application/json"})
                got = c.get(f"/entity/versions/{vid}", params={"fields": "flagged"}) \
                       .json()["data"]["attributes"]["flagged"]
                rows.append(f"  {label:<22} {u.status_code} -> {got!r} ({type(got).__name__})")
                c.request("PUT", f"/entity/versions/{vid}", json={"flagged": True},
                          headers={"Content-Type": "application/json"})

            rows.append("\n=== filter: every operator/value pair, on rows this probe owns")
            # Scoped by id, not by project: the sandbox is shared, so a project-wide count drifts.
            # Compare the returned ids, not just the counts: equal counts do not prove equal rows.
            mates = []
            for suffix in ("mate_a", "mate_b"):
                rr = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                                      "code": f"zzprobe_checkbox_{STAMP}_{suffix}"})
                mates.append(made.add("versions", rr.json()["data"]["id"]))
            c.request("PUT", f"/entity/versions/{vid}", json={"flagged": True},
                      headers={"Content-Type": "application/json"})
            MINE = ["id", "in", [vid] + mates]
            rows.append("  3 rows in scope: 1 ticked, 2 untouched")
            seen = {}
            for label, filt in [("is True", ["flagged", "is", True]),
                                ("is False", ["flagged", "is", False]),
                                ("is 'true'", ["flagged", "is", "true"]),
                                ("is 'false'", ["flagged", "is", "false"]),
                                ("is_not True", ["flagged", "is_not", True]),
                                ("is_not False", ["flagged", "is_not", False])]:
                rr = c.post("/entity/versions/_search", headers=ARR,
                            json={"filters": [MINE, filt], "fields": ["id"], "page": {"size": 500}})
                got = sorted(d["id"] for d in rr.json()["data"]) if rr.ok else [rr.status_code]
                seen[label] = got
                rows.append(f"  {label:<14} -> {len(got)} of 3   ids {got}")
            for a, b in [("is False", "is 'false'"), ("is True", "is 'true'"),
                         ("is False", "is_not True"), ("is True", "is_not False")]:
                rows.append(f"  {a} and {b} returned the same ids: {seen[a] == seen[b]}")

            rows.append("\n=== clear: does a checkbox survive being written on create?")
            r2 = c.post("/entity/versions", json={"project": {"type": "Project", "id": SANDBOX},
                                                  "code": f"zzprobe_checkbox_null_{STAMP}",
                                                  "flagged": None})
            echo = (r2.json()["data"]["attributes"].get("flagged", "<absent>") if r2.ok
                    else json.dumps(r2.json().get("errors")))
            rows.append(f"  POST with flagged=null -> {r2.status_code} {echo}")
            if r2.ok:
                made.add("versions", r2.json()["data"]["id"])
        else:
            rows.append(json.dumps(r.json().get("errors"), indent=1))

actual = "\n".join(rows)
_lib.emit("field_types/checkbox", actual, env)
