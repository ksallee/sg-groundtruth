---
tags: [create, permission, sudo, url, browser]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; 12 site rows made and deleted, as the script, an Admin and an Artist
coverage: partial
unmeasured: what the web interface sends to the URL, and Manager rights. Needs a person: `156 --write --listen 8765 --hold 900`, then run the items on a Shot
verdict: An ActionMenuItem creates from `{}` at 201 though `title` is flagged mandatory, and `url` is not validated. An Artist is refused; `permissions_groups` does not filter what the API returns.
---

# 156_action_menu_item

**Q** What does creating an ActionMenuItem by API take, which of its fields hold what was sent, who
may create one, and what does the web interface send to its URL when a person runs it?

**Endpoint** `POST /entity/action_menu_items ; GET /entity/action_menu_items/<id> ; POST /entity/action_menu_items/_search`

**Docs claim** Silent. The schema flags `title` mandatory and nothing else. There is no `configure_as`
field: what a menu item does is `url`, `payload_content_type` and the checkboxes below.
`field_types/entity_type` measured `ActionMenuItem.entity_type`; this measures the rest of the row.

**Actual**

```
POST /entity/action_menu_items
  {}                                    -> 201
  {title} | {title, url} | + entity_type "Shot", projects [sandbox] -> 201
  read back, nothing else sent: payload_content_type "form", signature_algorithm "sha256",
    add_btn_behavior "not_set", secret_token "", list_order null, the three checkboxes false
  every editable field set              -> 201, each reads back as sent;
    secret_token reads "*******"
  url "sgonset://shot/1" | "not a url"  -> 201
  payload_content_type "xml"            -> 400 code 104 "... Valid list values: 'form', 'json'."

as an Admin person (sudo_as_login)      create -> 201
as an Artist                            create -> 400 code 104 "Entity of type ActionMenuItem cannot be
                                                   created by this user."
three rows, permissions_groups [admin], [artist], none
  read by the Admin                     all three
  read by the Artist                    all three
```

**Fields**

| field | type | values, as measured |
|---|---|---|
| `title`, `url`, `folder` | text | stored as sent; `url` takes any string |
| `entity_type` | entity_type | a schema type name, validated as `field_types/entity_type` describes |
| `projects` | multi_entity | `Project` rows; empty when not sent |
| `permissions_groups` | multi_entity | `PermissionRuleSet` rows; empty when not sent |
| `list_order` | number | null when not sent |
| `selection_required`, `light_payload`, `open_in_overlay`, `poll_for_data_updates` | checkbox | false when not sent |
| `payload_content_type` | list | `form` (default), `json` |
| `add_btn_behavior` | list | `not_set` (default), `include_in_dropdown`, `override_default`, `internal_resources` |
| `signature_algorithm` | list | `sha256` (default), `sha1` |
| `secret_token` | text | `""` when not sent, `"*******"` on read once set |

**Teaches**
- Send `title`, `url`, `entity_type` and `projects` yourself: the server takes a row with none of
  them, and checks only `entity_type` (`field_types/entity_type`) and the list fields.
- Creating one is an administrator's call on the probed site: Admin 201, Artist 400 code 104.
  Manager was not reachable (probe 132), so do not infer it.
- `permissions_groups` is not a read filter: an Artist reads rows restricted to Admin. Whether it
  hides the item in the web interface is the browser step below.
- `secret_token` is write-only through the API; keep the value on the client that checks signatures.

**Needs a person**

| question | step |
|---|---|
| the request the web interface sends: method, content type, fields, new window or overlay | `156 --write --listen 8765 --hold 900` on the machine with the browser; sign in, right-click a Shot in the sandbox project, run `zzprobe 156 recorder form` and `... json`, with one Shot selected and then two. The probe prints each request whole |
| a custom-protocol `url` opening an app | the same run: `zzprobe 156 protocol` points at `sgonset://shot/1` |
| Manager rights | turn on `can_impersonate_this_user` for an active Manager, run `156 --write` |
