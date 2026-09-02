---
intent: Write a Cut and its CutItems from an edit, read the timeline back, and reconcile a second edit against the Cut already there
tags: [write, cut, timecode, version, shot, batch, filter, entity-field, multi-entity, trap, recipe]
scope: api
measured: sandbox project; Cut and CutItem hold 0 rows site-wide, so every row was created here
---

# 007_build_and_reconcile_a_cut

A Cut is the edit; a CutItem is one clip in it. `Cut` is addressed at `/entity/cuts` and `CutItem` at
`/entity/cut_items`, both project-scoped, both requiring only `project` on create and both generating
`code` as `New Cut <id>` / `New Cut Item <id>` when it is omitted. Neither has an entity-type card yet.
On the probed site both types hold zero rows, so everything below was measured on rows this probe wrote.

## The write order

Four stages, because each one needs ids from the one before and a batch cannot reference an id it
creates (`recipes/002`).

| stage | call | what it needs from the stage before |
|---|---|---|
| 1 | `POST /entity/cuts` | nothing. `project` only; `fps` and `timecode_start_text` are set here or nowhere |
| 2 | `POST /entity/_batch`, `entity: "Shot"` | nothing, but read `code` first: Shot codes are not unique |
| 3 | `POST /entity/_batch`, `entity: "Version"` | stage 2's Shot id, for `Version.entity` |
| 4 | `POST /entity/_batch`, `entity: "CutItem"` | the Cut id, the Shot id and the Version id, all three |

In a batch, `entity` is the singular schema name, and the two other spellings 400:
`"cut_item"` gives `Invalid entity type: entity type [cut_item] does not exist.` and `"CutItems"` the
same message with `[CutItems]`. A CutItem create needs `project` even
when `cut` is sent: 400 `API create() missing 'project' attribute: {"code" => "...", "cut" => {"type" =>
"Cut", "id" => 19}}`.

## The fields that place an item on the timeline

Six numbers and four strings, on two axes: where the clip sits in the cut, and where it was taken from
in the source. The server fills none of them and relates none of them to each other.

| field | data type | axis | filled by |
|---|---|---|---|
| `cut_order` | `number` | the item's rank in the cut | client |
| `edit_in`, `edit_out` | `number` | frames, position in the cut | client |
| `cut_item_in`, `cut_item_out` | `number` | frames, position in the source | client |
| `cut_item_duration` | `number` | frames, length | client. Still `null` after `edit_in` and `edit_out` are written |
| `timecode_edit_in_text`, `timecode_edit_out_text` | `text` | the same position in the cut, as `HH:MM:SS:FF` | client |
| `timecode_cut_item_in_text`, `timecode_cut_item_out_text` | `text` | the same position in the source | client |
| `cut`, `shot`, `version` | `entity` | `['Cut']`, `['Shot']`, `['Version']` | client |
| `code` | `text` | the clip name | server, as `New Cut Item <id>`, when omitted |
| `cached_display_name` | `text` | mirrors `code` | server |
| `id`, `created_at`, `created_by`, `updated_at`, `updated_by` | | | server |

Neither type has a field of data type `timecode`; the four `timecode_*_text` fields are `text` and
validate nothing, so the millisecond integer of `field_types/timecode` is not in play here. The frame
rate is `Cut.fps`, a `float` that reads back as the string `"24.0"` and is `null` when unset. A client
therefore needs three things of its own beside the frame numbers: the rate, whether the timecode is
drop frame, and the cut's start timecode. None of the three is derivable from a CutItem.

## Call

```python
import json
import sys

sys.path.insert(0, "src")                       # or PYTHONPATH=src
from sg_groundtruth.client import FPT           # adds the bearer token and the /api/v1 prefix
from sg_groundtruth.env import load

c = FPT.from_env(load("."))                     # FPT_API_SITE_URL, FPT_API_SCRIPT_NAME, FPT_API_API_KEY
JSON = {"Content-Type": "application/json"}
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}   # array filters need it (probe 004)

PROJECT_ID = 1180                               # the caller supplies these four
CUT_CODE, FPS, START = "reel1", 24.0, "01:00:00:00"

# One tuple per clip, in order: code, first and last frame on the cut timeline, first and last frame
# in the source media. "last frame" is this client's convention. The server stores the six numbers
# and relates none of them to each other.
EDIT_A = [("reel1_sh010", 0, 47, 86400, 86447),
          ("reel1_sh020", 48, 119, 12000, 12071),
          ("reel1_sh030", 120, 167, 400, 447)]
EDIT_B = [("reel1_sh010", 0, 47, 86400, 86447),      # unchanged
          ("reel1_sh020", 48, 95, 12000, 12047),     # retimed, 24 frames shorter
          ("reel1_sh040", 108, 155, 900, 947)]       # new, after 12 frames of black
MADE = []                                           # (slug, id) of every row this run created


def call(method, path, **kw):
    r = c.request(method, path, **kw)
    if not r.ok:
        raise SystemExit(json.dumps(r.json()["errors"], indent=2))
    return r.json() if r.content else {}


def batch(reqs):
    """One atomic call, one result row per request, in request order (recipe 002). Chunk at ~200."""
    return [row.get("data", row)["id"]
            for row in call("POST", "/entity/_batch", json={"requests": reqs})["data"]]


def search(slug, filters, fields, **kw):
    """A cut of 500 items needs paging: page until `data` is empty, never on a missing
    `links.next` (probe 006)."""
    return call("POST", f"/entity/{slug}/_search", headers=ARR,
                json={"filters": filters, "fields": fields, "page": {"size": 500}, **kw})["data"]


def tc(frame, fps, start="00:00:00:00"):
    """Frames to HH:MM:SS:FF, non drop frame. No CutItem field states the rate, so this is the
    client's own arithmetic over a rate it stored on Cut.fps."""
    r = int(round(fps))
    h, m, s, f = (int(x) for x in start.split(":"))
    t = frame + f + r * (s + 60 * m + 3600 * h)
    return "%02d:%02d:%02d:%02d" % (t // (3600 * r), t // (60 * r) % 60, t // r % 60, t % r)


def pairs(rows, code_of):
    """Nothing on CutItem is unique, and cut_order is exactly what a recut changes, so items pair
    on the clip name plus its occurrence, scoped to one Cut."""
    seen, out = {}, {}
    for row in rows:
        code = code_of(row)
        seen[code] = seen.get(code, 0) + 1
        out[(code, seen[code])] = row
    return out


IN_PROJECT = ["project", "is", {"type": "Project", "id": PROJECT_ID}]

# 1. The Cut. Only `project` is required, `code` is not unique, and `revision_number` is a plain
#    number the client sets, so "the current cut" is a sort, not a lookup.
cuts = search("cuts", [IN_PROJECT, ["code", "is", CUT_CODE]], ["code", "revision_number", "fps"],
              sort="-revision_number")
if cuts:
    CUT_ID = cuts[0]["id"]
    FPS = float(cuts[0]["attributes"]["fps"])   # a float reads back as a string (field_types/float)
else:
    CUT_ID = call("POST", "/entity/cuts", headers=JSON, json={
        "project": {"type": "Project", "id": PROJECT_ID}, "code": CUT_CODE, "revision_number": 1,
        "fps": FPS, "timecode_start_text": START})["data"]["id"]
    MADE.append(("cuts", CUT_ID))


def sync(edit):
    # 2. Shots, one per distinct clip name. A Shot code is not unique, so read before creating or a
    #    re-run doubles them (entity_types/Shot).
    codes = sorted({e[0] for e in edit})
    shots = {d["attributes"]["code"]: d["id"]
             for d in search("shots", [IN_PROJECT, ["code", "in", codes]], ["code"])}
    todo = [x for x in codes if x not in shots]
    new = batch([{"request_type": "create", "entity": "Shot",
                  "data": {"project": {"type": "Project", "id": PROJECT_ID}, "code": x}}
                 for x in todo]) if todo else []
    MADE.extend(("shots", i) for i in new)
    shots.update(zip(todo, new))

    # 3. Versions. Each one needs step 2's Shot id for `entity`, and a batch cannot reference an id
    #    it creates (recipe 002), so this is a second call and not the same one.
    by_code = {d["attributes"]["code"]: d["id"]
               for d in search("versions", [IN_PROJECT, ["code", "in", [f"{x}_v001" for x in codes]]],
                               ["code"])}
    vers = {x: by_code[f"{x}_v001"] for x in codes if f"{x}_v001" in by_code}
    todo = [x for x in codes if x not in vers]
    new = batch([{"request_type": "create", "entity": "Version",
                  "data": {"project": {"type": "Project", "id": PROJECT_ID}, "code": f"{x}_v001",
                           "entity": {"type": "Shot", "id": shots[x]}}} for x in todo]) if todo else []
    MADE.extend(("versions", i) for i in new)
    vers.update(zip(todo, new))

    def data(order, e):
        code, edit_in, edit_out, src_in, src_out = e
        return {"project": {"type": "Project", "id": PROJECT_ID}, "code": code,
                "cut": {"type": "Cut", "id": CUT_ID},
                "shot": {"type": "Shot", "id": shots[code]},
                "version": {"type": "Version", "id": vers[code]},
                "cut_order": order,
                "edit_in": edit_in, "edit_out": edit_out,
                "cut_item_in": src_in, "cut_item_out": src_out,
                "cut_item_duration": edit_out - edit_in + 1,
                "timecode_edit_in_text": tc(edit_in, FPS, START),
                "timecode_edit_out_text": tc(edit_out + 1, FPS, START),
                "timecode_cut_item_in_text": tc(src_in, FPS),
                "timecode_cut_item_out_text": tc(src_out + 1, FPS)}

    # 4. Pair the edit against what this Cut already holds. Reading the rows filtered on `cut` is
    #    the linked-Cut check: an id from anywhere else, a cached ingest map or a search on `code`,
    #    can sit on another Cut, and updating it corrupts that Cut instead of this one. Re-checking
    #    `cut.Cut.id` costs nothing here and is the guard to keep when the ids come from elsewhere.
    have = pairs(search("cut_items", [["cut", "is", {"type": "Cut", "id": CUT_ID}]],
                        ["code", "cut.Cut.id"], sort="cut_order"),
                 lambda d: d["attributes"]["code"])
    have = {k: d for k, d in have.items() if d["attributes"]["cut.Cut.id"] == CUT_ID}
    want = pairs(list(enumerate(edit, 1)), lambda p: p[1][0])

    # 5. CutItems last: each needs the Cut, the Shot and the Version. Update, create and delete go
    #    in one batch, which applies whole or not at all.
    reqs = [{"request_type": "update", "entity": "CutItem", "record_id": have[k]["id"],
             "data": data(*want[k])} for k in want if k in have]
    reqs += [{"request_type": "create", "entity": "CutItem", "data": data(*want[k])}
             for k in want if k not in have]
    reqs += [{"request_type": "delete", "entity": "CutItem", "record_id": have[k]["id"]}
             for k in have if k not in want]
    out = batch(reqs)
    MADE.extend(("cut_items", i) for r, i in zip(reqs, out) if r["request_type"] == "create")
    for r, i in zip(reqs, out):
        if r["request_type"] == "delete":
            MADE.remove(("cut_items", i))
    return [f"{r['request_type']} {i}" for r, i in zip(reqs, out)]


# 6. Read the cut back. The order is `cut_order` and nothing else: Cut.cut_items is returned sorted
#    by the item's display name. A gap is not stored, and neither is an overlap: both are the
#    difference between one item's edit_out and the next item's edit_in.
def timeline():
    items = search("cut_items", [["cut", "is", {"type": "Cut", "id": CUT_ID}]],
                   ["code", "cut_order", "edit_in", "edit_out", "cut_item_duration",
                    "timecode_edit_in_text"], sort="cut_order")
    out = []
    for prev, this in zip([None] + items, items):
        a = this["attributes"]
        d = None if prev is None else a["edit_in"] - (prev["attributes"]["edit_out"] + 1)
        out.append(f"{a['cut_order']} {a['code']} {a['edit_in']}-{a['edit_out']} "
                   f"dur {a['cut_item_duration']} {a['timecode_edit_in_text']} "
                   + ("" if not d else f"GAP {d}" if d > 0 else f"OVERLAP {-d}"))
    return out


print("cut", CUT_ID, "| A:", sync(EDIT_A))
print("\n".join("  " + x for x in timeline()))
print("B:", sync(EDIT_B))
print("\n".join("  " + x for x in timeline()))

# 7. Teardown, deleting only what this run made, CutItems before their Cut: deleting a Cut leaves
#    its CutItems behind with `cut` null, findable only with [["cut", "is", None]].
for slug, i in reversed(MADE):
    call("DELETE", f"/entity/{slug}/{i}")
```

## Response

```
cut 22 | A: ['create 59', 'create 60', 'create 61']
  1 reel1_sh010 0-47 dur 48 01:00:00:00
  2 reel1_sh020 48-119 dur 72 01:00:02:00
  3 reel1_sh030 120-167 dur 48 01:00:05:00
B: ['update 59', 'update 60', 'create 62', 'delete 61']
  1 reel1_sh010 0-47 dur 48 01:00:00:00
  2 reel1_sh020 48-95 dur 48 01:00:02:00
  3 reel1_sh040 108-155 dur 48 01:00:04:12 GAP 12
```

The reconcile is one batch of 4 requests answering `[59, 60, 62, 61]`, in request order: two updates,
then the create, then the delete.

A separate run that prints each stage, with the four clip names created up front:

```
1. POST /entity/cuts -> 201 id=19 code='reel1' cached_display_name='reel1 v001' fps='24.0'
2. batch create Shot x4    -> {'sh010': 7576, 'sh020': 7577, 'sh030': 7578, 'sh040': 7579}
3. batch create Version x4 -> {'sh010': 31681, 'sh020': 31682, 'sh030': 31683, 'sh040': 31684}
4. batch create CutItem x3 -> [46, 47, 48]
```

## Gaps and overlaps

Nothing between two items is stored. A boundary is `next.edit_in - (this.edit_out + 1)` under the
convention that `edit_out` is the last frame; a client that treats `edit_out` as one past the end
drops the `+ 1`. Six items in one Cut, read back sorted on `cut_order`:

| this item | next item | `edit_out` then `edit_in` | boundary |
|---|---|---|---|
| `sh010` | `sh020` | 47 then 48 | contiguous |
| `sh020` | `sh030` | 119 then 120 | contiguous |
| `sh030` | `sh030_gap` | 167 then 400 | gap 232 |
| `sh030_gap` | `sh030_overlap` | 447 then 300 | overlap 148 |
| `sh030_overlap` | `aaa_last` | 500 then 600 | gap 99 |

Every anomaly writes at 200 and reads back exactly as sent, so a client that does not test for one
never learns of it:

| written | result |
|---|---|
| `edit_in` 100, `edit_out` 50 | 200, `{'edit_in': 100, 'edit_out': 50}` |
| `edit_in` -100, `edit_out` -50 | 200, stored |
| a second item with the same `cut_order` | 200 |
| `cut_order` `null` | 200; the row sorts last |
| `timecode_edit_in_text` `"banana"` | 200, `'banana'` |
| `timecode_edit_in_text` `""` | 200, stored as `null` (`field_types/text`) |
| `timecode_edit_in_text` `01:00:05:00` with `timecode_edit_out_text` `01:00:00:00` | 200, both stored |
| `edit_in` and `edit_out` written, `cut_item_duration` sent as `null` | 200, `cut_item_duration` reads `null` |
| 6 items on a Cut whose `duration` is 168 and `timecode_end_text` `'01:00:07:00'` | both keep what was written |

The frame pair and the timecode pair are two independent stores of one boundary. Write both from one
source of truth in the same call and prefer the frames on read: they are integers the API type-checks
(`field_types/number`), while the timecode strings accept anything. When only the strings are populated,
parse them with `Cut.fps`, and treat a disagreement as corrupt data rather than picking a winner.

## Pairing an item across two edits

| candidate key | why |
|---|---|
| `id` | unique, and the only key the server enforces, but it exists only for rows already read back from this Cut |
| position in the list | wrong by construction: a recut is a change of position |
| `cut_order` | the stored form of position. Same objection, and it is neither unique nor non-null |
| `shot` | often `null`, and one Shot appears in several items |
| `code` | what the edit and the row both hold. Not unique: two items in one Cut may share it |
| `(code, nth occurrence in cut_order sequence)`, scoped to the Cut | works. `code` names the clip, the occurrence index separates repeats, and the Cut scope keeps it away from every other Cut's rows |

Matched key means update, unmatched wanted key means create, unmatched existing key means delete. What
counts as "the same clip retimed" versus "a different clip" beyond that is the caller's policy; the API
offers `code`, `shot`, `version` and the six numbers to decide it on, and enforces none of them.

## Notes

- **The four stages exist because a batch cannot use an id it creates** (`recipes/002`). A CutItem
  needs a Cut id, a Shot id and a Version id at once, and a Version needs a Shot id, so the graph is
  four levels deep and each level is its own call. Within a level, batch, and chunk at around 200
  requests.
- **An id alone does not say which Cut a row is on.** `code` repeats across Cuts:
  `[["code", "is", "reel1_sh010"]]` returned items `(46, cut 19)` and `(53, cut 20)`. A blind
  `PUT /entity/cut_items/53` with no `cut` key answered 200, left `cut` at 20, and overwrote that Cut's
  metadata. Before updating, confirm the row's Cut: filter on `cut` when reading, or ask for
  `cut.Cut.id` in `fields` and drop every id that does not match. A dotted read through this single
  `entity` field works, unlike one through a multi_entity field (probe 016).
- **Sending `cut` in an update moves the item.** `PUT` with `{"cut": {"type": "Cut", "id": other}}`
  answers 200 and the item leaves its old Cut. So does the other side:
  `PUT /entity/cuts/<a>` with `{"cut_items": {"multi_entity_update_mode": "add", "value": [...]}}`
  answered 200 and left the item's former Cut holding `[]`. `CutItem.cut` is single-valued, so an
  `add` on the parent is a re-parent, not an addition.
- **`Cut.cut_items` is not the running order.** It is returned sorted by the item's display name:
  `['aaa_last', 'sh010', 'sh020', 'sh030', 'sh030_gap', 'sh030_overlap']` against `cut_order`
  `1, 2, 3, 4, 5, 6` on the same six rows. Read the items with
  `POST /entity/cut_items/_search`, `[["cut", "is", {"type": "Cut", "id": N}]]`, `sort: "cut_order"`.
  A `null` `cut_order` sorts last in both directions.
- **No frame rate is reachable from a CutItem.** `Cut.fps` is the only rate on either type, it is
  `null` until someone writes it, and no CutItem field points at the Cut's value. Read `Cut.fps` once
  and pass it down; `float` reads back as a string, so `float()` it (`field_types/float`). Drop frame
  is expressible only inside the `text` fields, which validate nothing, so the client owns that flag
  too.
- **Deleting a Cut does not delete its CutItems.** `DELETE /entity/cuts/<id>` answered 204 and the
  item survived with `cut` `null`, reachable only through
  `[["project", "is", ...], ["cut", "is", None]]`. Delete the items first. A delete inside a batch is
  not idempotent: a second delete of the same id 404s and takes the whole batch with it
  (`recipes/002`).
- **Nothing about a Cut is unique either.** Three Cuts created with the same `code` all answered 201.
  `revision_number` is a plain number the client maintains, and the display name the server builds
  from it is `code` plus ` v%03d`: `reel1 v001`, `reel1 v002`, and bare `reel1` when
  `revision_number` is `null`. "The current cut" is `sort: "-revision_number"` over a `code` filter.
- `Cut.entity` accepts `['Sequence', 'Scene', 'Episode', 'Reel']` and `Cut.version` a `Version`, whose
  reverse `Version.cuts` fills in on the same write.
