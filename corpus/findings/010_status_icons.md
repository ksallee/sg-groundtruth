---
tags: [status, icon, cache, colour, entity-field]
scope: api
verdict: Status.icon is an entity link, so it is returned under relationships; display_type then picks one of three renderings, and bg_color alone already draws a badge.
---

# 010_status_icons

**Q** How does a status resolve to a colour and an icon, and do standard and custom icons differ?

**Endpoint** `GET /entity/statuses?fields=...,icon ; GET /entity/icons`

**Docs claim** Silent. Status and Icon are listed as ordinary entity types; nothing says how an icon resolves to an image.

**Actual**

```
Status fields: ['bg_color', 'cached_display_name', 'code', 'created_at', 'created_by', 'icon', 'id', 'name', 'system', 'updated_at', 'updated_by']
Status.icon data_type: entity

statuses: 32, with an icon relationship: 32
sample bg_color: ["25,118,27", "179,179,179", "150,150,150", "146,146,146"]

Icon fields: ['cached_display_name', 'display_type', 'html', 'icon_type', 'id', 'image_data', 'image_map_key', 'name', 'url', 'uuid']

98 icons, grouped by (icon_type, display_type):
  permanent_status / image_map  n=94
    url            empty string
    image_map_key  "icon_apr"
    html           null
    image_data     null

  custom_status / image  n=1
    url            data:image/png;base64,iVBORw0KG... (978 chars)
    image_map_key  null
    html           null
    image_data     base64 str, 972 chars

  custom_status / html  n=3
    url            empty string
    image_map_key  null
    html           "Active"
    image_data     null

unauthenticated GET /dist/production/stylesheets/login.css -> 200  771416 bytes  text/css
  div.icon_apr {width: 12px; height: 11px; background: ... url(/images/sg_icon_image_map.png?<hash>) -89px -11px ...}
unauthenticated GET /images/sg_icon_image_map.png?<hash>  -> 200  335561 bytes  image/png
```

**Teaches**
- `Status.icon` is an entity link, so it is returned under `relationships`, never `attributes`. Read
  `attributes` alone and every icon looks null (probe 004).
- `display_type` picks one of three renderings:

  | `display_type` | rendering |
  |---|---|
  | `image_map` | stock icon. `url` is empty; address it by `image_map_key`, such as `icon_apr` |
  | `image` | custom upload. `url` is a self-contained `data:image/png;base64` URI whose newlines must be stripped, and `image_data` holds the same bytes |
  | `html` | custom text badge. `html` is the label, and there is no image |

- `bg_color` is comma-separated RGB (`"25,118,27"`), not hex, and draws a badge on its own with no icon
  fetched: the cheapest correct rendering.
- The `image_map` sprite is not in the API. Nothing in `/entity/icons` names a stylesheet or an image, so
  do not expect the REST API to hand you a stock icon.
- `image_map_key` is a CSS class. On the probed site the rule is in the web app's
  `/dist/production/stylesheets/login.css` and points at `/images/sg_icon_image_map.png?<hash>` with a
  per-icon background offset (`div.icon_apr` -> `-89px -11px`); both answered a GET with no
  `Authorization` header at 200. Those two paths are undocumented and were found by reading the site's own
  stylesheet, so a client must rediscover them the same way. Fetch the page's stylesheet, match
  `.<image_map_key>`, and take the `url()` and the offset from the rule. Hardcoding either path breaks on a
  differently-versioned deployment.
