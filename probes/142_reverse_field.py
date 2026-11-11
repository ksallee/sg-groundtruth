"""Q: the reverse field an entity or multi_entity field makes on its linked type: what is it named, is
it in the schema, can its creation be avoided, and can it be retired on its own?

Probe 121 saw reverse fields only in the event log, and probe 134 saw a multi_entity to Attachment
make `<type>_<field>_<types>` on Attachment. sg-onset creates link fields at setup and must know what
else appears on the site. On two enabled custom slots (the first holds the field, the second is its
type), measured:

  1. an entity field: the fields new on the linked type, read in full
  2. the same create with a property the call does not document (`reverse`, `create_reverse`): the
     400 names the accepted set, or a 201 shows it was ignored
  3. a DELETE of the reverse field alone, then the forward field read
  4. a multi_entity field, for its reverse name

Writes, behind `--write`: schema fields `sg_zzprobe_142_*` on the first slot, retired before exit, and
whatever reverse fields they make, retired with them. No rows.

    python probes/142_reverse_field.py --write
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 142 writes; run with --write")
schema = c.get("/schema").json()["data"]
A, B = sorted(t for t in schema if t.startswith("CustomEntity") and t[12:].isdigit())[:2]
rows = []
made = []


def out(s=""):
    rows.append(str(s))


def errs(r):
    try:
        return json.dumps(r.json().get("errors", r.json()))[:900]
    except ValueError:
        return repr(r.text[:300])


def fields(t):
    return set(c.get(f"/schema/{t}/fields").json()["data"])


def mask(s):
    return s.replace(A, "<A>").replace(B, "<B>").replace(f"custom_entity{A[12:]}", "custom_entity<a>").replace(
        f"custom_entity{B[12:]}", "custom_entity<b>")


def create(label, body, linked):
    before = fields(linked)
    r = c.post(f"/schema/{A}/fields", json=body)
    name = r.json()["links"]["self"].rsplit("/", 1)[-1] if r.status_code == 201 else None
    out(f"  {label}: -> {r.status_code} {name or errs(r)}")
    if name:
        made.append(name)
    new = sorted(fields(linked) - before)
    out(f"    new on the linked type: {[mask(n) for n in new]}")
    for n in new:
        d = c.get(f"/schema/{linked}/fields/{n}").json()["data"]
        out(mask(f"      {n}: data_type {d['data_type']['value']}, name {d['name']['value']!r}, editable "
                 f"{d['editable']['value']}, valid_types {d['properties'].get('valid_types', {}).get('value')}, "
                 f"visible {d.get('visible', {}).get('value')}, custom_metadata {d.get('custom_metadata', {}).get('value')!r}"))
    return name, new


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


try:
    out("===== 1. an entity field on <A>, valid_types [<B>]")
    f1, rev1 = create("entity", {"data_type": "entity", "properties": prop(name="zzprobe 142 link", valid_types=[B])}, B)
    if rev1:
        r = c.get(f"/schema/{B}")
        out(f"    GET /schema/<B> -> {r.status_code}")
        r = c.get(f"/entity/custom_entity{B[12:]}s", params={"fields": rev1[0], "page[size]": 1})
        out(f"    GET /entity/<b> ?fields=<reverse> -> {r.status_code}")

    out("\n===== 2. undocumented properties that might stop the reverse field")
    for k, v in (("reverse", False), ("create_reverse", False)):
        create(f"entity with {k}: {v}", {"data_type": "entity", "properties": prop(
            name=f"zzprobe 142 {k.replace('_', ' ')}", valid_types=[B], **{k: v})}, B)

    out("\n===== 3. the reverse field retired on its own")
    if rev1:
        r = c.delete(f"/schema/{B}/fields/{rev1[0]}")
        out(f"  DELETE /schema/<B>/fields/<reverse> -> {r.status_code} {'' if r.ok else errs(r)}")
        out(f"    reverse live after: {c.get(f'/schema/{B}/fields/{rev1[0]}').status_code == 200}; "
            f"forward live: {c.get(f'/schema/{A}/fields/{f1}').status_code == 200}")
        r = c.put(f"/schema/{B}/fields/{rev1[0]}", json={"properties": prop(visible=False)})
        out(f"  PUT visible false on the reverse -> {r.status_code} {'' if r.ok else errs(r)}")

    out("\n===== 4. a multi_entity field on <A>, valid_types [<B>]")
    create("multi_entity", {"data_type": "multi_entity", "properties": prop(name="zzprobe 142 links", valid_types=[B])}, B)
    out("\n===== 5. an entity field on <A> to <A>")
    create("entity to its own type", {"data_type": "entity", "properties": prop(name="zzprobe 142 self", valid_types=[A])}, A)
finally:
    out("\n===== retire")
    bb = fields(B)
    for n in made:
        r = c.delete(f"/schema/{A}/fields/{n}")
        out(f"  retired <A>.{n} -> {r.status_code}")
    out(f"  reverse fields left on <B> after the forward fields retired: "
        f"{[mask(n) for n in sorted(bb - fields(B)) ]} went away; zzprobe-named still live: "
        f"{[mask(n) for n in fields(B) if 'zzprobe_142' in n]}")
    out(f"  zzprobe_142 live on <A>: {[mask(n) for n in fields(A) if 'zzprobe_142' in n]}")
    _lib.emit("142_reverse_field", "\n".join(rows), env)
    print("fields named, for the Trash:", made)
