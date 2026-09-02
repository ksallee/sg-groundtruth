---
tags: [write, project, create, schema]
scope: api
measured: site-wide, one Project created (the sandbox project itself)
verdict: A script user can create a Project with nothing but {"name": ...}, at 201, but the response echoes only 6 attributes, so read the project back if you need anything else.
---

# 011_create_project

**Q** What does creating a Project over REST require, and does it work from a script user?

**Endpoint** `GET /schema/Project/fields ; GET /entity/projects ; POST /entity/projects`

**Docs claim** Projects can be created over REST by a script user. The docs do not say which fields are required.

**Actual**

```
Project fields: 42
mandatory: ['name']
editable (first 25): ['archived', 'asset_linked_projects_assets', 'billboard', 'cached_display_name', 'client_site_settings_saved', 'code', 'color', 'current_user_favorite', 'filmstrip_image', 'image', 'last_accessed_by_current_user', 'name', 'phases', 'sg_client_name', 'sg_description', 'sg_flow_am_id', 'sg_flow_schema_config_version', 'sg_latest_version', 'sg_release_date', 'sg_status', 'sg_temp_due', 'sg_type', 'tags', 'tank_name', 'task_templates']

sandbox already present: False

POST /entity/projects -> 201
created id=1180; attributes returned: ['cached_display_name', 'created_at', 'landing_page_url', 'name', 'tracking_settings', 'updated_at']
```

**Teaches**
- `{"name": "sandbox_show"}` with `Content-Type: application/json` is a complete create: 201, no project
  template, no `code`, no dates.
- On the probed site, `GET /schema/Project/fields` returns 42 fields and flags exactly one, `name`,
  `mandatory: true`. That count is site configuration, and a schema flag is not the create contract
  (probe 012), so it does not establish that `name` is the server's only requirement. This probe never
  posted a body without `name`; that POST, behind `--write`, would settle it.
- **Trap.** The 201 body is not an entity read. It echoes 6 attributes (`cached_display_name`,
  `created_at`, `landing_page_url`, `name`, `tracking_settings`, `updated_at`); everything else, `id`
  apart, needs a GET on the new project.
- `name` is flagged both mandatory and unique in the schema, so creating is not idempotent. Probe first
  (`GET /entity/projects?fields=name`) and reuse the hit, as this probe does. Custom *fields* silently
  become `<name>_1` on a duplicate (probe 019); whether a Project name collides or duplicates is
  `<unverified>`.
- A fresh project has no `sg_status`, so a picker must not filter on it (probe 018).
