"""Q: are status list values site-wide or project-scoped, and what does REST expose?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()


def statuses(entity, params=None):
    r = c.get(f"/schema/{entity}/fields/sg_status_list", params=params)
    return r.status_code, (r.json().get("data") if r.ok else r.text[:200])


projects = {p["id"]: p["attributes"]["name"]
            for p in c.get("/entity/projects", params={"fields": "name", "page[size]": 20}).json()["data"]}
_lib.note_names(*projects.values())

rows = []
seen_valid = set()
scopes = [("site-wide", None)] + [(f"project {pid}", {"project_id": pid}) for pid in sorted(projects)]
for i, (label, params) in enumerate(scopes):
    code, d = statuses("Version", params)
    if not isinstance(d, dict):
        rows.append(f"{code} [{label}]: {d}")
        continue
    props = d.get("properties", {})
    vals = (props.get("valid_values") or {}).get("value")
    hidden = json.dumps((props.get("hidden_values") or {}).get("value"))
    seen_valid.add(json.dumps(vals))
    # Only the first two scopes get the full shape; after that hidden_values is the only thing that moves.
    if i < 2:
        rows.append(f"{code} Version sg_status_list [{label}]\n"
                    f"      top-level keys: {sorted(d)}\n"
                    f"      property keys:  {sorted(props)}\n"
                    f"      valid_values:   {vals}\n"
                    f"      display_values: {json.dumps((props.get('display_values') or {}).get('value'))}\n"
                    f"      hidden_values:  {hidden}\n"
                    f"      default_value:  {json.dumps((props.get('default_value') or {}).get('value'))}\n"
                    f"      editable:       {json.dumps((d.get('editable') or {}).get('value'))}  "
                    f"mandatory: {json.dumps((d.get('mandatory') or {}).get('value'))}")
    else:
        rows.append(f"{code} [{label}] hidden_values: {hidden}")

rows.append(f"\ndistinct valid_values across {len(scopes)} scopes: {len(seen_valid)}")

code, d = statuses("Task")
tv = ((d or {}).get("properties", {}).get("valid_values") or {}).get("value") if isinstance(d, dict) else d
rows.append(f"{code} Task sg_status_list valid_values: {tv}")

_lib.emit("009_status_lists", "\n".join(rows), env)
