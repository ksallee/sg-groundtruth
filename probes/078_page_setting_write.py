"""Q: can a script create a Page, write its shared settings_json and read it back identical, and can it
write a person's override on that page?

Page+ would save a layout it built. Everything here happens on a page this probe creates in the sandbox
project and deletes on exit; no existing page is touched. Needs --write.

**This probe cannot leave no trace.** DELETE on a PageSetting is 400 `Entity type PageSetting doesn't
respond to retirement`, and creating a Page makes one. Each --write run leaves that row behind with
`page` reading null and `settings_json` cleared to null, and prints its id. The rows that answer "can a
second shared row or a person's override be created" are one more permanent row each, so they run only
with --litter as well.
"""
import copy
import json

import _lib
import _pages as P
from sg_groundtruth.client import FPT

env = _lib.load_env()
c = _lib.client()
SANDBOX = _lib.sandbox_id(c, env)
PROJ = {"type": "Project", "id": SANDBOX}
rows = []

if not _lib.writes_allowed():
    raise SystemExit("078 writes a Page in the sandbox project: rerun with --write")


def err(r):
    e = r.json().get("errors", [{}])[0]
    t = e.get("title") or ""
    # A settings_json refusal echoes the whole value sent back, tens of kilobytes: keep its head.
    if len(t) > 300:
        e = dict(e, title=f"{t[:220]}... ({len(t)} chars, the rest echoes the value sent)")
    return json.dumps(e)


# A real Shot page's shared tree is the template, so the write carries every key a page holds.
src = P.search(c, "pages", [["project", "is", PROJ], ["page_type", "is", "canvas"], ["entity_type", "is", "Shot"]],
               ["name"], size=5) or P.search(c, "pages", [["page_type", "is", "canvas"], ["entity_type", "is", "Shot"]],
                                             ["name"], size=5)
tree = P.shared(P.settings(c, [src[0]["id"]]))[src[0]["id"]]
tree = copy.deepcopy(tree)
body = tree["children"]["body"]
body["settings"]["filters"] = {"logical_operator": "and", "conditions": [
    {"path": "project", "relation": "is", "active": "true", "values": [{"type": "Project", "id": SANDBOX, "valid": "valid"}]}]}
tree["children"]["body"]["children"]["list_content"]["settings"]["columns"] = ["code", "sg_status_list", "description"]
rows.append(f"=== template: a Shot canvas page's shared tree, {len(json.dumps(tree))} chars, "
            f"{sum(1 for _ in P.walk(tree))} widgets")

login = (env.get("FPT_USER_LOGIN") or "").strip()
if not login:
    raise SystemExit("set FPT_USER_LOGIN in .env.local: a script cannot create a Page, a person can")
pc = FPT.from_env(env, sudo_as_login=login)
who = c.get("/entity/human_users", params={"filter[login]": login, "fields": "id"}).json()["data"]
person = {"type": "HumanUser", "id": who[0]["id"]}


def read_tree(cl, sid):
    r = cl.get(f"/entity/page_settings/{sid}", params={"fields": "settings_json,user,page"})
    return r.status_code, (r.json()["data"] if r.ok else None)


LITTER = "--litter" in __import__("sys").argv
permanent = []   # PageSetting ids: DELETE cannot remove them, so they are cleared instead

# The person owns the Page and deletes it; the script deletes what the script made. Outer exits last.
with _lib.Created(pc) as by_person, _lib.Created(c) as made:
    rows.append("\n=== create the Page")
    attempts = (("script", c, "name only", {"name": "zzprobe_078_page", "project": PROJ}),
                ("script", c, "with entity_type", {"name": "zzprobe_078_page", "project": PROJ, "entity_type": "Shot"}),
                ("script", c, "with page_type", {"name": "zzprobe_078_page", "project": PROJ,
                                                 "page_type": "canvas", "entity_type": "Shot"}),
                ("person", pc, "with entity_type", {"name": "zzprobe_078_page", "project": PROJ, "entity_type": "Shot"}))
    page_id = None
    for who_, cl, label, payload in attempts:
        r = cl.post("/entity/pages", json=payload)
        rows.append(f"  POST /entity/pages as the {who_}, {label} -> {r.status_code} "
                    + (f"created" if r.ok else err(r)))
        if r.ok:
            page_id = r.json()["data"]["id"]
            (made if cl is c else by_person).add("pages", page_id)
    if page_id:
        for who_, cl in (("script", c), ("person", pc)):
            got = cl.get(f"/entity/pages/{page_id}", params={"fields": ",".join(P.PAGE_FIELDS + ["created_by"])})
            if not got.ok:
                rows.append(f"  GET the new Page as the {who_} -> {got.status_code}")
                continue
            a = got.json()["data"]["attributes"]
            rows.append(f"  GET as the {who_} -> 200: page_type {a['page_type']!r} entity_type {a['entity_type']!r} "
                        f"ui_category {a['ui_category']!r} shared {a['shared']} system_owned {a['system_owned']}")
        auto = P.settings(pc, [page_id])
        permanent += [x["id"] for x in auto]
        rows.append(f"  PageSetting rows the server made with it (read as the person): {len(auto)}, "
                    f"user {[P.rel(x, 'user') and 'set' for x in auto]}")
        for x in auto:
            t = x["attributes"]["settings_json"]
            rows.append(f"    widgets {sum(1 for _ in P.walk(t))}; body type {t.get('children', {}).get('body', {}).get('type')}; "
                        f"columns {t.get('children', {}).get('body', {}).get('children', {}).get('list_content', {}).get('settings', {}).get('columns')}")
        rows.append(f"  the script reads those rows: {len(P.settings(c, [page_id]))}")

        rows.append("\n=== replace the shared tree, as the script, on the probe's own page")
        ref = {"type": "Page", "id": page_id}
        shared_id = next((x["id"] for x in auto if P.rel(x, "user") is None), None)
        if shared_id:
            r = c.put(f"/entity/page_settings/{shared_id}", json={"settings_json": tree})
            st, back = read_tree(c, shared_id)
            rows.append(f"  PUT settings_json (an object) -> {r.status_code} {'' if r.ok else err(r)}; "
                        f"read back {st}, identical: {back is not None and back['attributes']['settings_json'] == tree}")
            new = copy.deepcopy(tree)
            new["children"]["body"]["children"]["list_content"]["settings"]["columns"] = ["code", "description"]
            r = c.put(f"/entity/page_settings/{shared_id}", json={"settings_json": json.dumps(new)})
            st, back = read_tree(c, shared_id)
            v = back["attributes"]["settings_json"] if back else None
            rows.append(f"  PUT settings_json (a JSON string) -> {r.status_code}; read back {type(v).__name__}, "
                        f"identical to the object: {v == new}")
            r = c.put(f"/entity/page_settings/{shared_id}", json={"settings_json": json.dumps({"not": "a widget tree"})})
            st, back = read_tree(c, shared_id)
            rows.append(f"  PUT a tree with no type or children -> {r.status_code}; read back "
                        f"{json.dumps(back['attributes']['settings_json'])[:60] if back else st}")
            r = c.put(f"/entity/page_settings/{shared_id}", json={"settings_json": json.dumps(tree)})
            st, back = read_tree(pc, shared_id)
            rows.append(f"  restored; the person reads it identical: {back is not None and back['attributes']['settings_json'] == tree}")

        rows.append("\n=== a second shared row, and a person's override (--litter)")
        if not LITTER:
            rows.append("  not attempted: each is a permanent row; rerun with --write --litter")
        else:
            r = c.post("/entity/page_settings", json={"page": ref, "settings_json": json.dumps(tree)})
            rows.append(f"  POST a second shared row as the script, a JSON string -> {r.status_code} {'' if r.ok else err(r)}")
            if r.ok:
                permanent.append(r.json()["data"]["id"])
                rows.append(f"    shared rows on the page now: "
                            f"{sum(1 for x in P.settings(pc, [page_id]) if P.rel(x, 'user') is None)}")
            patch = [{"spec_path": "body|list_content", "settings": {"columns": ["description", "code"]}}]
            for who_, cl in (("script", c), ("person", pc)):
                r = cl.post("/entity/page_settings", json={"page": ref, "user": person, "settings_json": json.dumps(patch)})
                rows.append(f"  POST user=<person>, a patch array as a JSON string, as the {who_} -> {r.status_code} {'' if r.ok else err(r)}")
                if r.ok:
                    oid = r.json()["data"]["id"]
                    permanent.append(oid)
                    st, back = read_tree(pc, oid)
                    rows.append(f"    the person reads it back identical: {back is not None and back['attributes']['settings_json'] == patch}")
            rows.append("  what the web interface draws for that person: not measured, needs a person at a browser")

    rows.append("\n=== leaving")
if permanent:
    r = c.delete(f"/entity/page_settings/{permanent[0]}")
    rows.append(f"  DELETE /entity/page_settings/<id> -> {r.status_code} {err(r) if not r.ok else ''}")
    for i in permanent:
        c.put(f"/entity/page_settings/{i}", json={"settings_json": None})
    left = [c.get(f"/entity/page_settings/{i}", params={"fields": "page,settings_json"}).json()["data"] for i in permanent]
    rows.append(f"  left behind, cleared: {len(left)} PageSetting rows, page "
                f"{[P.rel(x, 'page') for x in left]}, settings_json {[x['attributes']['settings_json'] for x in left]}")
    print(f"  PageSetting rows left by this run (cannot be deleted): {permanent}")

_lib.emit("078_page_setting_write", "\n".join(rows), env)
