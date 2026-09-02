"""Q: how is an Asset addressed, what does creating one really require, and what does it link to?

Asset is the type a pipeline keys on by `code`, so the two things worth settling are whether `code` is
unique anywhere and whether the schema's `mandatory` flags are the create contract (probe 012 says no).

Read-only by default. `--write` adds the create attempts and the sg_asset_type writes, sandbox only,
every row deleted on the way out.
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


def search(entity, filt, fields=("code",), size=500, project=None):
    body = {"filters": ([["project", "is", {"type": "Project", "id": project}]] if project else []) + filt,
            "fields": list(fields), "page": {"size": size}}
    r = c.post(f"/entity/{entity}/_search", headers=ARR, json=body)
    if not r.ok:
        return f"ERR {r.status_code}", err(r)
    return len(r.json()["data"]), r.json()["data"]


def props(entity, field, project=None):
    p = {"project_id": project} if project else None
    d = c.get(f"/schema/{entity}/fields/{field}", params=p).json()["data"]
    flat = {k: (v.get("value") if isinstance(v, dict) else v) for k, v in d.items() if k != "properties"}
    return flat, {k: v.get("value") for k, v in (d.get("properties") or {}).items()}


rows.append("=== the REST path slug, called rather than guessed")
for slug in ("assets", "asset", "Asset", "assetss"):
    r = c.get(f"/entity/{slug}", params={"page[size]": 1})
    tail = "" if r.ok else json.dumps(r.json()["errors"][0].get("detail"))
    rows.append(f"  GET /entity/{slug:8s} -> {r.status_code} {tail}")
r = c.get("/entity/assets", params={"page[size]": 1, "fields": "code"})
rows.append(f"  one row: {json.dumps(r.json()['data'][0])}")
_lib.note_from(r.json())

rows.append("\n=== project-scoped or site-wide")
schema = c.get("/schema/Asset/fields").json()["data"]
pf, pp = props("Asset", "project")
rows.append(f"  Asset.project data_type={pf.get('data_type')} mandatory={pf.get('mandatory')} "
            f"editable={pf.get('editable')} valid_types={pp.get('valid_types')}")
site_n, _ = search("assets", [], size=500)
proj_n, _ = search("assets", [], size=500, project=PROJECT)
rows.append(f"  _search with no project filter -> {site_n} rows (page size 500, site-wide)")
rows.append(f"  _search filtered to the sample project -> {proj_n} rows")

rows.append("\n=== identity: code")
cf, cp = props("Asset", "code")
rows.append(f"  Asset.code name={cf.get('name')!r} data_type={cf.get('data_type')} "
            f"mandatory={cf.get('mandatory')} unique={cf.get('unique')} editable={cf.get('editable')}")
rows.append(f"  Asset fields flagged mandatory: {sorted(k for k, v in schema.items() if (v.get('mandatory') or {}).get('value'))}")
rows.append(f"  Asset fields flagged unique:    {sorted(k for k, v in schema.items() if (v.get('unique') or {}).get('value'))}")
n, data = search("assets", [], fields=("code", "project"), size=500)
if isinstance(n, int):
    codes, pairs = {}, {}
    for d in data:
        code = d["attributes"].get("code")
        proj = (d.get("relationships", {}).get("project", {}).get("data") or {}).get("id")
        codes[code] = codes.get(code, 0) + 1
        pairs[(proj, code)] = pairs.get((proj, code), 0) + 1
    dupe_site = {k: v for k, v in codes.items() if v > 1}
    dupe_proj = {k: v for k, v in pairs.items() if v > 1}
    _lib.note_names(*[k for k in list(codes)[:5] if k])
    rows.append(f"  over {n} assets site-wide: {len(codes)} distinct codes, "
                f"{len(dupe_site)} code(s) held by more than one asset site-wide")
    rows.append(f"  same rows keyed (project, code): {len(dupe_proj)} duplicated pair(s)")
    rows.append(f"  sample of site-wide duplicate codes: {list(dupe_site.items())[:3]}")

rows.append("\n=== sg_asset_type, the list field that categorises an asset (field_types/list)")
af, ap = props("Asset", "sg_asset_type")
rows.append(f"  data_type={af.get('data_type')} editable={af.get('editable')} mandatory={af.get('mandatory')}")
rows.append(f"  property keys: {sorted(ap)}")
rows.append(f"  valid_values={ap.get('valid_values')}  default_value={ap.get('default_value')!r}")
_, apj = props("Asset", "sg_asset_type", PROJECT)
rows.append(f"  project-scoped valid_values identical: {apj.get('valid_values') == ap.get('valid_values')}")
n, data = search("assets", [], fields=("code", "sg_asset_type"), size=500, project=PROJECT)
seen = {}
for d in data if isinstance(n, int) else []:
    v = d["attributes"].get("sg_asset_type")
    seen[repr(v)] = seen.get(repr(v), 0) + 1
rows.append(f"  distinct sg_asset_type over {n} assets in the sample project: {seen}")
VALID = ap.get("valid_values") or []
BOGUS = "zzprobe_asset_not_a_valid_value"
for label, filt in [(f"is {VALID[0]!r}", [["sg_asset_type", "is", VALID[0]]]),
                    (f"is {VALID[0].lower()!r} (wrong case)", [["sg_asset_type", "is", VALID[0].lower()]]),
                    (f"is {BOGUS!r} (negative control)", [["sg_asset_type", "is", BOGUS]]),
                    ("is null", [["sg_asset_type", "is", None]])]:
    k, _ = search("assets", filt, size=500, project=PROJECT)
    rows.append(f"    filter sg_asset_type {label} -> {k}")

rows.append("\n=== status")
sf, sp = props("Asset", "sg_status_list")
_, spj = props("Asset", "sg_status_list", PROJECT)
rows.append(f"  data_type={sf.get('data_type')} default_value={sp.get('default_value')!r}")
rows.append(f"  valid_values={sp.get('valid_values')}")
rows.append(f"  display_values={json.dumps(sp.get('display_values'))}")
rows.append(f"  hidden_values site-wide={sp.get('hidden_values')!r}  project {PROJECT}={spj.get('hidden_values')!r}")
n, data = search("assets", [], fields=("code", "sg_status_list"), size=500, project=PROJECT)
seen = {}
for d in data if isinstance(n, int) else []:
    v = d["attributes"].get("sg_status_list")
    seen[repr(v)] = seen.get(repr(v), 0) + 1
rows.append(f"  distinct sg_status_list over {n} assets in the sample project: {seen}")

rows.append("\n=== links: entity and multi_entity fields (field_types/entity, field_types/multi_entity)")
links = {k: v for k, v in schema.items()
         if (v.get("data_type") or {}).get("value") in ("entity", "multi_entity")}
link_fields = sorted(links)
n, data = search("assets", [], fields=("code", *link_fields), size=500, project=PROJECT)
filled = {}
for d in data if isinstance(n, int) else []:
    for k, v in (d.get("relationships") or {}).items():
        payload = v.get("data")
        if payload:
            filled[k] = filled.get(k, 0) + 1
for k in link_fields:
    v = links[k]
    p = {kk: vv.get("value") for kk, vv in (v.get("properties") or {}).items()}
    vt = p.get("valid_types")
    vt = f"{len(vt)} types" if vt and len(vt) > 6 else vt
    rows.append(f"  {k:34s} {(v['data_type']['value']):12s} editable={str((v.get('editable') or {}).get('value')):5s} "
                f"valid_types={vt}  filled on {filled.get(k, 0)}/{n}")

rows.append("\n=== the reverse side of the Shot and Sequence links")
for entity, field in (("Shot", "assets"), ("Sequence", "assets"), ("Asset", "shots"), ("Asset", "sequences")):
    try:
        f, p = props(entity, field)
        rows.append(f"  {entity}.{field}: {f.get('data_type')} valid_types={p.get('valid_types')}")
    except Exception as exc:  # a site without the field
        rows.append(f"  {entity}.{field}: absent ({exc})")
for entity, field in (("shots", "assets"), ("sequences", "assets")):
    k, _ = search(entity, [[field, "is_not", None]], size=500, project=PROJECT)
    tot, _ = search(entity, [], size=500, project=PROJECT)
    rows.append(f"  {entity} in the sample project with {field} populated: {k}/{tot}")

if not _lib.writes_allowed():
    rows.append("\n(read-only run; pass --write for the create contract and the sg_asset_type writes)")
else:
    SANDBOX = _lib.sandbox_id(c, env)
    rows.append(f"\n=== create contract, sandbox project (probe 012: mandatory is not the contract)")
    with _lib.Created(c) as made:
        attempts = [
            ("neither", {}),
            ("code alone", {"code": "zzprobe_asset_code_only"}),
            ("project alone", {"project": {"type": "Project", "id": SANDBOX}}),
            ("project + code", {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_asset_a"}),
        ]
        for label, body in attempts:
            r = c.post("/entity/assets", headers=JSN, json=body)
            if r.ok:
                d = r.json()["data"]
                made.add("assets", d["id"])
                rows.append(f"  {r.status_code} {label}: id={d['id']} attributes={json.dumps(d['attributes'])}")
            else:
                rows.append(f"  {r.status_code} {label}:")
                rows.append("   " + err(r).replace("\n", "\n   "))

        rows.append("\n=== is code unique per project? two assets, same code, same project")
        dup = {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_asset_a"}
        r = c.post("/entity/assets", headers=JSN, json=dup)
        if r.ok:
            made.add("assets", r.json()["data"]["id"])
            rows.append(f"  {r.status_code} second asset with the same code: id={r.json()['data']['id']}")
        else:
            rows.append(f"  {r.status_code} second asset with the same code:")
            rows.append("   " + err(r).replace("\n", "\n   "))

        rows.append("\n=== sg_asset_type on create and on update")
        base = {"project": {"type": "Project", "id": SANDBOX}, "code": "zzprobe_asset_type"}
        r = c.post("/entity/assets", headers=JSN, json=base)
        aid = made.add("assets", r.json()["data"]["id"]) if r.ok else None
        rows.append(f"  create with sg_asset_type omitted -> {r.status_code} "
                    f"reads back {json.dumps((r.json().get('data', {}).get('attributes') or {}).get('sg_asset_type'))}")
        for label, value in ((repr(VALID[0]), VALID[0]), (repr(VALID[0].lower()), VALID[0].lower()),
                             (repr(BOGUS), BOGUS)):
            r = c.put(f"/entity/assets/{aid}", headers=JSN, json={"sg_asset_type": value})
            if r.ok:
                rows.append(f"  PUT sg_asset_type {label} -> 200, reads back "
                            f"{json.dumps(r.json()['data']['attributes'].get('sg_asset_type'))}")
            else:
                rows.append(f"  PUT sg_asset_type {label} -> {r.status_code}")
                rows.append("   " + err(r).replace("\n", "\n   "))
        rows.append(f"  valid_values after the writes: {props('Asset', 'sg_asset_type')[1].get('valid_values')}")

        rows.append("\n=== linking to a Shot from the Asset side")
        sn, sdata = search("shots", [], size=1, project=SANDBOX)
        if isinstance(sn, int) and sn:
            shot = sdata[0]
            r = c.put(f"/entity/assets/{aid}", headers=JSN,
                      json={"shots": [{"type": "Shot", "id": shot["id"]}]})
            rows.append(f"  PUT Asset.shots [{{Shot, {shot['id']}}}] -> {r.status_code} "
                        f"{json.dumps((r.json().get('data', {}).get('relationships') or {}).get('shots', {}).get('data'))}")
            back, bdata = search("shots", [["assets", "is", {"type": "Asset", "id": aid}]], size=10)
            rows.append(f"  Shot._search assets is that Asset -> {back} row(s); the reverse field sees it")
        else:
            rows.append("  no shot in the sandbox to link; skipped")

actual = "\n".join(rows)
_lib.emit("entity_types/Asset", actual, env)
