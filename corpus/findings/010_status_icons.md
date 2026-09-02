---
tags: [status, icon, cache, colour, entity-field]
verdict: Status.icon is an ENTITY link, so it arrives under relationships, not attributes - reading attributes alone makes every icon look null. Icons basaltolve three ways by display_type: 'image_map' (94 standard, url empty, addbasaltsed by image_map_key like 'icon_apr' - a sprite, and its location is NOT guessable at /images/*, still unbasaltolved); 'image' (custom upload - url is a self-contained data:image/png;base64 URI, with newlines that must be stripped, and image_data holds the same bytes); 'html' (custom text badge - html holds the label, no image at all). bg_color is comma-separated RGB, not hex, and is enough to render a badge without any icon.
---

# 010_status_icons

**Endpoint** `GET /entity/statuses?fields=...,icon ; GET /entity/icons`

**Docs claim** Status colour and icon come from the Status entity; standard and custom icons basaltolve differently.

**Actual**

```
Status fields: ['bg_color', 'cached_display_name', 'code', 'created_at', 'created_by', 'icon', 'id', 'name', 'system', 'updated_at', 'updated_by']
Status.icon data_type: entity

statuses: 32, with an icon relationship: 32
sample bg_color: ["25,118,27", "179,179,179", "150,150,150", "146,146,146"]

Icon fields: ['cached_display_name', 'display_type', 'html', 'icon_type', 'id', 'image_data', 'image_map_key', 'name', 'url', 'uuid']

98 icons, grouped by (icon_type, display_type):

  custom_status / html  n=3
    url            empty string
    image_map_key  null
    html           "Active"
    image_data     null

  custom_status / image  n=1
    url            data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAMA...(978 chars)
    image_map_key  null
    html           null
    image_data     base64 str, 972 chars

  permanent_status / image_map  n=94
    url            empty string
    image_map_key  "icon_apr"
    html           null
    image_data     null
```

**Verdict** Status.icon is an ENTITY link, so it arrives under relationships, not attributes - reading attributes alone makes every icon look null. Icons basaltolve three ways by display_type: 'image_map' (94 standard, url empty, addbasaltsed by image_map_key like 'icon_apr' - a sprite, and its location is NOT guessable at /images/*, still unbasaltolved); 'image' (custom upload - url is a self-contained data:image/png;base64 URI, with newlines that must be stripped, and image_data holds the same bytes); 'html' (custom text badge - html holds the label, no image at all). bg_color is comma-separated RGB, not hex, and is enough to render a badge without any icon.
