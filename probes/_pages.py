"""Page plumbing shared by probes 072-078: list the pages, fetch their PageSetting rows, walk a tree.

A PageSetting can name a Page the listing no longer returns (a retired page reads `page` null under
`relationships` while still passing `page is_not null`), so every tally here starts from the listed
pages and fetches settings by `page in [...]`, never by scanning PageSetting.
"""
import re

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HASH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
PAGE_FIELDS = ["name", "page_type", "entity_type", "ui_category", "project", "system_owned", "shared"]
QUERY = "SG.Widget.EntityQuery.EntityQueryPage"


def search(c, slug, filters, fields, size=500, headers=ARR):
    out, n = [], 1
    while True:
        r = c.post(f"/entity/{slug}/_search", headers=headers,
                   json={"filters": filters, "fields": fields, "page": {"size": size, "number": n}})
        if not r.ok:
            raise SystemExit(f"{slug} _search {r.status_code} {r.text}")   # never truncate
        d = r.json()["data"]
        if not d:
            return out
        out += d
        n += 1


def rel(row, name):
    return (row["relationships"].get(name) or {}).get("data")


def pages(c, filters=None):
    return search(c, "pages", filters or [], PAGE_FIELDS)


def settings(c, page_ids, fields=("page", "user", "settings_json"), chunk=200):
    out = []
    ids = list(page_ids)
    for i in range(0, len(ids), chunk):
        ref = [{"type": "Page", "id": x} for x in ids[i:i + chunk]]
        out += search(c, "page_settings", [["page", "in", ref]], list(fields))
    return out


def shared(rows):
    """page id -> the settings_json of its shared row (user null). Last row wins where a page has two."""
    return {rel(x, "page")["id"]: x["attributes"]["settings_json"]
            for x in rows if rel(x, "page") and rel(x, "user") is None}


def walk(node, path=""):
    """Yield (path, widget) for every `{type, settings, children}` node, depth first."""
    if isinstance(node, dict) and "type" in node:
        yield path or "/", node
        for k, v in (node.get("children") or {}).items():
            yield from walk(v, f"{path}/{k}")


def shape(path):
    """A path with its per-page indices folded, so /layout_1/row_2/child_9 tallies with its siblings."""
    return re.sub(r"(tab|layout|row|child)_\d+", r"\1_N", path)


def leaves(tree):
    if isinstance(tree, dict) and "conditions" in tree:
        for x in tree["conditions"]:
            yield from leaves(x)
    elif isinstance(tree, dict):
        yield tree
