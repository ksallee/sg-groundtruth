"""Q: may a person who is not an administrator create, update and delete rows of the project's custom
entities, and delete an Attachment?

sg-onset writes Take-like rows on custom entities and removes photos. Probe 132 read each group's
rights from `/schema/permission_groups/<code>/entity_types/<Type>`; this sends the writes, as the
script acting through `sudo_as_login` (probe 027) as every group that has an active impersonatable
person, and reads the answer next to what that table said.

Per person: create a row on each enabled custom slot; update `code` and `sg_status_list` (the one
field the table lists as an exception) on a row the script made; delete it; create an Attachment
(`POST /entity/attachments`, probe 014's empty create, with `project`); delete it; delete an
Attachment the script made.

Writes in the sandbox, behind `--write`: rows `zzprobe_143_*` and Attachments, all deleted by the
script on exit.

    python probes/143_nonadmin_rows.py --write
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402
from sg_groundtruth.client import FPT  # noqa: E402

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 143 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
rows = []


def out(s=""):
    rows.append(str(s))


def title(r):
    if r.ok:
        return f"{r.status_code}"
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} code {e.get('code')} {e['title'][:300]}"
    except (ValueError, KeyError, IndexError):
        return f"{r.status_code} {r.text[:300]}"


schema = c.get("/schema").json()["data"]
CES = [t for t in sorted(schema) if t.startswith("CustomEntity") and t[12:].isdigit()]
slug = {t: f"custom_entity{t[12:]}s" for t in CES}
users = c.post("/entity/human_users/_search", headers=ARR, json={
    "filters": [["sg_status_list", "is", "act"], ["can_impersonate_this_user", "is", True],
                ["projects", "is", P]],
    "fields": ["login", "permission_rule_set"], "page": {"size": 200}}).json()["data"]
by_group = {}
for u in users:
    by_group.setdefault((u["relationships"]["permission_rule_set"]["data"] or {}).get("name"),
                        u["attributes"]["login"])
    _lib.note_names(u["attributes"]["login"])
out(f"groups with an active, impersonatable person in the sandbox project: {sorted(by_group)}")

with _lib.Created(c) as made:
    for group, login in sorted(by_group.items()):
        p = FPT.from_env(env, sudo_as_login=login)
        out(f"\n===== as {group}")
        for t in CES:
            label = f"<slot {t[12:]}>"
            has_status = "sg_status_list" in c.get(f"/schema/{t}/fields").json()["data"]
            r = p.post(f"/entity/{slug[t]}", json={"project": P, "code": f"zzprobe_143_{group}"})
            if r.status_code == 201:
                made.add(slug[t], r.json()["data"]["id"])
            mine = made.add(slug[t], c.post(f"/entity/{slug[t]}", json={
                "project": P, "code": "zzprobe_143_script"}).json()["data"]["id"])
            u1 = p.put(f"/entity/{slug[t]}/{mine}", json={"code": f"zzprobe_143_{group}_upd"})
            u2 = p.put(f"/entity/{slug[t]}/{mine}", json={"sg_status_list": None}) if has_status else None
            d = p.delete(f"/entity/{slug[t]}/{mine}")
            gone = c.get(f"/entity/{slug[t]}/{mine}").status_code
            out(f"  {label}: create {title(r)}\n      update code {title(u1)}"
                + (f"\n      update sg_status_list {title(u2)}" if u2 is not None else "; no sg_status_list")
                + f"\n      delete the script's row {title(d)}; GET after -> {gone}")
            if d.ok:
                made.rows.remove((slug[t], mine))

        a = p.post("/entity/attachments", json={"project": P, "description": f"zzprobe_143_{group}"})
        out(f"  Attachment: create {title(a)}"
            + (f", project reads {(a.json()['data']['relationships'].get('project') or {}).get('data')}" if a.ok else ""))
        if a.status_code == 201:
            aid = made.add("attachments", a.json()["data"]["id"])
            d = p.delete(f"/entity/attachments/{aid}")
            out(f"      delete its own Attachment {title(d)}")
            if d.ok:
                made.rows.remove(("attachments", aid))
        sa = made.add("attachments", c.post("/entity/attachments", json={
            "project": P, "description": "zzprobe_143_script"}).json()["data"]["id"])
        d = p.delete(f"/entity/attachments/{sa}")
        out(f"      delete the script's Attachment {title(d)}")
        if d.ok:
            made.rows.remove(("attachments", sa))

    left = sum(len(c.post(f"/entity/{slug[t]}/_search", headers=ARR, json={
        "filters": [["code", "starts_with", "zzprobe_143"]], "fields": ["id"]}).json()["data"]) for t in CES)
    out(f"\nzzprobe_143 rows live before cleanup: {left}")
    _lib.emit("143_nonadmin_rows", "\n".join(rows), env)
