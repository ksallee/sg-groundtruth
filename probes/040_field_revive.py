"""Q: what happens when you create a field whose display name belongs to a trashed field?

019 settled the create half: the `sg_` prefix is added blind, the programmatic name is computed from the
display name and returned nowhere but `links.self`, a duplicate of a *live* field becomes `<name>_1`, and
a collision with a *trashed* field 400s `schema_field_create() failed`.

`docs/quirks.md` lists three claims nobody has probed:

  - a trashed field can be revived
  - reviving fails when the trashed field's type differs from the type you want
  - recovery is to trash again and pick another programmatic name

This probe settles them, because the failure is invisible: a trashed field cannot be listed, so a client
colliding with one has no way to see what it collided with.

**This probe burns field names permanently.** A trashed name still collides and cannot be enumerated, so
it can never be reused. Every name here is `sg_zzprobe_040_*`, which nobody would choose deliberately.
Writes. Fields are the one thing `_lib.Created` cannot undo, so the probe trashes them itself and says so.
"""
import _lib

if not _lib.writes_allowed():
    raise SystemExit("040 creates schema fields, which burn a name on the site forever. "
                     "Run with --write only if you accept that.")

env = _lib.load_env()
c = _lib.client()
TYPE = "Version"
out = []
burned = []


def create(display, data_type, **props):
    body = {"data_type": data_type, "properties": [{"property_name": "name", "value": display}]}
    for k, v in props.items():
        body["properties"].append({"property_name": k, "value": v})
    r = c.post(f"/schema/{TYPE}/fields", json=body)
    name = None
    if r.status_code in (200, 201):
        # 019: the programmatic name is absent from the body; the last segment of links.self carries it.
        link = (r.json().get("links") or {}).get("self", "")
        name = link.rstrip("/").split("/")[-1]
        burned.append(name)
    return r, name


def err(r):
    try:
        e = (r.json().get("errors") or [{}])[0]
        return f"{e.get('title')} {e.get('source') or ''}".strip()
    except Exception:
        return r.text[:120]


def live(name):
    r = c.get(f"/schema/{TYPE}/fields", params={"field_name": name})
    return r.status_code == 200 and bool((r.json().get("data") or {}).get(name))


DISPLAY = "zzprobe 040 revive"

# --- 1. create, confirm, trash -----------------------------------------------------------------
r1, n1 = create(DISPLAY, "text")
out.append("**Create, then trash**\n")
out.append("```")
out.append(f"POST /schema/{TYPE}/fields  name={DISPLAY!r} data_type=text -> {r1.status_code}")
out.append(f"programmatic name (from links.self): {n1}")
out.append(f"visible in /schema: {live(n1) if n1 else 'n/a'}")
d = c.delete(f"/schema/{TYPE}/fields/{n1}") if n1 else None
out.append(f"DELETE /schema/{TYPE}/fields/{n1} -> {d.status_code if d is not None else 'skipped'}")
out.append(f"visible in /schema after the delete: {live(n1) if n1 else 'n/a'}")
out.append("```\n")

# --- 2. same display name, same type: is it revived, or a collision? ---------------------------
r2, n2 = create(DISPLAY, "text")
out.append("**Same display name, same type**\n")
out.append("```")
out.append(f"POST -> {r2.status_code}")
out.append(f"{err(r2) if r2.status_code >= 400 else 'programmatic name: ' + str(n2)}")
out.append("```\n")

# --- 3. same display name, a different type ----------------------------------------------------
r3, n3 = create(DISPLAY, "number")
out.append("**Same display name, a different type**\n")
out.append("```")
out.append(f"POST -> {r3.status_code}  (data_type=number against a trashed text field)")
out.append(f"{err(r3) if r3.status_code >= 400 else 'programmatic name: ' + str(n3)}")
out.append("```\n")

# --- 4. is a trashed field visible anywhere? ---------------------------------------------------
seen = {}
for label, params in (("plain", {}),
                      ("retired_only", {"options[retired_only]": "true"}),
                      ("return_only", {"options[return_only]": "retired"})):
    rr = c.get(f"/schema/{TYPE}/fields", params=params)
    keys = list((rr.json().get("data") or {}).keys()) if rr.status_code == 200 else []
    seen[label] = (rr.status_code, n1 in keys, len(keys))
out.append("**Can the trashed field be seen at all?**\n")
out.append("| listing | status | trashed field present | fields returned |")
out.append("|---|---|---|---|")
for label, (st, present, count) in seen.items():
    out.append(f"| `{label}` | {st} | {present} | {count} |")
out.append("")

# --- 5. revive. The call is in no documentation; the API names it in a 400 --------------------
bare = c.post(f"/schema/{TYPE}/fields/{n1}", json={})
rev = c.post(f"/schema/{TYPE}/fields/{n1}", json={"revive": True})
out.append("**Revive**\n")
out.append("```")
out.append(f"POST /schema/{TYPE}/fields/{n1}  {{}} -> {bare.status_code}")
out.append(f"  source: {(bare.json().get('errors') or [{}])[0].get('source')}")
out.append(f"POST /schema/{TYPE}/fields/{n1}  {{'revive': true}} -> {rev.status_code}")
out.append(f"  visible in /schema afterwards: {live(n1)}")
if live(n1):
    d = c.get(f"/schema/{TYPE}/fields").json()["data"][n1]
    out.append(f"  data_type: {(d.get('data_type') or {}).get('value')}  "
               f"editable: {(d.get('data_type') or {}).get('editable')}")
out.append("```\n")

# --- 6. can the revived field be given the type you actually wanted? --------------------------
p_in = c.put(f"/schema/{TYPE}/fields/{n1}",
             json={"properties": [{"property_name": "data_type", "value": "number"}]})
p_top = c.put(f"/schema/{TYPE}/fields/{n1}",
              json={"data_type": "number",
                    "properties": [{"property_name": "name", "value": DISPLAY}]})
after = ((c.get(f"/schema/{TYPE}/fields").json().get("data") or {}).get(n1) or {})
out.append("**Changing the revived field's type**\n")
out.append("| sent | result |")
out.append("|---|---|")
out.append(f"| `data_type` inside `properties` | {p_in.status_code} {err(p_in) if p_in.status_code >= 400 else ''} |")
out.append(f"| `data_type` at the top level | {p_top.status_code}, data_type is now "
           f"`{(after.get('data_type') or {}).get('value')}` |")
out.append("")
out.append("The second is the trap: 200, the whole field returned, the old type still in it.\n")

# --- 7. the documented recovery: a different display name --------------------------------------
r5, n5 = create("zzprobe 040 revive two", "number")
out.append("**A different display name**\n")
out.append("```")
out.append(f"POST -> {r5.status_code}  programmatic name: {n5}")
out.append("```\n")

# --- clean up what can be cleaned --------------------------------------------------------------
out.append("**Trashed on the way out**\n")
for n in burned:
    dd = c.delete(f"/schema/{TYPE}/fields/{n}")
    out.append(f"- `{n}` -> {dd.status_code}")
out.append("")
out.append(f"{len(set(burned))} names are now spent on this site and can never be reused. "
           f"A revive does not give one back: it is spent from the moment it is created.")

_lib.emit("040_field_revive", "\n".join(out), env)
