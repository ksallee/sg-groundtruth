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

# Absence from /schema is the enablement test only if an absent slot is unaddressable. Ask for one
# directly instead of inferring it from the listing.
absent = [f"CustomEntity{n:02d}" for n in range(1, 100) if f"CustomEntity{n:02d}" not in schema]
lines += ["", f"slots absent from /schema: {len(absent)} (first: {absent[:3]})",
          "", "addressing an absent slot directly:"]
for slug in absent[:2]:
    for path in (f"/schema/{slug}", f"/schema/{slug}/fields"):
        r = c.get(path)
        lines.append(f"  GET {path} -> {r.status_code}")
        lines.append(f"    {r.text}")

_lib.emit("008_custom_entities", "\n".join(lines), env)
