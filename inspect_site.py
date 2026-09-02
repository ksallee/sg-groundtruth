"""Inspect one project and write the site profile the node consumes.

Named inspect_site.py, not inspect.py: a top-level inspect.py shadows the stdlib module of that name
for everything imported after it, and requests is in that blast radius.

TWO PASSES, for a measured reason (probe 020). Fill rate alone is misleading — on the reference
project 13 of the 18 fields reading ~100% are system fields or checkboxes full because False is not
null, while image and sg_uploaded_movie, the fields the node actually writes, sit at 1%.

  1. broad     one paged fetch of recent Versions, count non-null per field (probe 007). Cheap.
  2. shortlist _summarize grouping per candidate, for cardinality (probe 020). ~300ms each, and up
               to 1.5s on an entity field, so it runs over ten candidates and never over all 71.

Nothing here decides alone. It proposes, with the evidence beside it; the operator confirms.

    python inspect_site.py                                    list projects
    python inspect_site.py --project 70                       inspect, print, write ./profile.local.json
    python inspect_site.py --project 70 --out ../comfyui-fpt/profile.local.json
"""
import argparse
import json
import re
import sys
import time
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from sg_groundtruth.client import FPT                      # noqa: E402
from sg_groundtruth.env import load as load_env            # noqa: E402
from sg_groundtruth.schema import Schema, val              # noqa: E402
from sg_groundtruth import naming                          # noqa: E402

# probe 004 — _search and _summarize reject application/json with 415 and demand a vendor type.
ARRAY_JSON = {"Content-Type": "application/vnd+shotgun.api3_array+json"}

# probe 007 — a checkbox reads 100% filled because False is not null, so it can never be ranked by
# fill. probe 020 — it cannot be filtered `is_not None` either, which is the same trap from the
# other side. Everything else here is a container the operator does not choose a value for.
UNRANKABLE = {"checkbox", "image", "url", "serializable", "summary", "pivot_column", "uuid"}

SHORTLIST = 10
LINK_CANDIDATES = ("entity", "sg_task")
# A Version hangs off work, never off a person: `user` is filled 100% on the reference project and
# would otherwise outrank `entity` on a tie.
PEOPLE = {"HumanUser", "ApiUser", "Group", "Department"}


def projects(fpt):
    """(id, name) for projects worth publishing into.

    probe 018 — do NOT filter on sg_status: it is null on most real projects, so 'Active' hides
    working shows. The checkboxes are the reliable discriminators.
    """
    r = fpt.post("/entity/projects/_search", headers=ARRAY_JSON,
                 json={"filters": [["is_template", "is", False], ["archived", "is", False]],
                       "fields": ["name"], "page": {"size": 500}})
    r.raise_for_status()
    return sorted((d["id"], d["attributes"].get("name") or "") for d in r.json()["data"])


def recent(fpt, project_id, names, n):
    """The broad pass: one fetch, every field, most recent first (probe 007)."""
    r = fpt.get("/entity/versions", params={"filter[project.Project.id]": project_id,
                                            "fields": ",".join(names), "sort": "-id",
                                            "page[size]": n})
    r.raise_for_status()
    return r.json()["data"]


def value_of(row, field):
    """A field's value wherever it landed. probe 004 — entity and multi-entity fields always arrive
    under relationships as {data, links}, never under attributes."""
    if field in ("id", "type"):
        return row.get(field)
    v = row.get("attributes", {}).get(field)
    if v in (None, "", [], {}):
        v = (row.get("relationships", {}).get(field) or {}).get("data")
    return None if v in (None, "", [], {}) else v


def cardinality(fpt, project_id, field):
    """(distinct groups, rows in the empty group, ms) for one field, or None if it cannot be grouped.

    probe 020 — one _summarize with `grouping` gives both numbers at once, and empty values come back
    as a '' group. That is what fill rate cannot say: one group is no information at all, one group
    per row is an identifier.
    """
    t = time.time()
    r = fpt.post("/entity/versions/_summarize", headers=ARRAY_JSON,
                 json={"filters": [["project", "is", {"type": "Project", "id": project_id}]],
                       "summary_fields": [{"field": "id", "type": "count"}],
                       "grouping": [{"field": field, "type": "exact", "direction": "asc"}]})
    ms = round((time.time() - t) * 1000)
    if not r.ok:
        return None
    groups = r.json()["data"]["groups"]
    empty = sum(g["summaries"]["id"] for g in groups if str(g["group_name"]).strip() == "")
    return len(groups), empty, ms


def propose_code(codes):
    """A default Version name shaped like this project's, not like ours.

    The modal first segment, not the common prefix: one oddly named Version collapses a common
    prefix to nothing, and a project always has one.
    """
    seen = Counter(m.group(0) for m in (re.match(r"[^_\-.]+[_\-.]", c) for c in codes) if m)
    prefix, n = seen.most_common(1)[0] if seen else ("", 0)
    return f"{prefix}v001" if prefix and n * 2 >= len(codes) else "comfy_v001"


def inspect(fpt, project_id, n=100, shortlist=SHORTLIST):
    """Everything the profile is inferred from, plus the evidence for each inference."""
    sc = Schema(fpt, project_id)
    schema = sc.fields("Version")
    names = sorted(schema)
    rows = recent(fpt, project_id, names, n)
    filled = Counter()
    for row in rows:
        filled.update(f for f in names if value_of(row, f) is not None)

    # probe 005 — which field a Version actually hangs off, and what it points at. Never assumed:
    # on the reference project `entity` is filled 100% and sg_task 1%, and another site inverts that.
    links = {}
    for f in LINK_CANDIDATES + tuple(f for f in names
                                     if val(schema[f].get("data_type", {})) in ("entity", "multi_entity")):
        if f in links or f in ("project", "created_by", "updated_by"):
            continue
        types = Counter()
        for row in rows:
            v = value_of(row, f)
            for item in (v if isinstance(v, list) else [v]):
                if isinstance(item, dict) and item.get("type"):
                    types[item["type"]] += 1
        if types and not set(types) <= PEOPLE:
            links[f] = types

    status_field = schema.get("sg_status_list", {})
    usable = sc.statuses("Version")
    observed = Counter(v for v in (value_of(r, "sg_status_list") for r in rows) if v)
    codes = [c for c in (value_of(r, "code") for r in rows) if isinstance(c, str)]

    candidates = [f for f, _ in filled.most_common()
                  if val(schema[f].get("editable", {}), False)
                  and val(schema[f].get("data_type", {})) not in UNRANKABLE][:shortlist]
    ranked = []
    for f in candidates:
        card = cardinality(fpt, project_id, f)
        ranked.append((f, val(schema[f].get("data_type", {})), filled[f], card))

    # probe 008 — a slot number is site-specific and means nothing to an operator; the display name
    # is in /schema and is the only thing worth showing them.
    display = {t: val(v.get("name", {}), t) for t, v in sc.entity_types().items()}

    # The version number has no field of its own by default, so it lives in `code` as a convention.
    # Inferred and reported with its coverage — 0% is an honest answer and the operator must see it.
    # Task names come along because the middle token of a code cannot otherwise be told apart: `comp`
    # is a pipeline step, `depth` is a render pass, and only the site knows which it uses.
    tr = fpt.post("/entity/tasks/_search", headers=ARRAY_JSON,
                  json={"filters": [["project", "is", {"type": "Project", "id": project_id}]],
                        "fields": ["content"], "page": {"size": 200}})
    task_names = sorted({d["attributes"].get("content") for d in tr.json().get("data", [])
                         if tr.ok and d["attributes"].get("content")})
    template, regex, matched, total = naming.infer(codes, task_names)
    # How much evidence there is for the middle token being a pipeline step rather than a render pass.
    lowered = {t.lower() for t in task_names}
    mids = [m.group("output") for m in (re.match(regex, c) for c in codes)
            if m and "output" in (m.groupdict() or {})] if regex else []
    task_hits = sum(1 for t in mids if t.lower() in lowered)
    vfields = naming.version_field_candidates(schema)

    return {
        "template": template, "regex": regex, "matched": matched, "coverage_of": total,
        "task_names": task_names, "mids": mids, "task_hits": task_hits,
        "version_fields": vfields,
        "rows": len(rows), "fields": len(names), "schema": schema, "filled": filled,
        "display": display,
        "links": links, "usable": usable, "observed": observed, "codes": codes, "ranked": ranked,
        "status_default": val(status_field.get("properties", {}).get("default_value", {})),
        "dead": [f for f in names if not filled[f]],
    }


def infer(found):
    """The profile keys the node reads, each from one measured signal."""
    link_field, link_type = "entity", "Shot"
    if found["links"]:
        link_field = max(found["links"],
                         key=lambda f: (sum(found["links"][f].values()), f in LINK_CANDIDATES))
        link_type = found["links"][link_field].most_common(1)[0][0]

    codes = [c for _, c in found["usable"]]
    status = found["status_default"] if found["status_default"] in codes else ""
    if not status and found["observed"]:
        status = next((c for c, _ in found["observed"].most_common() if c in codes), "")
    out = {"link_field": link_field, "link_type": link_type, "status": status,
           "code_prefix": propose_code(found["codes"])}
    if found["template"]:
        out["code_template"] = found["template"]
        out["code_regex"] = found["regex"]
    return out


def report(project_id, name, found, inferred):
    out = [f"project {project_id}  {name}", f"sample: {found['rows']} most recent Versions, "
           f"{found['fields']} fields in schema", ""]

    out.append("link — what a Version hangs off here                         (probe 005)")
    for f, types in sorted(found["links"].items(), key=lambda kv: -sum(kv[1].values())):
        mark = "  <- chosen" if f == inferred["link_field"] else ""
        spread = ", ".join(f"{found['display'].get(t, t)}"
                           + (f" ({t})" if found["display"].get(t, t) != t else "")
                           + f" {c}" for t, c in types.most_common())
        out.append(f"  {f:<26} {sum(types.values()):>3}/{found['rows']}   {spread}{mark}")
    if not found["links"]:
        out.append(f"  nothing links anywhere — defaulting to {inferred['link_field']}/"
                   f"{inferred['link_type']}, which is a guess, not a finding")

    out += ["", "status — usable in this project                              (probe 009)"]
    hidden = val(found["schema"].get("sg_status_list", {}).get("properties", {})
                 .get("hidden_values", {}), []) or []
    out.append(f"  {len(found['usable'])} usable, {len(hidden)} hidden by this project; "
               f"default {found['status_default']!r}")
    if found["observed"]:
        out.append("  observed: " + ", ".join(f"{c} {n}" for c, n in found["observed"].most_common(6)))

    out += ["", "code — how Versions are named here"]
    out.append("  " + ", ".join(found["codes"][:4]) if found["codes"] else "  no Versions yet")
    out.append(f"  proposed default: {inferred['code_prefix']}")
    if found["template"]:
        pct = 100 * found["matched"] // max(found["coverage_of"], 1)
        verdict = ("trust it" if pct >= 80 else
                   "check it — a large minority do not match" if pct >= 40 else
                   "DO NOT trust it; this project has no convention to learn from")
        out.append(f"  convention:       {found['template']}")
        if found["matched"] and found["mids"]:
            sample = ", ".join(sorted(set(found["mids"]))[:4])
            out.append(f"  the middle token ({sample}) is recorded as {{output}}, a render pass. "
                       f"{found['task_hits']}/{len(found['mids'])} of them")
            out.append(f"  match a Task name on this project — if it is a pipeline step and not a "
                       f"pass, change it to {{task}}.")
        elif "{task}" in found["template"] and found["matched"]:
            out.append(f"  the middle token matches this project's Task names, so it reads as a "
                       f"pipeline step")
        out.append(f"  coverage:         {found['matched']}/{found['coverage_of']} ({pct}%) — {verdict}")
        out.append(f"  a graph with several image outputs needs {{output}} in the template, or every")
        out.append(f"  pass collapses onto one name.")
    if found["version_fields"]:
        out.append(f"  a real version-number field may exist: {', '.join(found['version_fields'])}")
        out.append(f"  set version_number_field yourself if one of those is it — guessing wrong would")
        out.append(f"  silently misnumber every publish.")

    out += ["", "fields — filled, then distinct                        (probes 007, 020)",
            f"  {'field':<36}{'type':<14}{'filled':>8}{'distinct':>10}  verdict"]
    for f, dt, ct, card in found["ranked"]:
        if card is None:
            verdict, real = "cannot be grouped", "-"
        else:
            distinct, empty, _ = card
            real = distinct - (1 if empty else 0)   # the '' group is absence, not a value (probe 020)
            verdict = ("identifier — one value per row, nothing to choose from" if real >= ct > 1
                       else "no information — one value" if real <= 1
                       else f"{real} values" + (f", {empty} empty" if empty else ""))
        out.append(f"  {f[:35]:<36}{dt:<14}{ct:>4}/{found['rows']}{str(real):>10}  {verdict}")
    out.append(f"\n  {len(found['dead'])} fields never populated: "
               + ", ".join(found["dead"][:12]) + (" ..." if len(found["dead"]) > 12 else ""))
    return "\n".join(out)


def write_profile(path, project_id, name, inferred, overwrite):
    """Merge one project's findings into the profile.

    Keyed per project, because one studio runs shows with different conventions (DESIGN: site
    profile) — inspecting a second show adds a block, it does not replace the first. Top-level keys
    stay untouched as the site-wide default.

    Operator edits win over inference, so a re-run keeps what is already there and reports where it
    disagreed rather than quietly replacing it.
    """
    doc = json.loads(path.read_text()) if path.is_file() else {}
    doc.setdefault("default_project", project_id)
    blocks = doc.setdefault("projects", {})
    existing = blocks.get(str(project_id), {})
    out = dict(name=name, **inferred)
    if not overwrite:
        out.update(existing)
    blocks[str(project_id)] = out
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n")
    kept = [] if overwrite else [k for k, v in out.items() if existing.get(k, v) != inferred.get(k, v)]
    return doc, out, kept


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--project", type=int, help="project to inspect; omit to list projects")
    ap.add_argument("--out", type=Path, default=Path("profile.local.json"))
    ap.add_argument("--versions", type=int, default=100, help="broad-pass sample size")
    ap.add_argument("--shortlist", type=int, default=SHORTLIST, help="fields to cost a _summarize on")
    ap.add_argument("--overwrite", action="store_true", help="discard existing profile values")
    args = ap.parse_args(argv)

    fpt = FPT.from_env(load_env())
    if not args.project:
        for pid, name in projects(fpt):
            print(f"  {pid:>6}  {name}")
        return 0

    name = dict((i, n) for i, n in projects(fpt)).get(args.project, "")
    found = inspect(fpt, args.project, args.versions, args.shortlist)
    inferred = infer(found)
    print(report(args.project, name, found, inferred))

    doc, block, kept = write_profile(args.out, args.project, name, inferred, args.overwrite)
    print(f"\nwrote {args.out}  ->  projects.{args.project}")
    for k, v in block.items():
        print(f"  {k:<14} {json.dumps(v)}" + ("   (yours, kept)" if k in kept else ""))
    others = [k for k in doc["projects"] if k != str(args.project)]
    if others:
        print(f"  untouched: projects {', '.join(others)}")
    if kept:
        print("  --overwrite replaces these with the inferred values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
