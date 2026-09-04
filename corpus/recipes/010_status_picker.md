---
intent: List the statuses a project actually offers, each with the label, colour and icon needed to draw it
tags: [status, icon, colour, schema, list-field, entity-field, dotted-field, project, cache]
endpoints: [GET /schema/<Type>/fields/<field>, POST /entity/<type>/_search]
scope: api
measured: the first 3 sample projects, read only
---

# 010_status_picker

Anything that shows Flow Production Tracking data to a person draws a status. Four pieces make one:
the codes the project offers, the label for each, the colour, and the icon. The first two come from
the field schema read with `project_id`, the last two from the `Status` row and the `Icon` behind it.
Two calls to the REST API cover all four. The stock icons are not in the API at all and are
rediscovered from the site's own stylesheet.

## Call

```python
import json
import re
import sys
from functools import lru_cache

import requests

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT           # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                     # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # array filters need it (probe 004)

PROJECT = 70                                    # the caller supplies these three
ENTITY_TYPE = "Version"
FIELD = "sg_status_list"

# `url` reads as an empty string unless `image_data` is asked for in the same call, so ask for both.
ICON = ("display_type", "image_map_key", "html", "url", "image_data")
FIELDS = "code,name,bg_color," + ",".join(f"icon.Icon.{f}" for f in ICON)
GREY = "204,204,204"                            # bg_color is null on some Status rows


def fail(r):
    raise SystemExit(r.text)                    # never truncate an error body


def usable(entity_type, field, project_id):
    """The codes the project offers, in the schema's own order, and the labels for them.

    `project_id` is what makes this a project answer: without it `hidden_values` is empty and the
    picker offers statuses the project's interface refuses (probe 009).
    """
    r = c.get(f"/schema/{entity_type}/fields/{field}", params={"project_id": project_id})
    if not r.ok:
        fail(r)
    p = r.json()["data"]["properties"]
    valid, hidden = p["valid_values"]["value"], p["hidden_values"]["value"]
    return [v for v in valid if v not in hidden], p["display_values"]["value"]


@lru_cache(maxsize=1)
def stylesheets():
    """The web app's own CSS, concatenated. 771416 bytes on the probed site, so fetch it once.

    The sprite is not in the REST API. `image_map_key` is a CSS class in a stylesheet the site names
    in its own root page, and the URL that rule points at ends in a per-release hash. Rediscover
    both rather than hardcoding either. Neither fetch needs an Authorization header.
    """
    root = requests.get(c.site, timeout=30)
    if not root.ok:
        return ""
    hrefs = re.findall(r'href=["\']([^"\']+\.css[^"\']*)["\']', root.text, re.I)
    out = []
    for href in hrefs:
        s = requests.get(href if href.startswith("http") else f"{c.site}{href}", timeout=60)
        if s.ok:
            out.append(s.text)
    return "\n".join(out)


def sprite(image_map_key):
    """The crop for one stock icon: the sheet, the offset into it, and the size to take.

    None when the rule is not found, which is the signal to fall back to the colour.
    """
    m = re.search(r"\.%s\b[^{}]*\{([^{}]*)\}" % re.escape(image_map_key), stylesheets())
    if not m:
        return None
    decl = m.group(1)
    href = re.search(r"url\(\s*['\"]?([^'\")]+)", decl)
    offset = re.search(r"(-?\d+)px\s+(-?\d+)px", decl)
    size = re.search(r"width:\s*(\d+)px.*?height:\s*(\d+)px", decl, re.S)
    if not (href and offset and size):
        return None
    return {"kind": "sprite", "url": href.group(1),          # join to the site root to fetch
            "offset": [int(offset.group(1)), int(offset.group(2))],
            "size": [int(size.group(1)), int(size.group(2))]}


def picker(entity_type, field, project_id):
    """Every status the project offers, each ready to draw."""
    codes, labels = usable(entity_type, field, project_id)
    # One call for all of them: `icon` is an entity link, and a dotted path through it returns the
    # Icon's own columns flattened into `attributes` (probe 003). Undotted, `icon` is
    # {id, name, type} and the renderings cost a second call over /entity/icons.
    r = c.post("/entity/statuses/_search", headers=ARR,
               json={"filters": [["code", "in", codes]], "fields": FIELDS,
                     "page": {"size": 200}})
    if not r.ok:
        fail(r)
    by_code = {x["attributes"]["code"]: x["attributes"] for x in r.json()["data"]}
    out = []
    for code in codes:                          # schema order is the order the picker shows
        a = by_code.get(code, {})
        display = a.get("icon.Icon.display_type")
        if display == "image_map":              # a stock icon, addressed by its CSS class
            icon = sprite(a["icon.Icon.image_map_key"])
        elif display == "image":                # a custom upload, already inline
            icon = {"kind": "data_uri", "uri": (a.get("icon.Icon.url") or "").replace("\n", "")}
        elif display == "html":                 # a text badge, no image at all
            icon = {"kind": "text", "text": a.get("icon.Icon.html")}
        else:                                   # no Status row for this code
            icon = None
        out.append({"code": code,
                    "label": labels.get(code, code),         # a missing key falls back to the code
                    "color": a.get("bg_color") or GREY,      # rgb(<color>) draws the badge alone
                    "icon": icon})
    return out


def show(entity_type, field, project_id):
    options = picker(entity_type, field, project_id)
    print(f"{len(options)} statuses for {entity_type}.{field} on project {project_id}")
    for o in options:
        icon = dict(o["icon"] or {"kind": "none"})
        if icon.get("kind") == "data_uri":       # never print the blob
            icon["uri"] = f"{icon['uri'][:32]}...({len(icon['uri'])} chars)"
        if icon.get("kind") == "sprite":
            icon["url"] = icon["url"].split("?")[0] + "?<release hash>"
        print(f"  {o['code']:<8} {o['label']:<22} rgb({o['color']:<11}) {json.dumps(icon)}")
    return options


options = show(ENTITY_TYPE, FIELD, PROJECT)
show("HumanUser", "sg_status_list", PROJECT)     # the third branch, on this site's user statuses

# A stored value is not a member of that list. `hidden_values` is not a subset of `valid_values`,
# and a hidden code writes and reads back at 200 (`field_types/status_list`), so read the label off
# the whole vocabulary and let the picker restrict only what a person may pick.
r = c.get(f"/schema/{ENTITY_TYPE}/fields/{FIELD}", params={"project_id": PROJECT})
labels = r.json()["data"]["properties"]["display_values"]["value"]
offered = {o["code"] for o in options}
for stored in ("apr", "pndl", None):
    print(f"  stored {str(stored):<6} label {labels.get(stored, stored)!r:<24} "
          f"offered by the picker: {stored in offered}")
```

## Response

On the probed site, project 70 hides `pndl` and `pndvs` of Version's 16 codes, and `HumanUser` is the
one type whose statuses reach the `html` branch. The status codes and labels below are that site's
vocabulary, read rather than assumed.

```
14 statuses for Version.sg_status_list on project 70
  na       N/A                    rgb(204,204,204) {"kind": "sprite", "url": "/images/sg_icon_image_map.png?<release hash>", "offset": [-46, 0], "size": [7, 6]}
  rev      Pending Review         rgb(149,227,167) {"kind": "sprite", ... "offset": [-314, -23], "size": [12, 13]}
  vwd      Viewed                 rgb(146,146,146) {"kind": "sprite", ... "offset": [-128, 0], "size": [7, 8]}
  apr      Approved               rgb(179,179,179) {"kind": "sprite", ... "offset": [-89, -11], "size": [12, 11]}
  custom   CustomIcon             rgb(204,204,204) {"kind": "data_uri", "uri": "data:image/png;base64,iVBORw0KGg...(978 chars)"}
  fin      Final                  rgb(150,150,150) {"kind": "sprite", ... "offset": [-128, 0], "size": [7, 8]}
  ip       In Progress            rgb(202,225,202) {"kind": "sprite", ... "offset": [-332, 0], "size": [10, 10]}
  clsd     Closed                 rgb(150,150,150) {"kind": "sprite", ... "offset": [-128, 0], "size": [7, 8]}
  cmpt     Complete               rgb(146,146,146) {"kind": "sprite", ... "offset": [-337, -79], "size": [14, 14]}
  cfrm     Confirmed              rgb(161,236,154) {"kind": "sprite", ... "offset": [-352, -586], "size": [16, 16]}
  pndad    Pending Art Director   rgb(246,155,12 ) {"kind": "sprite", ... "offset": [-144, -586], "size": [16, 16]}
  part     partial                rgb(203,243,23 ) {"kind": "sprite", ... "offset": [-330, -538], "size": [16, 16]}
  pass     pass                   rgb(204,204,204) {"kind": "sprite", ... "offset": [-89, -11], "size": [12, 11]}
  pndng    Pending                rgb(150,150,150) {"kind": "sprite", ... "offset": [-64, -602], "size": [16, 16]}
2 statuses for HumanUser.sg_status_list on project 70
  act      Active                 rgb(25,118,27  ) {"kind": "text", "text": "Active"}
  dis      Disabled               rgb(204,0,1    ) {"kind": "sprite", ... "offset": [-46, 0], "size": [7, 6]}
  stored apr    label 'Approved'               offered by the picker: True
  stored pndl   label 'Pending Lead'           offered by the picker: False
  stored None   label None                     offered by the picker: False
```

`rgb(204,204,204)` is the fallback, not a value the API returned: on the probed site `bg_color` is
null on 5 of 32 `Status` rows, `custom`, `na`, `pass`, `ready` and `recd` among them.

The rediscovery, from the same run of probe 038, every fetch made without an `Authorization` header:

```
GET /                                              200  16738 bytes   text/html
  stylesheets named in the page:
    /dist/production/stylesheets/css_reset.css?4eed9fe
    /dist/production/stylesheets/ext_all.css?4eed9fe
    /dist/production/stylesheets/login.css?4eed9fe
GET /dist/production/stylesheets/css_reset.css     200  10787 bytes   text/css
GET /dist/production/stylesheets/ext_all.css       200  62522 bytes   text/css
GET /dist/production/stylesheets/login.css         200  771416 bytes  text/css
  div.icon_apr {width: 12px; height: 11px;
                background: transparent url(/images/sg_icon_image_map.png?<32 hex chars>) -89px -11px no-repeat}
GET /images/sg_icon_image_map.png?<32 hex chars>   200  335561 bytes  image/png

23 distinct image_map_key over all 32 Status rows, 23 resolved to a rule, 0 unresolved
```

## Notes

### Two calls, not one per status

`Status.icon` is an entity link, so `?fields=icon` is returned under `relationships` as
`{"id": 2, "name": "Approved", "type": "Icon"}` and nothing else: no `display_type`, no
`image_map_key`, no `url`. A dotted path through it returns the `Icon` columns flattened into
`attributes` under the literal keys `icon.Icon.display_type` and so on, with `relationships` empty
(probe 003). One `_search` then answers for the whole picker.

| route | calls | on the probed site |
|---|---|---|
| `_search` with dotted `icon.Icon.*` | 1 | 14 statuses in 313ms |
| `_search` for `icon`, then `GET /entity/icons` and join on the link id | 2 | 308ms for the 98 icons |
| `GET /entity/statuses/<id>` per status | 1 per status | 5 rows in 1520ms |

The schema call for `valid_values` comes first either way, so the picker is two round trips.

### `Icon.url` is empty unless `image_data` is asked for beside it

The `image` rendering is the only one with a payload, and asking for the payload's field is what
returns it:

| requested | `url` |
|---|---|
| `?fields=display_type,url` | `""` |
| `?fields=url` | `""` |
| `?fields=display_type,url,image_data` | 994 chars |
| `?fields` omitted | 994 chars |
| dotted, `icon.Icon.image_data` in the list | 994 chars |
| dotted, `icon.Icon.image_data` left out | `""` |

An empty string reads as "this icon has no image", which is true of the other two renderings and
false here. Ask for `image_data` even when only `url` is wanted.

### The three renderings

| `display_type` | what the row holds | what to draw |
|---|---|---|
| `image_map` | `image_map_key`, such as `icon_apr`; `url` empty, `html` and `image_data` null | crop the sprite at the offset and size the CSS rule gives |
| `image` | `url`, a `data:image/png;base64` URI with newlines in it; `image_map_key` and `html` null | strip the newlines and use the URI as it stands |
| `html` | `html`, the badge text; `url` empty, `image_map_key` and `image_data` null | the text on `rgb(<bg_color>)`, no image |

`url` for the `image` case is exactly `"data:image/png;base64," + image_data`, newlines included, so
either field alone is enough. On the probed site the one custom upload is 994 chars with 16 newlines,
978 once stripped.

### Rediscover the sprite; never hardcode it

Nothing in `/entity/icons` names a stylesheet or an image. `image_map_key` is a CSS class, and the
rule for it gives the sheet, the offset and the size. Both the stylesheet href and the sprite href
end in a hash that changes per release, so a client fetches the site root, reads the `.css` hrefs off
it, and matches `.<image_map_key>` in what comes back. On the probed site the stylesheet is still the
`/dist/production/stylesheets/login.css` that probe 010 recorded, now served with `?4eed9fe`, and it
is one of three the root page names; the sprite href ends in 32 hex characters. Cache the
concatenated CSS: it is 771416 bytes there, against 10787 and 62522 for the other two sheets.

### Fall back to `bg_color`

A coloured badge with the label is a complete answer and needs no second request. `bg_color` is
comma-separated RGB (`"25,118,27"`), not hex, so it goes into `rgb(...)` rather than after a `#`. It
is also null on some rows, so keep a neutral of your own behind it. Take that path whenever the
stylesheet fetch fails, the rule is missing, or the client will not draw images at all.

### The picker is not a validator

`hidden_values` is not a subset of `valid_values`, and the API never enforces it: a hidden code
writes at 200 and reads back (`field_types/status_list`). Subtracting is right for offering a choice
and wrong for testing a row. On the probed site project 91 hides `awd`, `bid` and `to` on `Shot`, and
9 of its 32 Shots hold `to`. A cleared field reads `null` and fails the same membership test for a
different reason. Label a stored value off `display_values`, which covers the whole vocabulary, and
restrict only what a person may pick.

### The other pieces

- Read the schema per entity type. Codes do not transfer: on the probed site Version has 16 and Task
  10, overlapping on five, and `HumanUser` has `act` and `dis`, which no other type offers.
- `display_values` is a map from code to label and a key can be missing, so fall back to the code
  rather than dropping the option.
- `valid_values` order is the order to show. It is not alphabetical by label, and there is no
  substring operator on a `status_list` field, so a type-ahead filters the list client-side
  (`field_types/status_list`).
- `icon_type` has two values and no more. Over all 98 `Icon` rows on the probed site:
  `permanent_status`/`image_map` 94, `custom_status`/`html` 3, `custom_status`/`image` 1. Page 2 of
  the same listing returned 0 rows, so that census covers the whole table (probe 006). Probe 010 left
  the question open; the answer is site configuration, and a site with more custom statuses will hold
  more `custom_status` rows, not a third `icon_type`.
