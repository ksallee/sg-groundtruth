"""Q: what does creating an ActionMenuItem by API take, which of its fields hold what was sent, who may
create one, and what does the web interface send to its URL when a person runs it?

sg-onset wants an entry in a Shot's right-click menu that opens the app on that Shot.
`field_types/entity_type` measured `ActionMenuItem.entity_type`; nothing measured the rest of the row.

Steps, writes only behind `--write`, every row scoped to the sandbox project where the field allows:

1. creates with growing bodies: `{}`, `title`, `title` + `url`, + `entity_type`
2. one row with every editable field set, read back
3. edge values: a custom-protocol `url`, an `entity_type` that is no type, a `list` value outside
   `valid_values`
4. as an Admin and as an Artist (`sudo_as_login`, `_people`): create one, and read three rows
   restricted by `permissions_groups` to admin, to artist, and to nobody

`--listen <port> --hold <seconds>` also starts a recorder on `http://localhost:<port>`, creates two
rows pointing at it on Shot (form and json payload), and waits: a person signed in to the web
interface right-clicks a Shot in the sandbox project and runs each. Every request is printed whole.
The rows are deleted on exit.

    python probes/156_action_menu_item.py --write [--listen 8765 --hold 900]
"""
import http.server
import json
import sys
import threading
import time

import _lib
import _people
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 156 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
ME, LOGIN, aliases = _people.operator_and_aliases(c, env, SB, need=1)
ARTIST = next((a for a in aliases if a[2] == "Artist"), None)
LISTEN = int(sys.argv[sys.argv.index("--listen") + 1]) if "--listen" in sys.argv else 0
HOLD = int(sys.argv[sys.argv.index("--hold") + 1]) if "--hold" in sys.argv else 600
FIELDS = ("title,url,entity_type,list_order,selection_required,folder,projects,permissions_groups,"
          "payload_content_type,light_payload,open_in_overlay,poll_for_data_updates,add_btn_behavior,"
          "secret_token,signature_algorithm,created_by")
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def said(r):
    if r.ok:
        return str(r.status_code)
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} code {e.get('code')} {e.get('title')!r} source {json.dumps(e.get('source'))}"
    except (ValueError, KeyError, IndexError):
        return f"{r.status_code} {r.text}"


def readback(rid):
    d = c.get(f"/entity/action_menu_items/{rid}", params={"fields": FIELDS}).json()["data"]
    v = dict(d["attributes"])
    for k, rel in d["relationships"].items():
        x = rel.get("data")
        v[k] = [(y["type"], y.get("name") if y["type"] == "PermissionRuleSet" else "sandbox" if y["id"] == SB else y["id"])
                for y in x] if isinstance(x, list) else (x or {}).get("type")
    return v


prs = {r["attributes"]["code"]: {"type": "PermissionRuleSet", "id": r["id"]} for r in c.post(
    "/entity/permission_rule_sets/_search", headers=ARR, json={
        "filters": [["entity_type", "is", "HumanUser"]], "fields": ["code"]}).json()["data"]}


class Recorder(http.server.BaseHTTPRequestHandler):
    def _log(self):
        n = int(self.headers.get("Content-Length") or 0)
        body = self.rfile.read(n).decode(errors="replace") if n else ""
        keep = {k: v for k, v in self.headers.items() if k.lower() in (
            "content-type", "origin", "referer", "user-agent", "sec-fetch-mode", "sec-fetch-dest", "sec-fetch-site")}
        out(f"\n----- {self.command} {self.path}\n  headers {json.dumps(keep)}\n  body {body}")
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"zzprobe 156 recorded this request\n")

    do_GET = do_POST = _log

    def log_message(self, *a):
        pass


with _lib.Created(c) as made:
    def create(label, body, who=c):
        r = who.post("/entity/action_menu_items", json=body)
        if r.status_code == 201:
            made.add("action_menu_items", r.json()["data"]["id"])
        out(f"  {label} -> {said(r)}")
        return r.json()["data"]["id"] if r.status_code == 201 else None

    out("===== 1. creates with growing bodies")
    create("{}", {})
    create("title", {"title": "zzprobe 156 title only", "projects": [P]})
    create("title + url", {"title": "zzprobe 156 url", "url": "https://example.invalid/ami", "projects": [P]})
    rid = create("title + url + entity_type Shot", {"title": "zzprobe 156 shot", "url": "https://example.invalid/ami",
                                                   "entity_type": "Shot", "projects": [P]})
    if rid:
        out(f"  read back: {json.dumps(readback(rid))}")

    out("\n===== 2. every editable field")
    full = {"title": "zzprobe 156 full", "url": "https://example.invalid/ami?x=1", "entity_type": "Shot",
            "list_order": 7, "selection_required": True, "folder": "zzprobe 156", "projects": [P],
            "permissions_groups": [prs["admin"], prs["artist"]], "payload_content_type": "json",
            "light_payload": True, "open_in_overlay": True, "poll_for_data_updates": True,
            "add_btn_behavior": "include_in_dropdown", "secret_token": "zzprobe-156-secret",
            "signature_algorithm": "sha256"}
    rid = create("all fields", full)
    if rid:
        out(f"  read back: {json.dumps(readback(rid))}")

    out("\n===== 3. edge values")
    create("url sgonset://shot/1 (custom protocol)", {"title": "zzprobe 156 protocol", "url": "sgonset://shot/1",
                                                      "entity_type": "Shot", "projects": [P]})
    create("url 'not a url'", {"title": "zzprobe 156 junk url", "url": "not a url", "entity_type": "Shot", "projects": [P]})
    create("entity_type NotAType", {"title": "zzprobe 156 bad type", "url": "https://example.invalid/",
                                    "entity_type": "NotAType", "projects": [P]})
    create("payload_content_type xml", {"title": "zzprobe 156 xml", "url": "https://example.invalid/",
                                        "entity_type": "Shot", "payload_content_type": "xml", "projects": [P]})
    create("entity_type CustomEntity slot of the take", {"title": "zzprobe 156 slot", "url": "https://example.invalid/",
                                                         "entity_type": "CustomEntity09", "projects": [P]})

    out("\n===== 4. rights and visibility")
    vis = {}
    for code in ("admin", "artist", None):
        vis[code] = create(f"permissions_groups [{code or 'none'}], as the script",
                           {"title": f"zzprobe 156 for {code or 'everyone'}", "url": "https://example.invalid/",
                            "entity_type": "Shot", "projects": [P],
                            **({"permissions_groups": [prs[code]]} if code else {})})
    people = [("Admin (the operator)", FPT.from_env(env, sudo_as_login=LOGIN))]
    if ARTIST:
        people.append(("Artist", FPT.from_env(env, sudo_as_login=ARTIST[1])))
    for label, who in people:
        create(f"create as {label}", {"title": f"zzprobe 156 by {label.split()[0]}", "url": "https://example.invalid/",
                                      "entity_type": "Shot", "projects": [P]}, who=who)
        r = who.post("/entity/action_menu_items/_search", headers=ARR, json={
            "filters": [["title", "starts_with", "zzprobe 156 for"]], "fields": ["title"]})
        out(f"  read as {label}: {said(r)} {sorted(x['attributes']['title'][15:] for x in r.json()['data']) if r.ok else ''}")

    if LISTEN:
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", LISTEN), Recorder)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        for kind in ("form", "json"):
            create(f"recorder, payload {kind}", {"title": f"zzprobe 156 recorder {kind}",
                                                 "url": f"http://localhost:{LISTEN}/ami/{kind}", "entity_type": "Shot",
                                                 "payload_content_type": kind, "projects": [P]})
        print(f"\nlistening on http://localhost:{LISTEN} for {HOLD} s: right-click a Shot in the sandbox project, "
              "run 'zzprobe 156 recorder form', then 'json', once with one Shot selected and once with two", flush=True)
        time.sleep(HOLD)
        srv.shutdown()
    _lib.emit("156_action_menu_item", "\n".join(rows), env)
