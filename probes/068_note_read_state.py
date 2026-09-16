"""Q: what is Note.read_by_current_user, given GET /schema/Note/fields does not declare it?

Probe 067 saw the key on every Note create and read it as the string "unread". A notes client that
draws an unread badge has to know whether the value is per person, whether it can be written, and
whether a filter on it narrows anything. `--write` only for the seed; the schema and filter halves
run without it. Every row is deleted on exit.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
HSH = {"Content-Type": "application/vnd+shotgun.api3_hash+json"}
JSON = {"Content-Type": "application/json"}
FIELD = "read_by_current_user"
rows = []


def out(s=""):
    rows.append(s)


# --- 1. the schema, ungated -------------------------------------------------------------------
sch = c.get("/schema/Note/fields").json()["data"]
names = sorted(sch)
out("=== 1. GET /schema/Note/fields")
out(f"  {len(names)} fields; names containing 'read': {[n for n in names if 'read' in n] or 'none'}")
one = c.get(f"/schema/Note/fields/{FIELD}")
out(f"  GET /schema/Note/fields/{FIELD} -> {one.status_code} "
    f"{json.dumps(one.json())[:240]}")
ctl = c.get("/schema/Note/fields/sg_status_list")
out(f"  GET /schema/Note/fields/sg_status_list -> {ctl.status_code} (control, declared)")
nope = c.get("/schema/Note/fields/zz_not_a_field_at_all")
out(f"  GET /schema/Note/fields/zz_not_a_field_at_all -> {nope.status_code} "
    f"{json.dumps(nope.json())[:200]} (control, no such name)")

if not _lib.writes_allowed():
    _lib.emit("068_note_read_state", "\n".join(rows), env)
    raise SystemExit("\nschema half only; add --write for the seed and the filters")

SANDBOX = _lib.sandbox_id(c, env)
login = (env.get("FPT_USER_LOGIN") or "").strip()
person = c.post("/entity/human_users/_search", headers=ARR,
                json={"filters": [["login", "is", login]], "fields": ["login"]}).json()["data"]
PERSON = person[0]["id"]
_lib.note_names(login)
pc = _lib.FPT.from_env(env, sudo_as_login=login)

with _lib.Created(c) as made:
    # --- 2. the seed --------------------------------------------------------------------------
    made_ids = []
    for i in range(4):
        n = c.post("/entity/notes", headers=JSON, json={
            "project": {"type": "Project", "id": SANDBOX},
            "subject": f"zzprobe_068_{i}",
            "content": "zzprobe 068: read state",
            "sg_status_list": "opn"}).json()["data"]
        made.add("notes", n["id"])
        made_ids.append(n["id"])
    out("\n=== 2. the seed: 4 Notes in the sandbox project")
    fresh = c.get(f"/entity/notes/{made_ids[0]}", params={"fields": FIELD}).json()["data"]
    out(f"  on create, as the script: {FIELD} = {fresh['attributes'].get(FIELD)!r}")

    # --- 3. writing it ------------------------------------------------------------------------
    out(f"\n=== 3. PUT {FIELD}")
    w = c.put(f"/entity/notes/{made_ids[0]}", headers=JSON, json={FIELD: "read"})
    echo = w.json()["data"]["attributes"].get(FIELD, "<absent from the echo>") if w.ok else ""
    back = c.get(f"/entity/notes/{made_ids[0]}", params={"fields": FIELD}).json()["data"]
    out(f"  as the script, 'read'   -> {w.status_code}, echo {echo!r}, "
        f"re-read {back['attributes'].get(FIELD)!r}")
    for i, value in ((1, "read"), (2, "read")):
        pw = pc.put(f"/entity/notes/{made_ids[i]}", headers=JSON, json={FIELD: value})
        pb = pc.get(f"/entity/notes/{made_ids[i]}", params={"fields": FIELD}).json()["data"]
        out(f"  as the person, {value!r} -> {pw.status_code}, re-read {pb['attributes'].get(FIELD)!r}")
    bad = pc.put(f"/entity/notes/{made_ids[3]}", headers=JSON, json={FIELD: "zzznope"})
    out(f"  as the person, 'zzznope' -> {bad.status_code}")
    out(f"    {json.dumps(bad.json()['errors'][0]) if bad.content else ''}")

    # --- 4. reading it back per person --------------------------------------------------------
    out("\n=== 4. the same four Notes, read by each identity")
    for who, cl in (("script", c), ("person", pc)):
        got = []
        for i in made_ids:
            r = cl.get(f"/entity/notes/{i}", params={"fields": FIELD}).json()["data"]
            got.append(r["attributes"].get(FIELD))
        out(f"  {who:6}  {got}")

    # --- 5. filters ---------------------------------------------------------------------------
    scope = ["project", "is", {"type": "Project", "id": SANDBOX}]

    def search(cl, hdr, conds):
        body = {"filters": conds, "fields": "id", "page": {"size": 500}}
        if hdr is HSH:
            body["filters"] = {"logical_operator": "and", "conditions": conds}
        r = cl.post("/entity/notes/_search", headers=hdr, json=body)
        if not r.ok:
            return r.status_code, json.dumps(r.json()["errors"][0])
        return r.status_code, len(r.json()["data"])

    def summarize(cl, conds):
        r = cl.post("/entity/notes/_summarize", headers=ARR, json={
            "filters": conds, "summary_fields": [{"field": "id", "type": "record_count"}]})
        if not r.ok:
            return r.status_code, json.dumps(r.json()["errors"][0])
        return r.status_code, r.json()["data"]["summaries"]["id"]

    cases = [
        ("no read filter (baseline)", []),
        (f'{FIELD} is "read"', [[FIELD, "is", "read"]]),
        (f'{FIELD} is "unread"', [[FIELD, "is", "unread"]]),
        (f'{FIELD} is_not "read"', [[FIELD, "is_not", "read"]]),
        (f'{FIELD} is_not "unread"', [[FIELD, "is_not", "unread"]]),
        (f'{FIELD} is "zzznope"', [[FIELD, "is", "zzznope"]]),
        (f'{FIELD} in ["read"]', [[FIELD, "in", ["read"]]]),
        (f'{FIELD} in ["unread"]', [[FIELD, "in", ["unread"]]]),
        (f'{FIELD} in ["read","unread"]', [[FIELD, "in", ["read", "unread"]]]),
        (f'{FIELD} in ["zzznope"]', [[FIELD, "in", ["zzznope"]]]),
        (f'{FIELD} not_in ["read"]', [[FIELD, "not_in", ["read"]]]),
        (f'{FIELD} not_in ["unread"]', [[FIELD, "not_in", ["unread"]]]),
        ('control sg_status_list in ["clsd"]', [["sg_status_list", "in", ["clsd"]]]),
        ('control sg_status_list in ["opn"]', [["sg_status_list", "in", ["opn"]]]),
    ]
    out("\n=== 5. filters, as the person, every call scoped to the sandbox project")
    out(f"  {'filter':38} {'api3_array':>12} {'api3_hash':>12} {'_summarize':>12}")
    for label, conds in cases:
        full = [scope] + conds
        a = search(pc, ARR, full)
        h = search(pc, HSH, full)
        s = summarize(pc, full)
        out(f"  {label:38} {str(a[1]):>12} {str(h[1]):>12} {str(s[1]):>12}")

    out("\n=== 6. the same filters as the script, for whom every Note in the project is unread")
    for label, conds in cases[1:-2]:
        a = search(c, ARR, [scope] + conds)
        out(f"  {label:38} {str(a[1]):>12}")

    out("\n=== 7. the operator vocabulary")
    st, err = search(pc, ARR, [scope, [FIELD, "definitely_not_an_operator", None]])
    out(f"  {FIELD} definitely_not_an_operator -> {st}")
    out(f"    {err}")
    st, err = search(pc, ARR, [scope, ["sg_note_type", "contains", "Client"]])
    out(f"  sg_note_type contains 'Client' -> {st}")
    out(f"    {err}")

    out("\n=== 8. is it in a projection at all?")
    r = c.get(f"/entity/notes/{made_ids[0]}", params={"fields": f"subject,{FIELD},zz_not_a_field"})
    out(f"  ?fields=subject,{FIELD},zz_not_a_field -> {r.status_code} "
        f"{sorted(r.json()['data']['attributes'])}")

_lib.emit("068_note_read_state", "\n".join(rows), env)
