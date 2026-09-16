"""Q: can a Note be made client-facing over REST?

`Note.client_note` is what the web application ties to a client-facing note, and a notes client that
offers the same toggle has to know whether the API will honour it. `--write` only for the creates;
the schema half runs without it. Every row is deleted on exit.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSON = {"Content-Type": "application/json"}
rows = []


def out(s=""):
    rows.append(s)


def err(r):
    return json.dumps(r.json()["errors"][0]) if r.content and not r.ok else ""


# --- 1. what the schema says ------------------------------------------------------------------
sch = c.get("/schema/Note/fields").json()["data"]
out("=== 1. GET /schema/Note/fields")
for f in ("client_note", "sg_note_type"):
    d, p = sch[f], sch[f]["properties"]
    out(f"  {f}: data_type {d['data_type']['value']!r}, editable {d['editable']['value']}, "
        f"mandatory {d['mandatory']['value']}, "
        f"default {p.get('default_value', {}).get('value')!r}")
vv = sch["sg_note_type"]["properties"].get("valid_values", {}).get("value")
out(f"  sg_note_type valid_values: {vv}")

if not _lib.writes_allowed():
    _lib.emit("069_client_note", "\n".join(rows), env)
    raise SystemExit("\nschema half only; add --write for the creates")

SANDBOX = _lib.sandbox_id(c, env)
login = (env.get("FPT_USER_LOGIN") or "").strip()
_lib.note_names(login)
pc = _lib.FPT.from_env(env, sudo_as_login=login)
BASE = {"project": {"type": "Project", "id": SANDBOX}, "subject": "zzprobe_069"}

with _lib.Created(c) as made:
    # --- 2. create with client_note ------------------------------------------------------------
    out("\n=== 2. POST /entity/notes")
    for who, cl in (("script", c), ("person", pc)):
        for label, extra in (("client_note true", {"client_note": True}),
                             ("client_note false", {"client_note": False})):
            r = cl.post("/entity/notes", headers=JSON, json={**BASE, **extra})
            if r.ok:
                i = made.add("notes", r.json()["data"]["id"])
                echo = r.json()["data"]["attributes"].get("client_note", "<absent from the echo>")
                back = cl.get(f"/entity/notes/{i}", params={"fields": "client_note"}).json()["data"]
                out(f"  as the {who}, {label:18} -> {r.status_code}, echo {echo!r}, "
                    f"re-read {back['attributes'].get('client_note')!r}")
            else:
                out(f"  as the {who}, {label:18} -> {r.status_code} {err(r)}")

    # --- 3. update it on a Note that already exists ---------------------------------------------
    n = c.post("/entity/notes", headers=JSON, json=BASE).json()["data"]
    made.add("notes", n["id"])
    back = c.get(f"/entity/notes/{n['id']}", params={"fields": "client_note"}).json()["data"]
    out(f"\n=== 3. PUT /entity/notes/<id>, on a plain Note whose client_note reads "
        f"{back['attributes'].get('client_note')!r} "
        f"(the create echo names client_note: {'client_note' in n['attributes']})")
    for who, cl in (("script", c), ("person", pc)):
        for label, body in (("client_note true", {"client_note": True}),
                            ("client_note false", {"client_note": False})):
            r = cl.put(f"/entity/notes/{n['id']}", headers=JSON, json=body)
            out(f"  as the {who}, {label:18} -> {r.status_code} "
                f"{err(r) or 'read back ' + repr(r.json()['data']['attributes']['client_note'])}")

    # --- 4. the field a client can set -----------------------------------------------------------
    out("\n=== 4. sg_note_type, the list field beside it")
    for value in ((vv or []) + ["zzznope"]):
        r = c.post("/entity/notes", headers=JSON, json={**BASE, "sg_note_type": value})
        if r.ok:
            i = made.add("notes", r.json()["data"]["id"])
            a = r.json()["data"]["attributes"]
            b = c.get(f"/entity/notes/{i}",
                      params={"fields": "sg_note_type,client_note"}).json()["data"]["attributes"]
            out(f"  create sg_note_type {value!r:12} -> {r.status_code}, echo "
                f"{a.get('sg_note_type')!r}, re-read {b.get('sg_note_type')!r}, "
                f"client_note {b.get('client_note')!r}")
        else:
            out(f"  create sg_note_type {value!r:12} -> {r.status_code} {err(r)}")
    r = c.put(f"/entity/notes/{n['id']}", headers=JSON, json={"sg_note_type": (vv or ["Client"])[0]})
    out(f"  PUT sg_note_type on an existing Note -> {r.status_code} "
        f"{err(r) or 'read back ' + repr(r.json()['data']['attributes']['sg_note_type'])}")

    # --- 5. can a client-facing Note be found? ---------------------------------------------------
    out("\n=== 5. filtering, scoped to the sandbox project")
    scope = ["project", "is", {"type": "Project", "id": SANDBOX}]
    for label, cond in (("no filter", None),
                        ("client_note is true", ["client_note", "is", True]),
                        ("client_note is false", ["client_note", "is", False]),
                        ("sg_note_type is 'Client'", ["sg_note_type", "is", "Client"]),
                        ("sg_note_type in ['Client']", ["sg_note_type", "in", ["Client"]]),
                        ("sg_note_type is null", ["sg_note_type", "is", None])):
        f = [scope] + ([cond] if cond else [])
        r = c.post("/entity/notes/_search", headers=ARR,
                   json={"filters": f, "fields": "id", "page": {"size": 500}})
        out(f"  {label:28} -> {r.status_code} {len(r.json()['data']) if r.ok else err(r)}")

_lib.emit("069_client_note", "\n".join(rows), env)
