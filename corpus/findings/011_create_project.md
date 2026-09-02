---
tags: [write, project, create, sandbox]
verdict: see below
---

# 011_create_project

**Endpoint** `POST /api/v1/entity/projects`

**Docs claim** Projects can be created over REST by a script user.

**Actual**

```
Project fields: 42
mandatory: ['name']
editable (first 25): ['archived', 'asset_linked_projects_assets', 'billboard', 'cached_display_name', 'client_site_settings_saved', 'code', 'color', 'current_user_favorite', 'filmstrip_image', 'image', 'last_accessed_by_current_user', 'name', 'phases', 'sg_client_name', 'sg_description', 'sg_flow_am_id', 'sg_flow_schema_config_version', 'sg_latest_version', 'sg_release_date', 'sg_status', 'sg_temp_due', 'sg_type', 'tags', 'tank_name', 'task_templates']

sandbox already present: False

POST /entity/projects -> 201
created id=1180; attributes returned: ['cached_display_name', 'created_at', 'landing_page_url', 'name', 'tracking_settings', 'updated_at']
```

**Verdict** see below
