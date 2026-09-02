---
tags: [entity-type, delivery, version, published-file, reply, attachment, create, multi-entity, entity-field, status, list-field, filter, trap]
scope: api
verdict: Delivery has two independent Version links, sg_versions and version_sg_deliveries_versions; writing one leaves the other empty, and only the second mirrors Version.sg_deliveries.
---

# Delivery

**Type** Schema name `Delivery`, addressed at `/api/v1/entity/deliveries`, 32 fields. The slug is neither
case nor plural sensitive, and only an unknown name is refused.

```
GET /entity/deliveries -> 200    GET /entity/Deliveries  -> 200    GET /entity/deliverys -> 200
GET /entity/delivery   -> 200    GET /entity/Delivery    -> 200
GET /entity/deliveriess -> 404 "Entity type 'deliveriess' does not exist."
GET /entity/deliver     -> 404 "Entity type 'deliver' does not exist."
```

Project-scoped: `Delivery.project` is an editable `entity` field, `valid_types: ['Project']`, required on
create. On the probed site the type holds zero rows site-wide, so everything below was measured on rows
created in the sandbox and deleted.

**Identity** `title`, display name `Title`, `data_type: text`. No Delivery field is flagged `mandatory`
and none is flagged `unique`: two deliveries created in one project with the same `title` both returned
201. Omit `title` and the server writes `New Delivery <id>`. `delivery_number` is read-only `text`
holding the id as a string, and it is not reused after a delete.

`cached_display_name` is `#<delivery_number>: <title>`, and stale in the create response: the 201 that
returned `delivery_number` `"34"` returned `'#(No Number) : zzprobe_036_delivery'`, which a later `PUT`
of `title` recomposed as `'#34: zzprobe_036_renamed'`. Re-read after the create (probe 024).

**Create** `POST /entity/deliveries`, `Content-Type: application/json`. `project` is the whole contract,
inverting the schema's flags as Playlist, Shot and Version do (probe 012).

| body sent | result |
|---|---|
| `{}` | 400 code 103 `API create() missing 'project' attribute: {}` |
| `{"project": {"type": "Project", "id": N}}` | 201, `title` `"New Delivery 21"`, `delivery_number` `"21"`, `sg_status_list` `"opn"`, `sg_delivery_progress` `null` |
| `{"project": …, "title": "…"}` | 201, `title` as sent |
| the same `{project, title}` again | 201, a second Delivery with the same title |

The 201 echoes eight attributes: `cached_display_name`, `created_at`, `delivery_number`,
`read_by_current_user`, `reply_content`, `sg_status_list`, `title`, `updated_at`.

**Links** Written and read as `field_types/entity` and `field_types/multi_entity` describe.

| field | data type | `valid_types` | editable |
|---|---|---|---|
| `sg_versions` | multi_entity | `['Version']` | yes |
| `version_sg_deliveries_versions` | multi_entity | `['Version']` | yes |
| `sg_published_files` | multi_entity | `['PublishedFile']` | yes |
| `attachments` | multi_entity | `['Attachment']` | yes |
| `replies` | multi_entity | `['Reply']` | yes |
| `addressings_to`, `addressings_cc` | multi_entity | `['Group', 'HumanUser']` | yes |
| `tags` | multi_entity | `['Tag']` | yes |
| `project` | entity | `['Project']` | yes |
| `sg_from` | entity | `['HumanUser']` | yes |
| `created_by`, `updated_by` | entity | `['HumanUser', 'ApiUser']` | no |
| `image_source_entity` | entity | every entity type on the site | no |

**Two Version links, and they are not one link.**

```
PUT Delivery.sg_versions                     200  {"sg_versions": [V], "version_sg_deliveries_versions": []}
PUT Delivery.version_sg_deliveries_versions  200  {"sg_versions": [V], "version_sg_deliveries_versions": [V]}
PUT Delivery.sg_versions []                  200  {"sg_versions": [],  "version_sg_deliveries_versions": [V]}
PUT Version.sg_deliveries [D]                200  {"sg_versions": [V], "version_sg_deliveries_versions": [V]}
PUT Version.sg_deliveries []                 200  {"sg_versions": [V], "version_sg_deliveries_versions": []}
```

`version_sg_deliveries_versions` is the reverse of `Version.sg_deliveries`, the only field on Version with
`valid_types: ['Delivery']`, whose join row `Version_sg_deliveries_Connection` answers a `GET` at 200.
`sg_versions` has no counterpart on Version, and neither has `sg_published_files` on PublishedFile.
Nothing observable through the API says which link the web interface fills, and the probed site has no
rows to look at: write both, read both, take the union.

**Status** Two fields, and a client needs both: `sg_status_list` is the code, `sg_delivery_progress` a
`list` beside it. Both vocabularies are site configuration, read per project with
`GET /schema/Delivery/fields/sg_status_list?project_id=<pid>` (probe 009), and `hidden_values` is not a
subset of `valid_values` (`field_types/status_list`).

| field | data type | on the probed site |
|---|---|---|
| `sg_status_list` | status_list | `['opn', 'ip', 'dlvr', 'recd']`, `default_value` `opn`, `hidden_values` `[]` at site and project scope |
| `sg_delivery_progress` | list | 11 values, among them `In transit`, `Delivery cancelled`, `Delivery failed`, `Delivered`, `Ingesting`, `Ingest failed` |
| `sg_delivery_method` | list | `['FTP', 'Aspera', 'FedEx', 'Sneaker Net']` |
| `sg_delivery_type` | list | `valid_values: []` |

On the probed site the status codes stop at `dlvr` and `recd`, so a cancelled or failed transfer is
expressible only through `sg_delivery_progress` and the free-text `description` (`recipes/008_delivery_progress`).

**Filter** Every field filters, with the relations its data type allows (probe 017). An unfiltered
`_search` returns deliveries from every project, so send the project filter on every read.

| field | `Valid relations` |
|---|---|
| `sg_status_list`, `sg_delivery_progress` | `["is", "is_not", "in", "not_in"]` |
| `title`, `delivery_number` | `["contains", "not_contains", "is", "is_not", "starts_with", "ends_with", "in", "not_in"]` |
| `project`, `sg_versions` | `["is", "is_not", "name_contains", "name_not_contains", "name_is", "type_is", "type_is_not", "in", "not_in"]` |

**Traps**
- `reply_content` returns a developer warning instead of a value. On a Delivery holding one real Reply it
  read `'Warning: If you see this displayed in the UI, it means the widget is not respecting grid_column
  = false.'` The thread is `replies`, or `POST /entity/replies/_search` on
  `[["entity", "is", {"type": "Delivery", "id": N}]]` (`entity_types/Reply`).
- `sg_delivery_type` has `valid_values: []`, so every write is
  `400 … 'Final' is not a valid list value. Valid list values: ''.` An empty vocabulary is a field that
  can never be set, not a free-text field.
- A Reply reads back HTML-escaped through one field and not the other: `content` containing `"` is
  returned verbatim by `Reply.content` and by the `name` of the `Delivery.replies` link, and as `&quot;`
  by `Reply.cached_display_name`.
- Eight fields are read-only, `created_at`, `created_by`, `delivery_number`, `id`, `image_blur_hash`,
  `image_source_entity`, `updated_at`, `updated_by`, and they refuse a write two different ways:

| written | answer |
|---|---|
| `created_at` | 400 code 103 `API update() Delivery.created_at is editable on create only.` |
| `delivery_number` | 400 code 104 `The field is not editable for this user: [Delivery.delivery_number]. Rule: API Admin -- PermissionRule 336: DENY update_field FOR entity_type => Delivery, field_name => delivery_number, field_value =>`, so the message depends on the script's role (probe 027) |
