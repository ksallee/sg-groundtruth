"""Q: how many Page and PageSetting rows does a script, an Admin and an Artist read, and does a person
read other people's per-user overrides?

A page runner acting for a person (sudo_as_login, probe 027) needs to know whether the page list and the
layouts narrow with the level, and whether one person's column order leaks to another. Site-wide, read
only. Subjects are discovered, never named: a login in committed source is site data.
"""
import collections

import _lib
import _pages as P
from sg_groundtruth.client import FPT

env = _lib.load_env()
c = _lib.client()
rows = []

cands = P.search(c, "human_users", [["can_impersonate_this_user", "is", True], ["sg_status_list", "is", "act"]],
                 ["login", "permission_rule_set"])
by_set = {}
for u in cands:
    name = (P.rel(u, "permission_rule_set") or {}).get("name")
    by_set.setdefault(name, (u["attributes"]["login"], u["id"]))
rows.append(f"=== impersonable active users by permission_rule_set: {sorted(k for k in by_set if k)}")
levels = [("script", None, None)]
for want in ("Admin", "Artist"):
    if want in by_set:
        levels.append((want, *by_set[want]))
if not any(lv[0] == "Artist" for lv in levels):
    other = next((k for k in sorted(by_set, key=str) if k not in ("Admin", None)), None)
    if other:
        levels.append((other, *by_set[other]))

writers = {}
for label, login, uid in levels:
    cl = c if login is None else FPT.from_env(env, sudo_as_login=login)
    try:
        pages = P.search(cl, "pages", [], ["project", "shared", "page_type", "ui_category", "created_by"])
    except SystemExit as e:
        rows.append(f"  {label}: pages refused {e}")
        continue
    ids = {p["id"] for p in pages}
    try:
        st = P.settings(cl, ids, fields=("page", "user"))
        err = ""
    except SystemExit as e:
        st, err = [], str(e)
    shared = sum(1 for x in st if P.rel(x, "user") is None)
    users = collections.Counter("own" if uid and P.rel(x, "user") and P.rel(x, "user")["id"] == uid else "another's"
                                for x in st if P.rel(x, "user"))
    see = collections.Counter(p["attributes"].get("shared") for p in pages)
    proj = sum(1 for p in pages if P.rel(p, "project"))
    rows.append(f"  {label:<7} pages {len(pages):>5} (project {proj}, site {len(pages) - proj})  "
                f"shared {dict(see)}")
    rows.append(f"          PageSetting on those pages {len(st):>5}: shared {shared}, per-user {dict(users)} {err}")
    writers[label] = {p["id"]: p for p in pages}
    # One field, not the others, fails the whole page of results for some callers.
    fails = []
    for n in range(1, len(pages) // 500 + 2):
        r = cl.post("/entity/pages/_search", headers=P.ARR,
                    json={"filters": [], "fields": ["current_user_can_see"], "page": {"size": 500, "number": n}})
        if not r.ok:
            fails.append(f"page {n}: {r.status_code} {r.json()['errors'][0]}")
    rows.append(f"          fields=current_user_can_see, pages of 500: {fails or 'all 200'}")

rows.append("\n=== pages the script lists that a level does not")
base = writers.get("script", {})
for label, got in writers.items():
    if label == "script":
        continue
    extra = [got[i] for i in set(got) - set(base)]
    rows.append(f"  {label}: missing {len(set(base) - set(got))}, extra {len(extra)}")
    if extra:
        rows.append(f"    extra by shared {dict(collections.Counter(p['attributes']['shared'] for p in extra))}, "
                    f"ui_category {dict(collections.Counter(p['attributes']['ui_category'] for p in extra))}")
        rows.append(f"    extra by page_type {dict(collections.Counter(p['attributes']['page_type'] for p in extra).most_common(6))}")
        own = collections.Counter("created by this user" if (P.rel(p, "created_by") or {}).get("id") == lv_id
                                  else "created by another" for p in extra
                                  for lv_id in [next(lv[2] for lv in levels if lv[0] == label)])
        rows.append(f"    extra by author {dict(own)}")
        st = P.settings(c, [p["id"] for p in extra], fields=("page", "user"))
        rows.append(f"    the script reads PageSetting for {len({P.rel(x, 'page')['id'] for x in st if P.rel(x, 'page')})} "
                    f"of those {len(extra)} pages by id")
        r = c.get(f"/entity/pages/{extra[0]['id']}", params={"fields": "name"})
        rows.append(f"    GET /entity/pages/<an extra id> as the script -> {r.status_code}")

rows.append("\n=== another user's override, fetched by id as the lower level")
lower = next((lv for lv in levels if lv[0] not in ("script", "Admin")), None)
if lower:
    theirs = P.search(c, "page_settings", [["user", "is_not", None],
                                            ["user", "is_not", {"type": "HumanUser", "id": lower[2]}]],
                      ["page", "user"], size=5)[:1]
    if theirs:
        cl = FPT.from_env(env, sudo_as_login=lower[1])
        r = cl.get(f"/entity/page_settings/{theirs[0]['id']}", params={"fields": "user,settings_json"})
        body = r.json()
        rows.append(f"  GET /entity/page_settings/<another user's row> as {lower[0]} -> {r.status_code} "
                    + (f"settings_json {type(body['data']['attributes'].get('settings_json')).__name__}"
                       if r.ok else str(body.get("errors"))))
        r = cl.post("/entity/page_settings/_search", headers=P.ARR,
                    json={"filters": [["user", "is_not", None]], "fields": ["user"], "page": {"size": 500}})
        n = len(r.json().get("data", [])) if r.ok else r.text
        rows.append(f"  _search user is_not null as {lower[0]} -> {r.status_code}, {n} rows")
else:
    rows.append("  no impersonable user below Admin on this site; not measured")

_lib.emit("076_page_visibility", "\n".join(rows), env)
