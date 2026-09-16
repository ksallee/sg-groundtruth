"""Q: which dotted path filters a Note by the name of the thing it is about?

`note_links` is a multi_entity field whose `valid_types` spans most of the site, and probe 016 proved
a dotted path through a multi_entity field filters even though it cannot be read back. A notes client
searching "notes about sh010" has to pick one path per type, and the types disagree about whether the
name field is `code`, `content` or `name`. Read-only.
"""
import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []
P = _lib.sample_projects(c, env)[0]
SCOPE = ["project", "is", {"type": "Project", "id": P}]


def out(s=""):
    rows.append(s)


def search(conds, fields="id"):
    r = c.post("/entity/notes/_search", headers=ARR,
               json={"filters": [SCOPE] + conds, "fields": fields, "page": {"size": 500}})
    if not r.ok:
        return r.status_code, r.json()["errors"][0]["title"]
    return r.status_code, r.json()["data"]


def count(conds):
    """_summarize, so a count is the real one and not the page size."""
    r = c.post("/entity/notes/_summarize", headers=ARR, json={
        "filters": [SCOPE] + conds, "summary_fields": [{"field": "id", "type": "record_count"}]})
    if not r.ok:
        return r.status_code, r.json()["errors"][0]["title"]
    return r.status_code, r.json()["data"]["summaries"]["id"]


sch = c.get("/schema/Note/fields").json()["data"]
TYPES = sch["note_links"]["properties"]["valid_types"]["value"]
out(f"=== 1. Note.note_links valid_types: {len(TYPES)} on the probed site")
out(f"  {', '.join(TYPES)}")

st, base = count([])
out(f"\n=== 2. baseline: {base} Notes in the sample project")
linked = search([["note_links", "is_not", None]], "note_links")[1]
names = {}
for n in linked:
    for d in n["relationships"]["note_links"]["data"]:
        names.setdefault(d["type"], d["name"])
_lib.note_from(linked)
out(f"  {len(linked)} of them have note_links; linked types "
    f"{ {t: sum(1 for n in linked for d in n['relationships']['note_links']['data'] if d['type'] == t) for t in sorted(names)} }")

ONE = sorted(names.values(), key=len)[-1] if names else "zz"
STEM = ONE[:4]
out(f"  stem taken from a linked row's name: {STEM!r}, one whole name {ONE!r}")

out("\n=== 3. one filter per valid type, three candidate name fields")
out(f"  {'type':22} {'cached_display_name':>22} {'code':>22} {'name':>22}")
tally = {"cached_display_name": [0, 0], "code": [0, 0], "name": [0, 0]}
for t in TYPES:
    cells = []
    for f in ("cached_display_name", "code", "name"):
        path = f"note_links.{t}.{f}"
        st, got = count([[path, "contains", STEM]])
        ok = st == 200
        tally[f][0 if ok else 1] += 1
        cells.append(f"200, {got}" if ok else "400 doesn't exist")
    out(f"  {t:22} {cells[0]:>22} {cells[1]:>22} {cells[2]:>22}")
out(f"  resolved / 400: " + ", ".join(f"{f} {v[0]}/{v[1]}" for f, v in tally.items()))

out("\n=== 4. the 400s in full")
for path in (f"note_links.Booking.code", "note_links.Group.name", "note_links.Shot.zz_not_a_field",
             "note_links.ZzNotAType.code", "note_links.cached_display_name"):
    st, got = count([[path, "contains", STEM]])
    out(f"  {path:34} -> {st} {got}")

out("\n=== 5. the filter is evaluated, not ignored")
for label, conds in (
        ("note_links.Shot.code contains ZZZNOPE", [["note_links.Shot.code", "contains", "ZZZNOPE"]]),
        (f"note_links.Shot.code contains {STEM!r}", [["note_links.Shot.code", "contains", STEM]]),
        (f"note_links.Shot.code is {ONE!r}", [["note_links.Shot.code", "is", ONE]]),
        (f"note_links.Shot.cached_display_name is {ONE!r}",
         [["note_links.Shot.cached_display_name", "is", ONE]]),
        ("note_links.Shot.code is_not null", [["note_links.Shot.code", "is_not", None]]),
        ("note_links is_not null", [["note_links", "is_not", None]]),
        ("tasks is_not null", [["tasks", "is_not", None]]),
        ("two hops: note_links.Shot.sg_sequence.Sequence.code is_not null",
         [["note_links.Shot.sg_sequence.Sequence.code", "is_not", None]]),
        ("tasks.Task.content contains a", [["tasks.Task.content", "contains", "a"]]),
):
    st, got = count(conds)
    out(f"  {label:62} -> {st} {got}")

out("\n=== 6. reading the same path back")
r = c.post("/entity/notes/_search", headers=ARR, json={
    "filters": [SCOPE, ["note_links", "is_not", None]],
    "fields": "subject,note_links.Shot.code", "page": {"size": 3}})
out(f"  ?fields=subject,note_links.Shot.code -> {r.status_code} "
    f"attributes {sorted(r.json()['data'][0]['attributes']) if r.ok else ''}")

_lib.emit("071_note_link_name_filter", "\n".join(rows), env)
