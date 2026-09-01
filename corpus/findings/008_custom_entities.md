---
tags: [schema, custom-entity, discovery]
verdict: /schema returns ONLY enabled custom entities (11 slots, all visible) - a disabled slot is simply absent, so presence in /schema is the enablement test. Slot numbers are non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value and never hardcode a number. Connection entities appear as their own type.
---

# 008_custom_entities

**Endpoint** `GET /api/v1/schema`

**Docs claim** Custom entities are CustomEntityNN; display name lives in the schema; cannot be enabled over REST.

**Actual**

```
total entity types in /schema: 113
custom entity slots present: 11
custom entity slots enabled:  11

enabled:
  CustomEntity01           display='E2E Test Run'
  CustomEntity02           display='E2E Test Result'
  CustomEntity03           display='Code Quality Report'
  CustomEntity04           display='Benchmark Run'
  CustomEntity05           display='Fields History'
  CustomEntity06           display='Security Scan Report'
  CustomEntity07           display='Security Finding'
  CustomEntity19           display='Lenses'
  CustomEntity29           display='Location'
  CustomEntity29_sg_scene_Connection display='Custom Entity29 Sg Scene Connection'
  CustomEntity66           display='Weekly Report Custom Entity '

sample of disabled slots (first 5):
```

**Verdict** /schema returns ONLY enabled custom entities (11 slots, all visible) - a disabled slot is simply absent, so presence in /schema is the enablement test. Slot numbers are non-contiguous and site-specific (01-07, 19, 29, 66 here); resolve display names from name.value and never hardcode a number. Connection entities appear as their own type.
