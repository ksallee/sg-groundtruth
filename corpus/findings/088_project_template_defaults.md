---
tags: [task-template, project, serializable, discovery]
endpoints: [GET /schema/<Type>/fields, POST /entity/<type>/_search, GET /entity/<type>/<id>, GET /preferences]
phase: read
scope: api
coverage: partial
unmeasured: Whether a Shot or Asset created over REST without `task_template` gets the default: blocked on the site, since testing it means writing a project's tracking settings.
measured: site-wide read of 22 projects and 20 templates, sample project 1 of 1
verdict: The per-entity-type default is readable at `Project.tracking_settings.default_task_template.<Type>`, a `{type, id, name, valid}` dict. `Project.task_templates` is a separate list, not the default.
---

# 088_project_template_defaults

**Q** Can a script read which task template a project uses for each entity type?

**Endpoint** `GET /schema/Project/fields ; POST /entity/projects/_search ; POST /entity/project_task_template_connections/_search ; GET /preferences`

**Docs claim** Silent. `tracking_settings` is typed `serializable` with no declared structure
(`field_types/serializable`).

**Actual**

```
Project fields naming a template or a setting
  task_templates     multi_entity ['TaskTemplate'] editable
  tracking_settings  serializable                  editable
  is_template, is_template_project  checkbox, read only (the project flags, not task templates)

22 projects; tracking_settings key paths, projects holding each
  navchains.Asset 21   navchains.Cut 22   navchains.CutItem 22   navchains.Shot 20   navchains.Sequence 1
  default_task_template present on 6, non-empty on 1
  Shot: true on 1
project A: {"default_task_template": {"Asset": {"type": "TaskTemplate", "id": 40,
            "name": "<template>", "valid": "valid"}}}
  GET /entity/task_templates/40 -> 200; in project A's task_templates: False
five projects: {"default_task_template": {}}

Project.task_templates non-empty on 1 of 22: [{"id": 46, "name": "<template>", "type": "TaskTemplate"}]
ProjectTaskTemplateConnection: fields project, task_template, cached_display_name; 1 row, the same pair
TaskTemplate.projects: the same 1 pair; the three agree
GET /preferences: 17 keys, none naming a template or a task
```

**Teaches**

| where | holds | readable |
|---|---|---|
| `Project.tracking_settings.default_task_template.<EntityType>` | the default template for that type, as `{type, id, name, valid}` | yes, `?fields=tracking_settings` |
| `Project.task_templates` | a list of templates attached to the project | yes |
| `ProjectTaskTemplateConnection` | the join row behind `task_templates` | yes, `/entity/project_task_template_connections` |
| `TaskTemplate.projects` | the same list from the other side | yes |
| `/preferences` | nothing about templates | n/a |

- **The default and the attached list are different data.** On the probed site the one project with a
  default for Asset does not list that template in `task_templates`. Read the default from
  `tracking_settings`, never infer it from the list.
- On the probed site `default_task_template` is absent on 16 projects and `{}` on 5. Absent, `{}` and a
  missing entity-type key all mean no default. `valid` read `"valid"`; no other value was seen.
- `tracking_settings` is a blob: no filter reaches into it (`field_types/serializable`), so finding
  projects with a default means reading every project's value.
- **Whether the API applies the default is unmeasured.** Probe 083 found `task_template: null` on a
  create generates nothing in a project with no default. Send `task_template` explicitly rather than
  rely on the project default.
