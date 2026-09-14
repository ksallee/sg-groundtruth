# Findings — render: showing it to a person

How the API behaves in this part of a session. Each rule is the entry's own **Teaches**, copied whole.

## 010_status_icons

Status.icon is an entity link under relationships; display_type picks one of three renderings; url is empty unless image_data is asked for beside it; the stock sprite is in the site's own stylesheet.

- `Status.icon` is an entity link, so it is returned under `relationships`, never `attributes`. Read
  `attributes` alone and every icon looks null (probe 004).

- `display_type` picks one of three renderings:

  | `display_type` | rendering |
  |---|---|
  | `image_map` | stock icon. `url` is empty; address it by `image_map_key`, such as `icon_apr` |
  | `image` | custom upload. `url` is a self-contained `data:image/png;base64` URI whose newlines must be stripped, and `image_data` holds the same bytes |
  | `html` | custom text badge. `html` is the label, and there is no image |

- Ask for `image_data` beside `url`. `?fields=display_type,url` returns `""` for the `image`
  rendering and the same request with `image_data` added returns the data URI, so narrowing the
  projection is what empties the field, and `""` is indistinguishable from "this icon has no
  image". `recipes/010` measures every combination and draws the whole picker from them.

- `bg_color` is comma-separated RGB (`"25,118,27"`), not hex, and draws a badge on its own with no icon
  fetched: the cheapest correct rendering.

- The `image_map` sprite is not in the API. Nothing in `/entity/icons` names a stylesheet or an image, so
  do not expect the REST API to hand you a stock icon.

- `image_map_key` is a CSS class. On the probed site the rule is in the web app's
  `/dist/production/stylesheets/login.css` and points at `/images/sg_icon_image_map.png?<hash>` with a
  per-icon background offset (`div.icon_apr` -> `-89px -11px`); both answered a GET with no
  `Authorization` header at 200.

- Those two paths are undocumented and were found by reading the site's own stylesheet, so a client must
  rediscover them the same way. Fetch the page's stylesheet, match `.<image_map_key>`, and take the `url()`
  and the offset from the rule. Hardcoding either path breaks on a differently-versioned deployment.

`corpus/findings/010_status_icons.md`
