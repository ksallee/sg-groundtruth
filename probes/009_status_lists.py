"""Q: are status list values site-wide or project-scoped, and what does REST expose?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
BBB = 70


def statuses(entity, params=None):
    r = c.get(f"/schema/{entity}/fields/sg_status_list", params=params)
    return r.status_code, (r.json().get("data") if r.ok else r.text[:200])


projects = {p["id"]: p["attributes"]["name"]
            for p in c.get("/entity/projects", params={"fields": "name", "page[size]": 20}).json()["data"]}
_lib.register_names(*projects.values())

rows = []
scopes = [("site-wide", None)] + [(f"project {pid}", {"project_id": pid}) for pid in sorted(projects)]
for label, params in scopes:
    code, d = statuses("Version", params)
    if isinstance(d, dict):
        props = d.get("properties", {})
        vals = (props.get("valid_values") or {}).get("value")
        disp = (props.get("display_values") or {}).get("value")
        rows.append(f"{code} Version sg_status_list [{label}]\n"
                    f"      top-level keys: {sorted(d)}\n"
                    f"      property keys:  {sorted(props)}\n"
                    f"      valid_values:   {vals}\n"
                    f"      display_values: {json.dumps(disp)[:200]}\n"
                    f"      hidden_values:  {json.dumps((props.get('hidden_values') or {}).get('value'))}\n"
                    f"      default_value:  {json.dumps((props.get('default_value') or {}).get('value'))}\n"
                    f"      editable:       {json.dumps((d.get('editable') or {}).get('value'))}  "
                    f"mandatory: {json.dumps((d.get('mandatory') or {}).get('value'))}")
    else:
        rows.append(f"{code} [{label}]: {d}")

code, d = statuses("Task")
tv = ((d or {}).get("properties", {}).get("valid_values") or {}).get("value") if isinstance(d, dict) else d
rows.append(f"\n{code} Task sg_status_list valid_values: {tv}")

actual = "\n".join(rows)
_lib.record("009_status_lists", "GET /schema/<Type>/fields/sg_status_list ± project_id",
            "Status lists are project-scoped; REST cannot see or set some of it.",
            actual,
            "A project's usable statuses are valid_values MINUS hidden_values, read with project_id. "
            "valid_values is identical at every scope and is NOT the answer on its own; hidden_values is what "
            "varies (site-wide hides 0, one project hides 2, another hides 6). Status lists are also per "
            "entity type - Version and Task share no vocabulary. Always read display_values: raw codes like "
            "'pndvs' mean nothing to a user.",
            env, tags=("schema", "status", "list-field", "inspector"))
print(actual)
