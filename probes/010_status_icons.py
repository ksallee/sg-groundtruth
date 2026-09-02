"""Q: how are status colours and icons resolved, and do standard and custom icons differ?"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

sfields = sorted(c.get("/schema/Status/fields").json()["data"])
rows.append(f"Status fields: {sfields}")
rows.append(f"Status.icon data_type: "
            f"{c.get('/schema/Status/fields/icon').json()['data']['data_type']['value']}")

st = c.get("/entity/statuses", params={"fields": "code,name,bg_color,system,icon", "page[size]": 100}).json()
_lib.register_from(st)
withicon = [x for x in st["data"] if (x.get("relationships", {}).get("icon") or {}).get("data")]
rows.append(f"\nstatuses: {len(st['data'])}, with an icon relationship: {len(withicon)}")
rows.append(f"sample bg_color: {json.dumps([x['attributes'].get('bg_color') for x in st['data'][:4]])}")

ifields = sorted(c.get("/schema/Icon/fields").json()["data"])
rows.append(f"\nIcon fields: {ifields}")
icons = c.get("/entity/icons", params={"fields": ",".join(ifields), "page[size]": 200}).json()
_lib.register_from(icons)

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

actual = "\n".join(rows)
_lib.record(
    "010_status_icons", "GET /entity/statuses?fields=...,icon ; GET /entity/icons",
    "Status colour and icon come from the Status entity; standard and custom icons resolve differently.",
    actual,
    "Status.icon is an ENTITY link, so it arrives under relationships, not attributes - reading attributes "
    "alone makes every icon look null. Icons resolve three ways by display_type: 'image_map' (94 standard, "
    "url empty, addressed by image_map_key like 'icon_apr' - a sprite, and its location is NOT guessable at "
    "/images/*, still unresolved); 'image' (custom upload - url is a self-contained data:image/png;base64 URI, "
    "with newlines that must be stripped, and image_data holds the same bytes); 'html' (custom text badge - "
    "html holds the label, no image at all). bg_color is comma-separated RGB, not hex, and is enough to render "
    "a badge without any icon.",
    env, tags=("status", "icon", "cache", "colour", "entity-field"))
print(actual)
