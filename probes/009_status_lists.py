"""Q: are status list values site-wide or project-scoped, and what does REST expose?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
BBB = 70


def statuses(entity, params=None):
    r = c.get(f"/schema/{entity}/fields/sg_status_list", params=params)
    return r.status_code, (r.json().get("data") if r.ok else r.text[:200])


rows = []
for label, params in (("site-wide", None), (f"project_id={BBB}", {"project_id": BBB})):
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
            "Status lists are per entity type, not global - Version and Task share no vocabulary. "
            "valid_values, display_values, hidden_values and default_value are ALL readable over REST, so "
            "hidden values are visible even if not settable. On this site project_id changed nothing, which "
            "does not disprove project scoping - it means no per-project override exists here. Always read "
            "display_values: raw codes like 'pndvs' are meaningless to a user.",
            env, tags=("schema", "status", "list-field", "inspector"))
print(actual)
