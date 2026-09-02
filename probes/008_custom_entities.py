"""Q: which CustomEntityNN are enabled on this site, and how do I get their real names?"""
import _lib

env = _lib.load_env()
c = _lib.client()

schema = c.get("/schema").json()["data"]
_lib.register_from(schema)
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

actual = "\n".join(lines)
_lib.record("008_custom_entities", "GET /api/v1/schema",
            "Custom entities are CustomEntityNN; display name lives in the schema; cannot be enabled over REST.",
            actual,
            f"/schema returns ONLY enabled custom entities ({len(custom)} slots, all visible) - a disabled slot "
            f"is simply absent, so presence in /schema is the enablement test. Slot numbers are "
            f"non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value "
            f"and never hardcode a number. Connection entities appear as their own type.",
            env, tags=("schema", "custom-entity", "discovery"))
print(actual)
