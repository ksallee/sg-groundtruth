---
tags: [create, permission, sudo, url, browser, header]
endpoints: [POST /entity/<type>, GET /entity/<type>/<id>, POST /entity/<type>/_search, DELETE /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written twice, 2026-11-17; 12 then 14 rows made and deleted, 2 run in the operator's web session
coverage: partial
unmeasured: a custom-protocol `url` opening an app, whether `permissions_groups` hides an item in the web interface, and Manager rights. Each needs a person, steps below. Blocked on the work
verdict: An ActionMenuItem creates from `{}` at 201 and `url` is not checked; an Artist is refused. Run from the web interface, an http `url` got a form POST in a new tab, `json` or not, with no token.
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

**Run from the web interface**

The second run's two recorder rows (`entity_type` `Shot`, `url` `http://localhost:8765/ami/<kind>`,
`payload_content_type` `form` and `json`, every checkbox false) were run from a Shots page in the
sandbox project, in the operator's signed-in Chrome session, driven by Claude in Chrome. Each item ran
once with one Shot selected, then once with two.

```
each run          a new browser tab on the url; the tab then sent GET /favicon.ico
POST /ami/form, POST /ami/json, one Shot then two:
  Content-Type    application/x-www-form-urlencoded     for both items
  Origin          null
  Sec-Fetch-Site  cross-site
  Sec-Fetch-Mode  navigate
  Sec-Fetch-Dest  document
  Referer         absent
  body            21 fields, form and json identical
  selected_ids    <shot_a>                one Shot
                  <shot_a>,<shot_b>       two Shots
```

The recorder kept `Content-Type`, `Origin`, `Referer`, `User-Agent` and the three `Sec-Fetch-*`
headers. Any other header is unrecorded.

| field | value, as recorded |
|---|---|
| `user_id`, `user_login` | the signed-in person's `HumanUser` id and login |
| `title` | `undefined`, the literal string; the item's own title was `zzprobe 156 recorder <kind>` |
| `entity_type` | `Shot` |
| `server_hostname` | the site's host, `<site host>` |
| `referrer_path` | `/detail/HumanUser/<user_id>`, while `page_id` named the Shots page |
| `page_id` | the Shots page's id |
| `session_uuid` | a 36-character UUID |
| `project_name`, `project_id` | the sandbox project |
| `target_column` | `sg_status_list` |
| `ids` | every row on the page, comma-separated, not in id order: 87 on the probed page |
| `selected_ids` | the selected rows, comma-separated |
| `cols` | the page's column fields: `image,code,sg_sequence,sg_status_list`, five `step_<n>`, `sg_cut_in,sg_cut_out,sg_cut_duration` |
| `column_display_names` | the same columns' display names, same order: `Thumbnail,Shot Code,Sequence,Status,LAY,...` |
| `view` | `Default` |
| `sort_column`, `sort_direction` | `code`, `asc` |
| `grouping_column`, `grouping_method`, `grouping_direction` | `sg_sequence`, `exact`, `asc` |

**Teaches**
- Send `title`, `url`, `entity_type` and `projects` yourself: the server takes a row with none of
  them, and checks only `entity_type` (`field_types/entity_type`) and the list fields.
- Creating one is an administrator's call on the probed site: Admin 201, Artist 400 code 104.
  Manager was not reachable (probe 132), so do not infer it.
- `permissions_groups` is not a read filter: an Artist reads rows restricted to Admin. Whether it
  hides the item in the web interface is unmeasured.
- `secret_token` is write-only through the API; keep the value on the client that checks signatures.
- Parse the request as a form. With `payload_content_type` `json`, the browser posted the same
  `application/x-www-form-urlencoded` body to an http `url` as with `form`, field for field, in this run.
- Act on `selected_ids`, split on commas. `ids` is every row on the page, selected or not, and `title`
  is the string `undefined`.
- Check who sent it yourself. The body names a person (`user_id`, `user_login`) and holds no token,
  key or password, so any client that can reach the `url` can post the same form. Whether
  `secret_token` adds a signature was not measured.
- Accept a cross-site navigation: `Origin: null`, `Sec-Fetch-Site: cross-site`, no `Referer`. A server
  that refuses cross-origin form posts refuses every run. Its response is the page the new tab shows.

**Needs a person**

| question | step |
|---|---|
| a custom-protocol `url` opening an app | `156 --write --listen 8765 --hold 900` on the machine with the browser; sign in, right-click a Shot in the sandbox project, run `zzprobe 156 protocol`, which points at `sgonset://shot/1` |
| whether `permissions_groups` hides an item in the web interface | the same run, signed in as an Artist: which of `zzprobe 156 for admin`, `... for artist` and `... for everyone` a Shot's menu lists |
| Manager rights | turn on `can_impersonate_this_user` for an active Manager, run `156 --write` |
