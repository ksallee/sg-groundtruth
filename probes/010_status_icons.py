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

actual = "\n".join(rows)
_lib.emit("010_status_icons", actual, env)
