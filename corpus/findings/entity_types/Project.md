---
tags: [entity-type, project, schema, filter, trap]
scope: api
summary: A show, the scope almost every other type is filtered by.
verdict: Project is site-wide and has no `project` field, so a scoping filter 400s on it; `name` is the identity, the only field both mandatory and unique, and `code` is a second unique text field.
---

# Project

**Type** Schema name `Project`, addressed at `/entity/projects`. Site-wide, not project-scoped.

The path segment is matched against the schema name loosely. Both cases and both numbers resolve; what
404s is a spelling that loses the word boundary, and the 404 names the type it could not find.

| path | result |
|---|---|
| `/entity/projects` | 200, `type: "Project"` |
| `/entity/project`, `/entity/Project`, `/entity/Projects` | 200, same rows |
| `/entity/projectz` | 404 `Entity type 'projectz' does not exist.` |
| `/entity/published_files`, `/entity/PublishedFile`, `/entity/human_users` | 200 |
| `/entity/publishedfiles` | 404 `Entity type 'publishedfiles' does not exist.` |

Probe 002 found no endpoint that enumerates types, so write the snake_case plural and treat the 404
`detail` as the check.

Project has no `project` field, so nothing scopes a listing of projects:

```
GET /entity/projects?filter[project.Project.id]=N -> 400
  title  "API read() Project.project.Project.id doesn't exist."
  source {"Project.project.Project.id": " does not exist. Value: {\"path\" => \"project.Project.id\",
          \"relation\" => \"is\", \"values\" => [\"N\"]}"}
```

Narrow a project listing with `filter[id]` or with the checkboxes (probe 018). Project is the scope every
other type points at, so the useful direction is inbound:

| call | result |
|---|---|
| `GET /entity/shots?filter[project.Project.id]=N` | 200 |
| `GET /entity/shots?filter[project]=N` | 400 `API read() Shot.project expected [Hash, ActiveSupport::HashWithIndifferentAccess, ActionDispatch::Http::Parameters, ActionDispatch::Http::ParamsHashWithIndifferentAccess, NilClass] data type(s) but got String: "N"` |
| `POST /entity/shots/_search` with `["project", "is", {"type": "Project", "id": N}]` | 200 |
| `GET /entity/shots?fields=project.Project.name` | 200, flat key `"project.Project.name"` under `attributes` |

**Identity** `name`. It is the only field on the type flagged both `mandatory` and `unique`, and it is what
`cached_display_name` mirrors.

| field | mandatory | unique | editable |
|---|---|---|---|
| `name` | true | true | true |
| `code` | false | true | true |
| `cached_display_name` | false | false | true |
| `tank_name` | false | false | true |

`code` is not the identity here, unlike `Shot.code` and `Version.code`. It is unique when set and may be
empty: on the probed site 5 of 22 projects have a `code`, and it equals `name` on 1 of them. `tank_name`
is the folder name on disk, not a display name. Read `name`, and `cached_display_name` only as a fallback.

**Create** `POST /entity/projects` with `{"name": ...}` and `Content-Type: application/json` returns 201
(probe 011, behind `--write`). The 201 body echoes 6 attributes, not the row, so GET the new project for
anything else. `name` being unique means a create is not idempotent: search by name first and reuse the
hit. This card posts nothing. Project is site-wide, so there is no sandbox project to scope a write to,
and every row is a real show.

**Links**

| field | type | editable | `valid_types` |
|---|---|---|---|
| `users` | multi_entity | true | `['HumanUser']` |
| `task_templates` | multi_entity | true | `['TaskTemplate']` |
| `tags` | multi_entity | true | `['Tag']` |
| `asset_linked_projects_assets` | multi_entity | true | `['Asset']` |
| `phases` | multi_entity | true | `[]` |
| `layout_project` | entity | false | `['Project']` |
| `created_by`, `updated_by` | entity | false | `['HumanUser', 'ApiUser']` |
| `image_source_entity` | entity | false | every entity type on the site |

All of them are returned under `relationships`, never `attributes` (`field_types/entity`,
`field_types/multi_entity`). A client normally reads none of them: it identifies a project and then
filters other types by it. `layout_project` names the template a project was cloned from and is read only.
`phases` declares no `valid_types` at all, so validate that one client-side.

**Status** `sg_status`, data_type `list` rather than `status_list`. There is no `Status` row behind a
`list`, so there is no icon, no `bg_color` and no display label to render (`field_types/status_list`,
probe 010). Read the usable set for one project with `GET /schema/Project/fields?project_id=N` and
subtract `hidden_values` from `valid_values` (probe 009); the vocabulary itself is site configuration.
`sg_type` is a second `list` field of the same shape.

On the probed site `sg_status` has no `display_values` and is null on 15 of 22 projects, 8 of them working
shows, so a picker that filters on it hides real projects (probe 018).

**Traps**
- `is_template`, `is_demo` and `is_template_project` are read only over REST, so the flags a picker filters
  on cannot be set by a script user. `archived` is editable.
- `start_date`, `end_date` and `duration` are read only and derived. On the probed site all three are null on
  every project read, so do not filter or sort a project listing on them.
- `landing_page_url` is a path, not a URL: `"/detail/Project/N?legacy=true"`. Prefix the site URL yourself.
- On the probed site `GET /schema/Project/fields` returns 42 fields, 15 of them not editable
  (`created_at`, `created_by`, `duration`, `end_date`, `id`, `image_blur_hash`, `image_source_entity`,
  `is_demo`, `is_template`, `is_template_project`, `landing_page_url`, `layout_project`, `start_date`,
  `updated_at`, `updated_by`). The count is site configuration; the names are stock.
