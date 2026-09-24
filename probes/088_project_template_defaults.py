"""Q: can a script read which task template a project uses for each entity type?

A sync app that applies "the project's template" to new Shots needs the per-entity-type default the
web app's project settings offer. Candidates: `Project.task_templates`, the `ProjectTaskTemplateConnection`
join, `TaskTemplate.projects`, every key of `Project.tracking_settings`, and any Project field or
`/preferences` key whose name mentions a template.

Read-only, site-wide over every project the script can see, plus the sample projects.
"""
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
import _tasktpl as T  # noqa: E402

env = _lib.load_env()
c = _lib.client()
rows = []
SAMPLE = _lib.sample_projects(c, env)


def keys(o, prefix=""):
    """Every key path in a decoded blob, lists collapsed to []."""
    if isinstance(o, dict):
        for k, v in o.items():
            yield from keys(v, f"{prefix}.{k}" if prefix else k)
    elif isinstance(o, list):
        yield f"{prefix}[]"
        for v in o[:1]:
            yield from keys(v, f"{prefix}[]")
    else:
        yield prefix


rows.append("=== Project fields that could hold a default")
pf = c.get("/schema/Project/fields").json()["data"]
for n, d in sorted(pf.items()):
    if any(w in n for w in ("template", "default", "tracking", "setting")):
        rows.append(f"  {n:<24} {d['data_type']['value']:<14} editable={d['editable']['value']} "
                    f"valid_types={(d.get('properties', {}).get('valid_types') or {}).get('value')}")

rows.append("\n=== every project the script can see")
projs = T.search(c, "projects", [], ["name", "task_templates", "tracking_settings", "is_template"])
_lib.note_from(projs)
with_tt = [p for p in projs if T.rel(p, "task_templates")]
rows.append(f"  {len(projs)} projects; task_templates non-empty on {len(with_tt)}")
for p in with_tt[:3]:
    rows.append(f"    project {p['id']} is_template={p['attributes']['is_template']} "
                f"task_templates={json.dumps(T.rel(p, 'task_templates'))}")
paths = Counter()
for p in projs:
    paths.update(set(keys(p["attributes"].get("tracking_settings") or {})))
rows.append(f"  tracking_settings null on {sum(1 for p in projs if not p['attributes'].get('tracking_settings'))}")
rows.append(f"  default_task_template key present on "
            f"{sum(1 for p in projs if 'default_task_template' in (p['attributes'].get('tracking_settings') or {}))}"
            f", non-empty on {sum(1 for p in projs if (p['attributes'].get('tracking_settings') or {}).get('default_task_template'))}")
rows.append("  tracking_settings key paths (leaves), projects holding each:")
for k, n in sorted(paths.items()):
    rows.append(f"    {k:<48} {n}")
for p in projs:
    ts = p["attributes"].get("tracking_settings") or {}
    if set(ts) - {"navchains"}:
        rows.append(f"  project {p['id']} beyond navchains: "
                    f"{json.dumps({k: v for k, v in ts.items() if k != 'navchains'})}")
        for et, d in (ts.get("default_task_template") or {}).items():
            listed = d.get("id") in [t["id"] for t in (T.rel(p, "task_templates") or [])]
            r = c.get(f"/entity/task_templates/{d.get('id')}", params={"fields": "entity_type"})
            rows.append(f"    default for {et}: template {d.get('id')} GET -> {r.status_code}, "
                        f"in this project's task_templates: {listed}")
for i in SAMPLE:
    p = next((x for x in projs if x["id"] == i), None)
    if p:
        rows.append(f"  sample project tracking_settings: {json.dumps(p['attributes']['tracking_settings'])[:400]}")

rows.append("\n=== ProjectTaskTemplateConnection")
sch = c.get("/schema/ProjectTaskTemplateConnection/fields")
if sch.ok:
    for n, d in sorted(sch.json()["data"].items()):
        rows.append(f"  {n:<24} {d['data_type']['value']:<14} editable={d['editable']['value']}")
for slug in ("project_task_template_connections", "ProjectTaskTemplateConnection"):
    r = c.post(f"/entity/{slug}/_search", headers=T.ARR,
               json={"filters": [], "fields": ["project", "task_template"], "page": {"size": 500}})
    rows.append(f"  _search /entity/{slug} -> {r.status_code} "
                + (f"{len(r.json()['data'])} rows {json.dumps(r.json()['data'][:2])[:300]}" if r.ok else T.errs(r)))

rows.append("\n=== TaskTemplate.projects, the other side")
tts = T.search(c, "task_templates", [], ["code", "entity_type", "projects"])
_lib.note_from(tts)
for t in tts:
    if T.rel(t, "projects"):
        rows.append(f"  template {t['id']} entity_type={t['attributes']['entity_type']} "
                    f"projects={[x['id'] for x in T.rel(t, 'projects')]}")
back = {(p["id"], t["id"]) for p in projs for t in (T.rel(p, "task_templates") or [])}
fwd = {(x["id"], t["id"]) for t in tts for x in (T.rel(t, "projects") or [])}
rows.append(f"  pairs from Project.task_templates {len(back)}, from TaskTemplate.projects {len(fwd)}, "
            f"equal: {back == fwd}")
per = Counter((pid, next(t['attributes']['entity_type'] for t in tts if t['id'] == tid)) for pid, tid in fwd)
rows.append(f"  (project, entity_type) pairs holding more than one template: {[k for k, n in per.items() if n > 1]}")

rows.append("\n=== site preferences")
r = c.get("/preferences")
prefs = r.json().get("data", {}) if r.ok else {}
hits = {k: v for k, v in prefs.items() if "template" in k.lower() or "task" in k.lower()}
rows.append(f"  GET /preferences -> {r.status_code}, {len(prefs)} keys; mentioning template or task: "
            f"{json.dumps(hits)[:400]}")

_lib.emit("088_project_template_defaults", "\n".join(rows), env)
