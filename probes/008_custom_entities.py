"""Q: which CustomEntityNN are enabled on this site, and how do I get their real names?"""
import _lib

env = _lib.load_env()
c = _lib.client()

schema = c.get("/schema").json()["data"]
_lib.note_from(schema)
custom = {k: v for k, v in schema.items() if k.startswith("CustomEntity") or k.startswith("CustomNonProject")}
visible = {k: v for k, v in custom.items() if (v.get("visible") or {}).get("value")}

lines = [f"total entity types in /schema: {len(schema)}",
         f"custom entity slots present: {len(custom)}",
         f"custom entity slots enabled:  {len(visible)}", "",
         "enabled:"]
lines += [f"  {k:<24} display={(v.get('name') or {}).get('value')!r}" for k, v in sorted(visible.items())] or ["  none"]
lines += ["", "sample of disabled slots (first 5):"]
lines += [f"  {k:<24} name={(v.get('name') or {}).get('value')!r} visible={(v.get('visible') or {}).get('value')}"
          for k, v in sorted(custom.items()) if k not in visible][:5]

_lib.emit("008_custom_entities", "\n".join(lines), env)
