"""Q: what does a client need to offer a project's statuses to a person, each with its icon and colour?

Three entries hold the pieces and none of them holds the sequence. 009 has the subtraction that makes
a project's usable set, `field_types/status_list` has the caveat that the subtraction is wrong for
testing a row, and 010 has the icon under `relationships` and the three `display_type` renderings. This
probe joins them: the usable set, one call that carries the icon with the status, a branch per
rendering, and the sprite rediscovered from the site's own stylesheet rather than hardcoded.

It also settles the two questions 010 left open: whether `icon_type` has values beyond
`permanent_status` and `custom_status`, and whether the stylesheet is still where 010 found it.
"""
import re
import time

import requests

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []

SLUG = {"Version": "versions", "Task": "tasks", "Shot": "shots", "Asset": "assets"}
# `url` reads as an empty string unless `image_data` is asked for in the same call; section 2.
ICON_FIELDS = ("display_type", "image_map_key", "html", "url", "image_data")
FIELDS = "code,name,bg_color," + ",".join(f"icon.Icon.{f}" for f in ICON_FIELDS)
SAMPLES = _lib.sample_projects(c, env)
PROJECT = SAMPLES[0]


def blob(s):
    """Never paste a base64 blob (`field_types/image`): a prefix and a length say as much."""
    return f"{s[:32]}...({len(s)} chars, {s.count(chr(10))} newlines)" if s else repr(s)


def usable(entity_type, field, project_id):
    p = c.get(f"/schema/{entity_type}/fields/{field}",
              params={"project_id": project_id}).json()["data"]["properties"]
    valid, hidden = p["valid_values"]["value"], p["hidden_values"]["value"]
    return valid, hidden, [v for v in valid if v not in hidden], p["display_values"]["value"]


# ---------------------------------------------------------------- 1. the usable set
rows.append("=== 1. valid_values minus hidden_values, per project and per entity type (009)")
for pid in SAMPLES[:3]:
    for et in ("Version", "Task", "Shot"):
        valid, hidden, use, _ = usable(et, "sg_status_list", pid)
        extra = [h for h in hidden if h not in valid]
        rows.append(f"  project {pid} {et:<8} valid={len(valid):<3} hidden={len(hidden)} "
                    f"-> usable={len(use)}   hidden_values not in valid_values: {extra}")
valid, hidden, USE, DISPLAY = usable("Version", "sg_status_list", PROJECT)
rows.append(f"  project {PROJECT} Version hidden={hidden}")
rows.append(f"  usable ({len(USE)}): {USE}")
rows.append(f"  labels from display_values, missing keys fall back to the code: "
            f"{[DISPLAY.get(v, v) for v in USE][:6]} ...")

# ---------------------------------------------------------------- 2. one call, or one per status?
rows.append("\n=== 2. how many calls carry the icon along with the status")
t = time.time()
r = c.post("/entity/statuses/_search", headers=ARR,
           json={"filters": [["code", "in", USE]], "fields": FIELDS, "page": {"size": 200}})
one_call = r.json()["data"] if r.ok else []
rows.append(f"  POST /entity/statuses/_search  ['code','in',<the usable codes>] with dotted icon "
            f"fields -> {r.status_code}, {len(one_call)} rows in {int((time.time() - t) * 1000)}ms")
_lib.note_from(r.json())
got = {x["attributes"]["code"] for x in one_call}
rows.append(f"  usable codes with no Status row: {sorted(set(USE) - got) or 'none'}")
sample = one_call[0]
rows.append(f"  attributes keys: {sorted(sample['attributes'])}")
rows.append(f"  relationships keys: {sorted(sample.get('relationships') or {})}  "
            f"(a dotted read is flattened into attributes, so the link is not returned)")

r2 = c.post("/entity/statuses/_search", headers=ARR,
            json={"filters": [["code", "in", USE]], "fields": "code,bg_color,icon"})
und = r2.json()["data"][0]
rows.append(f"  the same asking for `icon` undotted -> {r2.status_code}, "
            f"relationships.icon.data = {und['relationships']['icon']['data']}")
rows.append("    an entity link and nothing else. display_type, image_map_key, html and url are "
            "absent, so the undotted read costs a second call over /entity/icons")

t = time.time()
ic = c.get("/entity/icons", params={"fields": ",".join(ICON_FIELDS) + ",icon_type",
                                    "page[size]": 500})
rows.append(f"  the two-call alternative: that _search, then GET /entity/icons -> {ic.status_code}, "
            f"{len(ic.json()['data'])} icons in {int((time.time() - t) * 1000)}ms, joined on the id")
t = time.time()
for x in one_call[:5]:
    c.get(f"/entity/statuses/{x['id']}", params={"fields": FIELDS})
rows.append(f"  one GET per status, for comparison: 5 rows in {int((time.time() - t) * 1000)}ms")

rows.append("\n  Icon.url is an empty string unless image_data is asked for in the same call")
IMAGE_CODE = next(x["attributes"]["code"] for x in one_call
                  if x["attributes"]["icon.Icon.display_type"] == "image")
ICON_ID = next(x["relationships"]["icon"]["data"]["id"] for x in r2.json()["data"]
               if x["attributes"]["code"] == IMAGE_CODE)
for f in ("display_type,url", "url", "display_type,url,image_data", None):
    a = c.get(f"/entity/icons/{ICON_ID}",
              params={"fields": f} if f else {}).json()["data"]["attributes"]
    rows.append(f"    GET /entity/icons/<id>?fields={f or '<omitted>':<28} url {blob(a.get('url'))}")
for f in (FIELDS, FIELDS.replace(",icon.Icon.image_data", "")):
    d = c.get("/entity/statuses", params={"fields": f, "page[size]": 200}).json()["data"]
    a = next(x["attributes"] for x in d if x["attributes"]["code"] == IMAGE_CODE)
    rows.append(f"    dotted, image_data {'asked for' if 'image_data' in f else 'omitted  '}"
                f"          icon.Icon.url {blob(a['icon.Icon.url'])}")

# ---------------------------------------------------------------- 3. the sprite, rediscovered
rows.append("\n=== 3. rediscovering the sprite from the site's own stylesheet (010)")
root = requests.get(c.site, timeout=30)
sheets = re.findall(r'href=["\']([^"\']+\.css[^"\']*)["\']', root.text, re.I)
rows.append(f"  unauthenticated GET /              -> {root.status_code}  {len(root.content)} bytes  "
            f"{root.headers.get('content-type')}")
rows.append(f"  stylesheets named in the page: {sheets}")
rows.append("    010 recorded /dist/production/stylesheets/login.css; still named: "
            f"{any('login.css' in s for s in sheets)}")
css = ""
for href in sheets:
    s = requests.get(f"{c.site}{href}", timeout=60)
    rows.append(f"  unauthenticated GET {href.split('?')[0]:<45} -> {s.status_code}  "
                f"{len(s.content)} bytes  {s.headers.get('content-type')}")
    if s.ok:
        css += s.text


def sprite_for(key):
    m = re.search(r"\.%s\b[^{}]*\{([^{}]*)\}" % re.escape(key), css)
    if not m:
        return None
    decl = m.group(1)
    href = re.search(r"url\(\s*['\"]?([^'\")]+)", decl)
    off = re.search(r"(-?\d+)px\s+(-?\d+)px", decl)
    size = re.search(r"width:\s*(\d+)px.*?height:\s*(\d+)px", decl, re.S)
    return {"url": href.group(1) if href else None,
            "offset": (int(off.group(1)), int(off.group(2))) if off else None,
            "size": (int(size.group(1)), int(size.group(2))) if size else None}


ALL = c.get("/entity/statuses", params={"fields": FIELDS, "page[size]": 200}).json()["data"]
_lib.note_from({"data": ALL})
keys = sorted({x["attributes"]["icon.Icon.image_map_key"] for x in ALL
               if x["attributes"]["icon.Icon.display_type"] == "image_map"})
resolved = {k: sprite_for(k) for k in keys}
rows.append(f"  {len(keys)} distinct image_map_key over all {len(ALL)} Status rows, "
            f"{sum(1 for v in resolved.values() if v)} resolved to a rule")
for k in keys[:4]:
    v = resolved[k]
    rows.append(f"    {k:<20} {v['size'][0]}x{v['size'][1]} at {v['offset']}  {v['url']}")
rows.append(f"  unresolved keys: {[k for k, v in resolved.items() if not v] or 'none'}")
href = next(v["url"] for v in resolved.values() if v and v["url"])
png = requests.get(f"{c.site}{href}", timeout=60)
rows.append(f"  unauthenticated GET the sprite -> {png.status_code}  {len(png.content)} bytes  "
            f"{png.headers.get('content-type')}")
rows.append(f"  the query on that href is a release hash: {href.split('?')[1][:8]}... "
            f"({len(href.split('?')[1])} chars); the stylesheet carries its own, "
            f"{sheets[0].split('?')[1]}")

# ---------------------------------------------------------------- 4. one branch per display_type
rows.append("\n=== 4. the three renderings")


def branches(statuses, label):
    seen = {}
    for x in statuses:
        seen.setdefault(x["attributes"]["icon.Icon.display_type"], []).append(x["attributes"])
    rows.append(f"  {label}: " + ", ".join(f"{k} n={len(v)}" for k, v in sorted(seen.items())))
    return seen


branches(one_call, f"project {PROJECT} Version, {len(one_call)} usable statuses")
seen = branches(ALL, "every Status row on the site")
for dt, items in sorted(seen.items()):
    a = items[0]
    rows.append(f"\n  {dt}  codes {[i['code'] for i in items][:6]}")
    rows.append(f"    bg_color {a['bg_color']!r}  image_map_key {a['icon.Icon.image_map_key']!r}  "
                f"html {a['icon.Icon.html']!r}")
    rows.append(f"    url {blob(a['icon.Icon.url'])}  image_data {blob(a['icon.Icon.image_data'])}")
    if dt == "image_map":
        v = resolved[a["icon.Icon.image_map_key"]]
        rows.append(f"    -> crop {v['url'].split('?')[0]} at {v['offset']}, "
                    f"{v['size'][0]}x{v['size'][1]}")
    elif dt == "image":
        rows.append(f"    -> the same URI with newlines stripped: "
                    f"{blob(a['icon.Icon.url'].replace(chr(10), ''))}")
        rows.append(f"       url == 'data:image/png;base64,' + image_data: "
                    f"{a['icon.Icon.url'] == 'data:image/png;base64,' + a['icon.Icon.image_data']}")
    else:
        rows.append(f"    -> a text badge reading {a['icon.Icon.html']!r} on rgb({a['bg_color']})")

colours = {x["attributes"]["code"]: x["attributes"]["bg_color"] for x in ALL}
rows.append(f"\n  bg_color, comma-separated RGB: "
            f"{sorted(str(v) for v in set(colours.values()) if v)[:5]}")
rows.append(f"  bg_color null on {len([v for v in colours.values() if not v])} of {len(colours)} "
            f"Status rows: {sorted(k for k, v in colours.items() if not v)}")

# ---------------------------------------------------------------- 5. icon_type, the open question
rows.append("\n=== 5. icon_type and display_type over every Icon row (010 asked)")
icons = ic.json()["data"]
census = {}
for x in icons:
    a = x["attributes"]
    census.setdefault((a["icon_type"], a["display_type"]), []).append(a)
rows.append(f"  GET /entity/icons page[size]=500 -> {len(icons)} rows")
for (it, dt), items in sorted(census.items(), key=lambda kv: str(kv[0])):
    rows.append(f"    {str(it):<18} / {str(dt):<10} n={len(items)}")
rows.append(f"  distinct icon_type:    {sorted({str(x['attributes']['icon_type']) for x in icons})}")
rows.append(f"  distinct display_type: {sorted({str(x['attributes']['display_type']) for x in icons})}")
nxt = c.get("/entity/icons", params={"fields": "icon_type", "page[size]": 500, "page[number]": 2})
rows.append(f"  page 2 -> {nxt.status_code}, {len(nxt.json()['data'])} rows, so the census covers "
            f"the whole table (probe 006)")

# ---------------------------------------------------------------- 6. the caveat the subtraction hides
rows.append("\n=== 6. a row may hold a code outside the usable set (field_types/status_list)")
for pid in SAMPLES:
    for et in ("Version", "Task", "Shot", "Asset"):
        _, hid, use, _ = usable(et, "sg_status_list", pid)
        r = c.post(f"/entity/{SLUG[et]}/_search", headers=ARR, json={
            "filters": [["project", "is", {"type": "Project", "id": pid}]],
            "fields": "sg_status_list", "page": {"size": 500}})
        if not r.ok:
            continue
        held = {}
        for row in r.json()["data"]:
            v = row["attributes"]["sg_status_list"]
            held[v] = held.get(v, 0) + 1
        out = {k: v for k, v in held.items() if k not in use}
        if out:
            rows.append(f"  project {pid} {et:<8} hides {hid}; {sum(out.values())} of "
                        f"{sum(held.values())} rows hold {out}")
rows.append("  None is a cleared field, not a hidden code; both fail a `code in usable` test")

_lib.emit("038_status_picker", "\n".join(rows), env)
