"""Q: how is a Playlist addressed, what does creating one require, and does its version order survive?

A playlist is its `versions` multi_entity and nothing else. `field_types/multi_entity` proved a bare list
replaces the whole set, so the common operation here (append one Version to a review) is the one that
fails silently. The second question is order: a playlist reads as a sequence to a human, and
`field_types/multi_entity` found read order is not insertion order on the field it probed.

Read-only by default. `--write` adds the create contract, the order and add-mode writes and the
cross-project attempt, sandbox only, every row deleted on the way out.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
JSN = {"Content-Type": "application/json"}
rows = []


def err(r):
    """Whole errors[] object, source included; the 400 is where the API documents itself (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()), indent=1)
    except ValueError:
        return r.text


def show(r, label):
    rows.append(f"  {r.status_code} {label}:")
    rows.append("   " + err(r).replace("\n", "\n   "))


def search(entity, filt, fields=("code",), size=500, project=None):
    body = {"filters": ([["project", "is", {"type": "Project", "id": project}]] if project else []) + filt,
            "fields": list(fields), "page": {"size": size}}
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    return len(r.json()["data"]), r.json()["data"]


def props(entity, field, project=None):
    p = {"project_id": project} if project else None
    r = c.get(f"/schema/{entity}/fields/{field}", params=p)
    if not r.ok:
        return {}, {}
    d = r.json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items() if k != "properties"}
    return flat, {k: v.get("value") for k, v in (d.get("properties") or {}).items()}


def links_of(pid, field="versions"):
    """The link list as the API returns it, in the order it returns it."""
    r = c.get(f"/entity/playlists/{pid}", params={"fields": field})
    data = ((r.json().get("data", {}).get("relationships") or {}).get(field) or {}).get("data") or []
    return [x["id"] for x in data]


rows.append("=== the REST path slug, called rather than guessed")
for slug in ("playlists", "playlist", "Playlist", "playlistss"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    tail = "" if r.ok else json.dumps(r.json()["errors"][0].get("detail"))
    rows.append(f"  GET /entity/{slug:11s} -> {r.status_code} {tail}")
r = c.get("/entity/playlists", params={"page[size]": 1, "fields": "code"})
if r.ok and r.json()["data"]:
    rows.append(f"  one row: {json.dumps(r.json()['data'][0])}")
    _lib.note_from(r.json())

rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/Playlist/fields").json()["data"]
pf, pp = props("Playlist", "project")
rows.append(f"  Playlist.project data_type={pf.get('data_type')} mandatory={pf.get('mandatory')} "
            f"editable={pf.get('editable')} valid_types={pp.get('valid_types')}")
site_n, _ = search("playlists", [], size=500)
proj_n, _ = search("playlists", [], size=500, project=PROJECT)
rows.append(f"  _search with no project filter -> {site_n} rows (page size 500, site-wide)")
rows.append(f"  _search filtered to the sample project -> {proj_n} rows")

rows.append("\n=== identity")
cf, cp = props("Playlist", "code")
rows.append(f"  Playlist.code name={cf.get('name')!r} data_type={cf.get('data_type')} "
            f"mandatory={cf.get('mandatory')} unique={cf.get('unique')} editable={cf.get('editable')}")
rows.append(f"  fields flagged mandatory: {sorted(k for k, v in schema.items() if (v.get('mandatory') or {}).get('value'))}")
rows.append(f"  fields flagged unique:    {sorted(k for k, v in schema.items() if (v.get('unique') or {}).get('value'))}")
rows.append(f"  total fields in /schema/Playlist/fields: {len(schema)}; "
            f"read only: {len([k for k, v in schema.items() if not (v.get('editable') or {}).get('value')])}")
rows.append(f"  read-only field names: {sorted(k for k, v in schema.items() if not (v.get('editable') or {}).get('value'))}")

rows.append("\n=== versions, the field that is the type (field_types/multi_entity)")
vf, vp = props("Playlist", "versions")
rows.append(f"  Playlist.versions data_type={vf.get('data_type')} editable={vf.get('editable')} "
            f"mandatory={vf.get('mandatory')} valid_types={vp.get('valid_types')}")
rows.append(f"  Version.playlists (the reverse): {props('Version', 'playlists')[0].get('data_type')} "
            f"valid_types={props('Version', 'playlists')[1].get('valid_types')} "
            f"editable={props('Version', 'playlists')[0].get('editable')}")

rows.append("\n=== is there an order field anywhere")
sortish = sorted(k for k in schema if "sort" in k or "order" in k)
rows.append(f"  Playlist fields matching sort/order: {sortish}")
types = c.get("/schema").json()["data"]
conns = sorted(k for k in types if "Playlist" in k)
rows.append(f"  schema types naming Playlist: {conns}")
for t in conns:
    if t == "Playlist":
        continue
    r = c.get(f"/schema/{t}/fields")
    if not r.ok:
        rows.append(f"  /schema/{t}/fields -> {r.status_code}")
        continue
    cs = r.json()["data"]
    rows.append(f"  {t}: {len(cs)} fields = {sorted(cs)}")
    for k in sorted(cs):
        if "sort" in k or "order" in k:
            f2, p2 = props(t, k)
            rows.append(f"    {t}.{k} data_type={f2.get('data_type')} editable={f2.get('editable')}")

rows.append("\n=== link fields with valid_types")
links = {k: v for k, v in schema.items()
         if (v.get("data_type") or {}).get("value") in ("entity", "multi_entity")}
n, data = search("playlists", [], fields=("code", *sorted(links)), size=500, project=PROJECT)
filled = {}
for d in data if isinstance(n, int) else []:
    for k, v in (d.get("relationships") or {}).items():
        if v.get("data"):
            filled[k] = filled.get(k, 0) + 1
for k in sorted(links):
    v = links[k]
    p = {kk: vv.get("value") for kk, vv in (v.get("properties") or {}).items()}
    vt = p.get("valid_types")
    vt = f"{len(vt)} types" if vt and len(vt) > 6 else vt
    rows.append(f"  {k:28s} {v['data_type']['value']:12s} editable={str((v.get('editable') or {}).get('value')):5s} "
                f"valid_types={vt}  filled on {filled.get(k, 0)}/{n}")

rows.append("\n=== status")
sf, sp = props("Playlist", "sg_status_list")
rows.append(f"  Playlist.sg_status_list -> {sf.get('data_type') or 'absent'}")
statusy = sorted(k for k, v in schema.items()
                 if (v.get("data_type") or {}).get("value") in ("status_list", "list"))
rows.append(f"  status_list / list fields on Playlist: {statusy}")
for k in statusy:
    f2, p2 = props("Playlist", k)
    rows.append(f"    {k}: {f2.get('data_type')} valid_values={p2.get('valid_values')} "
                f"default_value={p2.get('default_value')!r}")

rows.append("\n=== read order of an existing playlist, twice, from two endpoints")
n, data = search("playlists", [["versions", "is_not", None]], fields=("code", "versions"),
                 size=5, project=PROJECT)
if isinstance(n, int) and n:
    pid = data[0]["id"]
    a = [x["id"] for x in ((data[0].get("relationships") or {}).get("versions") or {}).get("data") or []]
    b = links_of(pid)
    n2, d2 = search("playlists", [["id", "is", pid]], fields=("code", "versions"), size=1)
    cc = [x["id"] for x in ((d2[0].get("relationships") or {}).get("versions") or {}).get("data") or []] if isinstance(n2, int) and n2 else []
    rows.append(f"  playlist {pid}: {len(a)} versions")
    rows.append(f"  _search order == GET order:      {a == b}")
    rows.append(f"  _search order == second _search: {a == cc}")
    rows.append(f"  first 6 ids from _search: {a[:6]}")
    rows.append(f"  first 6 ids from GET:     {b[:6]}")
    rows.append(f"  ascending by id: {a == sorted(a)}")
else:
    rows.append(f"  no playlist with versions in the sample project ({n}); order read skipped")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the create contract, order and add mode)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    with _lib.Created(c) as made:
        rows.append("\n=== three versions to play with, coded so name order reverses id order")
        vids = []
        for i in ("ccc", "bbb", "aaa"):
            r = c.post("/entity/versions", headers=JSN,
                       json={"project": {"type": "Project", "id": SANDBOX}, "code": f"zzprobe_pl_v_{i}"})
            vids.append(made.add("versions", r.json()["data"]["id"]))
        rows.append(f"  A={vids[0]} zzprobe_pl_v_ccc, B={vids[1]} zzprobe_pl_v_bbb, C={vids[2]} zzprobe_pl_v_aaa")
        rows.append("  ascending by id: A B C. ascending by code: C B A")
        NAME = {vids[0]: "A", vids[1]: "B", vids[2]: "C"}

        def lbl(ids):
            return " ".join(NAME.get(i, str(i)) for i in ids)
        V = [{"type": "Version", "id": i} for i in vids]

        rows.append("\n=== create contract (probe 012: mandatory is not the contract)")
        for label, body in [
            ("neither", {}),
            ("code alone", {"code": "zzprobe_playlist_code_only"}),
            ("project alone", {"project": {"type": "Project", "id": SANDBOX}}),
            ("project + code", {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_playlist_a"}),
        ]:
            r = c.post("/entity/playlists", headers=JSN, json=body)
            if r.ok:
                d = r.json()["data"]
                made.add("playlists", d["id"])
                rows.append(f"  {r.status_code} {label}: id={d['id']} attributes={json.dumps(d['attributes'])}")
            else:
                show(r, label)

        r = c.post("/entity/playlists", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_playlist_a"})
        if r.ok:
            made.add("playlists", r.json()["data"]["id"])
            rows.append(f"  {r.status_code} the same code a second time: id={r.json()['data']['id']}")
        else:
            show(r, "the same code a second time")

        rows.append("\n=== versions set in the POST body, C B A")
        r = c.post("/entity/playlists", headers=JSN,
                   json={"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_playlist_order",
                         "versions": [V[2], V[1], V[0]]})
        if not r.ok:
            show(r, "create with versions")
            pid = None
        else:
            pid = made.add("playlists", r.json()["data"]["id"])
            echoed = [x["id"] for x in (r.json()["data"]["relationships"].get("versions") or {}).get("data") or []]
            rows.append("  201 sent [C, B, A]")
            rows.append(f"      201 echo   {lbl(echoed)}")
            rows.append(f"      read back  {lbl(links_of(pid))}")

        if pid:
            rows.append("\n=== order on write, and whether it is readable")
            for label, order in (("[A, B, C]", [V[0], V[1], V[2]]), ("[C, B, A]", [V[2], V[1], V[0]]),
                                 ("[B, A, C]", [V[1], V[0], V[2]])):
                r = c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": order})
                got = links_of(pid)
                rows.append(f"  PUT versions {label:10s} -> {r.status_code}  reads back {lbl(got)}  "
                            f"as sent: {got == [x['id'] for x in order]}  "
                            f"ascending by code: {got == [vids[2], vids[1], vids[0]]}  "
                            f"ascending by id: {got == sorted(got)}")

            rows.append("\n=== add mode on Playlist.versions specifically (field_types/multi_entity)")
            c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": [V[0]]})
            rows.append(f"  reset to [A]: {lbl(links_of(pid))}")
            for label, payload in (
                ("bare [B]", [V[1]]),
                ("add [C]", {"multi_entity_update_mode": "add", "value": [V[2]]}),
                ("add [C] again", {"multi_entity_update_mode": "add", "value": [V[2]]}),
                ("remove [C]", {"multi_entity_update_mode": "remove", "value": [V[2]]}),
                ("set [A, B]", {"multi_entity_update_mode": "set", "value": [V[0], V[1]]}),
            ):
                r = c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": payload})
                rows.append(f"  {label:16s} -> {r.status_code} {lbl(links_of(pid))}")
            c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": [V[0]]})
            r = c.put(f"/entity/playlists/{pid}", params={"multi_entity_update_mode": "add"},
                      headers=JSN, json={"versions": [V[1]]})
            rows.append(f"  ?multi_entity_update_mode=add in the query string, from [A] sending [B] "
                        f"-> {r.status_code} {lbl(links_of(pid))}")

            rows.append("\n=== does add append at the end, or sort")
            c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": [V[2], V[1]]})
            rows.append(f"  set [C, B]: {lbl(links_of(pid))}")
            r = c.put(f"/entity/playlists/{pid}", headers=JSN,
                      json={"versions": {"multi_entity_update_mode": "add", "value": [V[0]]}})
            rows.append(f"  add [A]  -> {r.status_code} {lbl(links_of(pid))}")

            rows.append("\n=== the connection carrying sg_sort_order, addressed every way the slug can be spelled")
            for slug in ("playlistversionconnections", "PlaylistVersionConnection",
                         "playlist_version_connections", "playlistversionconnection",
                         "playlistshares", "PlaylistShare"):
                r = c.get(f"/entity/{slug}", params={"page[size]": 1})
                tail = "" if r.ok else json.dumps(r.json()["errors"][0].get("detail"))
                rows.append(f"  GET /entity/{slug:28s} -> {r.status_code} {tail}")

            def conns_of(plid):
                body = {"filters": [["playlist", "is", {"type": "Playlist", "id": plid}]],
                        "fields": ["sg_sort_order", "version"], "sort": ["sg_sort_order"],
                        "page": {"size": 100}}
                r = c.post("/entity/PlaylistVersionConnection/_search", headers=ARR, json=body)
                if not r.ok:
                    return f"ERR {r.status_code} " + err(r)
                return [(x["id"], x["attributes"].get("sg_sort_order"),
                         NAME.get((x["relationships"]["version"]["data"] or {}).get("id"), "?"))
                        for x in r.json()["data"]]

            rows.append(f"  Playlist.versions reads {lbl(links_of(pid))}")
            rows.append(f"  connections sorted by sg_sort_order (id, sg_sort_order, version): {conns_of(pid)}")

            rows.append("\n=== writing sg_sort_order on the connection, and whether the field write respects it")
            cur = conns_of(pid)
            for i, (cid, _, _) in enumerate(cur):
                r = c.put(f"/entity/PlaylistVersionConnection/{cid}", headers=JSN,
                          json={"sg_sort_order": len(cur) - i})
                if not r.ok:
                    show(r, f"PUT sg_sort_order on connection {cid}")
                    break
            rows.append(f"  reversed sg_sort_order -> {conns_of(pid)}")
            rows.append(f"  Playlist.versions still reads {lbl(links_of(pid))}")
            r = c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": [V[0], V[1], V[2]]})
            rows.append(f"  bare-list PUT of the same three -> {r.status_code}; connections {conns_of(pid)}")
            r = c.put(f"/entity/playlists/{pid}", headers=JSN,
                      json={"versions": {"multi_entity_update_mode": "remove", "value": [V[0]]}})
            r = c.put(f"/entity/playlists/{pid}", headers=JSN,
                      json={"versions": {"multi_entity_update_mode": "add", "value": [V[0]]}})
            rows.append(f"  remove A then add A back -> {r.status_code}; connections {conns_of(pid)}")

            rows.append("\n=== creating the connection row directly, order and link in one call")
            c.put(f"/entity/playlists/{pid}", headers=JSN,
                  json={"versions": {"multi_entity_update_mode": "remove", "value": [V[0]]}})
            for label, body in (
                ("playlist + version + sg_sort_order",
                 {"playlist": {"type": "Playlist", "id": pid},
                  "version": {"type": "Version", "id": vids[0]}, "sg_sort_order": 99}),
                ("a second row for the same pair",
                 {"playlist": {"type": "Playlist", "id": pid},
                  "version": {"type": "Version", "id": vids[0]}, "sg_sort_order": 5}),
            ):
                r = c.post("/entity/PlaylistVersionConnection", headers=JSN, json=body)
                if r.ok:
                    made.add("PlaylistVersionConnection", r.json()["data"]["id"])
                    rows.append(f"  {r.status_code} {label}: id={r.json()['data']['id']}; "
                                f"Playlist.versions now {lbl(links_of(pid))}")
                else:
                    show(r, label)
            rows.append(f"  connections {conns_of(pid)}")

            rows.append("\n=== writing the link from the Version side")
            r = c.put(f"/entity/versions/{vids[1]}", headers=JSN,
                      json={"playlists": {"multi_entity_update_mode": "add",
                                          "value": [{"type": "Playlist", "id": pid}]}})
            rows.append(f"  PUT Version.playlists add [this playlist] -> {r.status_code}; "
                        f"Playlist.versions now {lbl(links_of(pid))}")

            rows.append("\n=== can a playlist span projects")
            n2, d2 = search("versions", [], fields=("code",), size=1, project=PROJECT)
            if isinstance(n2, int) and n2:
                foreign = d2[0]["id"]
                r = c.put(f"/entity/playlists/{pid}", headers=JSN,
                          json={"versions": {"multi_entity_update_mode": "add",
                                             "value": [{"type": "Version", "id": foreign}]}})
                rows.append(f"  sandbox playlist, add a Version from another project -> {r.status_code}")
                if r.ok:
                    rows.append(f"    reads back {lbl(links_of(pid))} with the foreign version, id {foreign}")
                else:
                    rows.append("   " + err(r).replace("\n", "\n   "))
                r = c.put(f"/entity/playlists/{pid}", headers=JSN, json={"versions": [V[0]]})
                rows.append(f"  reset -> {r.status_code} {lbl(links_of(pid))}")
            else:
                rows.append("  no version in the sample project to try; skipped")

            rows.append("\n=== moving the playlist itself between projects")
            r = c.put(f"/entity/playlists/{pid}", headers=JSN,
                      json={"project": {"type": "Project", "id": PROJECT}})
            rows.append(f"  PUT project -> {r.status_code}")
            if not r.ok:
                rows.append("   " + err(r).replace("\n", "\n   "))
            else:
                c.put(f"/entity/playlists/{pid}", headers=JSN,
                      json={"project": {"type": "Project", "id": SANDBOX}})
                rows.append("  moved back to the sandbox")

            rows.append("\n=== read-only fields, written")
            for k in ("versions_count", "created_at", "id"):
                if k not in schema:
                    continue
                r = c.put(f"/entity/playlists/{pid}", headers=JSN, json={k: 99})
                rows.append(f"  PUT {k}=99 -> {r.status_code}")
                if not r.ok:
                    rows.append("   " + err(r).replace("\n", "\n   "))

actual = "\n".join(rows)
_lib.emit("entity_types/Playlist", actual, env)
