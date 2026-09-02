"""Q: how are status colours and icons resolved, and do standard and custom icons differ?"""
import json
import re

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

sfields = sorted(c.get("/schema/Status/fields").json()["data"])
rows.append(f"Status fields: {sfields}")
rows.append(f"Status.icon data_type: "
            f"{c.get('/schema/Status/fields/icon').json()['data']['data_type']['value']}")

st = c.get("/entity/statuses", params={"fields": "code,name,bg_color,system,icon", "page[size]": 100}).json()
_lib.note_from(st)
withicon = [x for x in st["data"] if (x.get("relationships", {}).get("icon") or {}).get("data")]
rows.append(f"\nstatuses: {len(st['data'])}, with an icon relationship: {len(withicon)}")
rows.append(f"sample bg_color: {json.dumps([x['attributes'].get('bg_color') for x in st['data'][:4]])}")

ifields = sorted(c.get("/schema/Icon/fields").json()["data"])
rows.append(f"\nIcon fields: {ifields}")
icons = c.get("/entity/icons", params={"fields": ",".join(ifields), "page[size]": 200}).json()
_lib.note_from(icons)

groups = {}
for x in icons["data"]:
    a = x["attributes"]
    groups.setdefault((a.get("icon_type"), a.get("display_type")), []).append(a)

rows.append(f"\n{len(icons['data'])} icons, grouped by (icon_type, display_type):")
for (it, dt), items in sorted(groups.items(), key=lambda kv: str(kv[0])):
    a = items[0]
    url = (a.get("url") or "").replace("\n", "")
    url_desc = f"{url[:58]}...({len(url)} chars)" if url else "empty string"
    idata = a.get("image_data")
    data_desc = f"base64 str, {len(idata)} chars" if isinstance(idata, str) else "null"
    rows.append(
        f"\n  {it} / {dt}  n={len(items)}\n"
        f"    url            {url_desc}\n"
        f"    image_map_key  {json.dumps(a.get('image_map_key'))}\n"
        f"    html           {json.dumps(a.get('html'))[:60]}\n"
        f"    image_data     {data_desc}")

# The sprite is not in the API. Rediscover it the way a client has to: read the web app's own
# stylesheet and follow the rule for an image_map_key. No auth header on either fetch.
CSS = "/dist/production/stylesheets/login.css"
css = requests.get(f"{c.site}{CSS}", timeout=30)
rows.append(f"\nunauthenticated GET {CSS} -> {css.status_code}  {len(css.content)} bytes  "
            f"content-type: {css.headers.get('content-type')}")
rule = re.search(r"[^{}]*\.icon_apr[^{}]*\{[^{}]*\}", css.text) if css.ok else None
rows.append(f"  rule for image_map_key 'icon_apr': {rule.group(0).strip() if rule else '<not found>'}")
sprite = re.search(r"url\(([^)]*sg_icon_image_map[^)]*)\)", css.text) if css.ok else None
if sprite:
    href = sprite.group(1).strip("'\"")
    png = requests.get(f"{c.site}{href}" if href.startswith("/") else href, timeout=30)
    rows.append(f"  sprite href in the stylesheet: {href}")
    rows.append(f"unauthenticated GET the sprite -> {png.status_code}  {len(png.content)} bytes  "
                f"content-type: {png.headers.get('content-type')}")
else:
    rows.append("  no sg_icon_image_map url() in the stylesheet")

actual = "\n".join(rows)
_lib.emit("010_status_icons", actual, env)
