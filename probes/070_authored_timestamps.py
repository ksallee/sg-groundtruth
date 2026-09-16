"""Q: can a create body set created_at, and can anything set updated_at?

Anything that imports history, seeds a demo or mirrors another tracker needs rows dated when the work
happened rather than when the import ran. The schema reports both timestamps `editable: false`, which
probe 012 already showed is not what the create path enforces for `mandatory`. `--write` only; the
schema half runs without it. Every row is deleted on exit.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
JSON = {"Content-Type": "application/json"}
WHEN = "2019-03-04T05:06:07Z"
LATER = "2021-07-08T09:10:11Z"
TYPES = ("Note", "Reply", "Task", "Version")
SLUG = {"Note": "notes", "Reply": "replies", "Task": "tasks", "Version": "versions"}
rows = []


def out(s=""):
    rows.append(s)


def err(r):
    return json.dumps(r.json()["errors"][0]) if r.content and not r.ok else ""


# --- 1. what the schema says ------------------------------------------------------------------
out("=== 1. the schema's editable flag")
out(f"  {'type':10} {'created_at':>22} {'updated_at':>22}")
for t in TYPES:
    sch = c.get(f"/schema/{t}/fields").json()["data"]
    cells = []
    for f in ("created_at", "updated_at"):
        d = sch.get(f)
        cells.append("absent" if not d else
                     f"{d['data_type']['value']}, editable {d['editable']['value']}")
    out(f"  {t:10} {cells[0]:>22} {cells[1]:>22}")

if not _lib.writes_allowed():
    _lib.emit("070_authored_timestamps", "\n".join(rows), env)
    raise SystemExit("\nschema half only; add --write for the creates")

SANDBOX = _lib.sandbox_id(c, env)
login = (env.get("FPT_USER_LOGIN") or "").strip()
_lib.note_names(login)
pc = _lib.FPT.from_env(env, sudo_as_login=login)
P = {"type": "Project", "id": SANDBOX}

with _lib.Created(c) as made:
    host = c.post("/entity/notes", headers=JSON,
                  json={"project": P, "subject": "zzprobe_070_host"}).json()["data"]
    made.add("notes", host["id"])
    body = {
        "Note": {"project": P, "subject": "zzprobe_070"},
        "Reply": {"entity": {"type": "Note", "id": host["id"]}, "content": "zzprobe_070"},
        "Task": {"project": P, "content": "zzprobe_070"},
        "Version": {"project": P, "code": "zzprobe_070"},
    }

    def create(cl, t, extra):
        r = cl.post(f"/entity/{SLUG[t]}", headers=JSON, json={**body[t], **extra})
        if not r.ok:
            return r.status_code, err(r), None
        d = r.json()["data"]
        made.add(SLUG[t], d["id"])
        return r.status_code, d["attributes"], d["id"]

    # --- 2. created_at in the create body -------------------------------------------------------
    out(f"\n=== 2. POST with created_at {WHEN!r}")
    ids = {}
    for who, cl in (("script", c), ("person", pc)):
        for t in TYPES:
            st, a, i = create(cl, t, {"created_at": WHEN})
            if i is None:
                out(f"  as the {who}, {t:8} -> {st} {a}")
                continue
            back = cl.get(f"/entity/{SLUG[t]}/{i}",
                          params={"fields": "created_at,updated_at"}).json()["data"]["attributes"]
            out(f"  as the {who}, {t:8} -> {st}, echo created_at {a.get('created_at')!r}, "
                f"re-read {back.get('created_at')!r}, updated_at {back.get('updated_at')!r}")
            ids.setdefault(t, i)

    # --- 3. updated_at, and both together -------------------------------------------------------
    out(f"\n=== 3. POST with updated_at {WHEN!r}, and with both")
    for t in TYPES:
        for label, extra in ((" updated_at alone", {"updated_at": WHEN}),
                             ("created + updated", {"created_at": WHEN, "updated_at": LATER})):
            st, a, i = create(c, t, extra)
            if i is None:
                out(f"  {t:8} {label} -> {st} {a}")
            else:
                back = c.get(f"/entity/{SLUG[t]}/{i}",
                             params={"fields": "created_at,updated_at"}).json()["data"]["attributes"]
                out(f"  {t:8} {label} -> {st}, re-read created_at {back.get('created_at')!r}, "
                    f"updated_at {back.get('updated_at')!r}")

    # --- 4. on an existing row ------------------------------------------------------------------
    out(f"\n=== 4. PUT created_at {LATER!r} on the row created in step 2")
    for t in TYPES:
        if t not in ids:
            continue
        r = c.put(f"/entity/{SLUG[t]}/{ids[t]}", headers=JSON, json={"created_at": LATER})
        back = c.get(f"/entity/{SLUG[t]}/{ids[t]}",
                     params={"fields": "created_at"}).json()["data"]["attributes"]
        out(f"  {t:8} -> {r.status_code} {err(r) or ''} re-read {back.get('created_at')!r}")

    # --- 5. the formats a create accepts --------------------------------------------------------
    out("\n=== 5. created_at value shapes, on a Note")
    for value in (WHEN, "2019-03-04 05:06:07 UTC", "2019-03-04", "2019-03-04T05:06:07+02:00",
                  1551675967, "zzznope", None):
        st, a, i = create(c, "Note", {"created_at": value})
        if i is None:
            out(f"  {json.dumps(value):28} -> {st} {a}")
        else:
            back = c.get(f"/entity/notes/{i}",
                         params={"fields": "created_at"}).json()["data"]["attributes"]
            out(f"  {json.dumps(value):28} -> {st}, re-read {back.get('created_at')!r}")

    # --- 6. does the row sort and filter where it was dated? -------------------------------------
    out("\n=== 6. the authored date is the one the server queries")
    if "Note" in ids:
        f = [["project", "is", P], ["created_at", "less_than", "2020-01-01T00:00:00Z"],
             ["subject", "is", "zzprobe_070"]]
        r = c.post("/entity/notes/_search",
                   headers={"Content-Type": "application/vnd+shotgun.api3_array+json"},
                   json={"filters": f, "fields": "created_at", "sort": "created_at"})
        out(f"  created_at less_than 2020-01-01 -> {r.status_code} "
            f"{len(r.json()['data']) if r.ok else err(r)} zzprobe_070 Notes")

_lib.emit("070_authored_timestamps", "\n".join(rows), env)
