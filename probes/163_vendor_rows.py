"""Q: does a person in the Vendor group see every row of a custom entity in a project they are
assigned to, or only some?

sg-bids keeps one Bid per vendor and round. A vendor seeing another vendor's Bid sees their price.
Probe 162 read the Vendor group's rule on Bid as `read: allowed`, with no condition; this measures
what that means for rows. The script makes three Bids in the sandbox, one whose vendor groups field
holds group A, one holding group B, one holding none, and a Bid Line under each of the first two.
Vendor A and vendor B (`_bids.vendors`, re-roled for the run and restored) then list, fetch and
filter them.

Writes behind `--write`: the probe's fields if absent (`_bids.FIELDS`, left in place), rows
`zzprobe_163_*` deleted on exit, and the two people's permission group and Groups, restored.

    python probes/163_vendor_rows.py --write --people A,B --groups GA,GB
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bids  # noqa: E402
import _lib  # noqa: E402
from _bids import ARR, said  # noqa: E402

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 163 writes; run with --write --people A,B --groups GA,GB")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
S = _bids.slots(c)
BID, LINE = _bids.slug(S["Bid"]), _bids.slug(S["Bid Line"])
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


out("===== fields")
F = _bids.ensure_fields(c, S, out)
VG, LBID = F["zzprobe 163 vendor groups"], F["zzprobe 163 bid"]
GA, GB = _bids._ids("--groups")
NAMES = {}


def codes(r):
    if not r.ok:
        return said(r)
    return sorted(NAMES.get((x["type"], x["id"]), x["id"]) for x in r.json()["data"])


with _lib.Created(c) as made:
    ids = {}
    for tag, groups in (("A", [GA]), ("B", [GB]), ("none", [])):
        r = c.post(f"/entity/{BID}", json={"project": P, "code": f"zzprobe_163_bid_{tag}",
                                            VG: [{"type": "Group", "id": g} for g in groups]})
        ids[tag] = made.add(BID, r.json()["data"]["id"])
        NAMES[(S["Bid"], ids[tag])] = f"bid {tag}"
    for tag in ("A", "B"):
        r = c.post(f"/entity/{LINE}", json={"project": P, "code": f"zzprobe_163_line_{tag}",
                                             LBID: {"type": S["Bid"], "id": ids[tag]}})
        lid = made.add(LINE, r.json()["data"]["id"])
        NAMES[(S["Bid Line"], lid)] = f"line {tag}"
    out(f"\n===== rows, as the script: Bids {sorted(NAMES[(S['Bid'], i)] for i in ids.values())}, two Bid Lines")
    MINE = [["project", "is", P], ["code", "starts_with", "zzprobe_163"]]
    out(f"  script _search Bids -> {codes(c.post(f'/entity/{BID}/_search', headers=ARR, json={'filters': MINE, 'fields': ['code']}))}")

    with _bids.vendors(c, env, SB, out) as vs:
        for (pid, v, g, _), who in zip(vs, ("vendor A", "vendor B")):
            out(f"\n===== as {who}, a Vendor in group {'A' if g == GA else 'B'}")
            r = v.post(f"/entity/{BID}/_search", headers=ARR, json={"filters": MINE, "fields": ["code", VG]})
            out(f"  _search Bids in the sandbox -> {codes(r)}")
            r = v.post(f"/entity/{LINE}/_search", headers=ARR, json={"filters": MINE, "fields": ["code", LBID]})
            out(f"  _search Bid Lines in the sandbox -> {codes(r)}")
            for tag, i in ids.items():
                r = v.get(f"/entity/{BID}/{i}", params={"fields": f"code,{VG}"})
                vg = [x["id"] for x in r.json()["data"]["relationships"][VG]["data"]] if r.ok else None
                out(f"  GET bid {tag} -> {said(r)}" + (f"; vendor groups {['A' if x == GA else 'B' for x in vg]}" if r.ok else ""))
            r = v.get(f"/entity/{BID}", params={"filter[project.Project.id]": SB, "fields": "code"})
            out(f"  GET /entity/<Bid>?filter[project.Project.id]=<sandbox> -> {codes(r)}")
            mine = MINE + [[f"{VG}.Group.users", "is", {"type": "HumanUser", "id": pid}]]
            r = v.post(f"/entity/{BID}/_search", headers=ARR, json={"filters": mine, "fields": ["code"]})
            out(f"  _search with {VG}.Group.users is <themselves> -> {codes(r)}")
            r = v.post(f"/entity/{BID}/_summarize", headers=ARR, json={
                "filters": MINE, "summary_fields": [{"field": "id", "type": "count"}]})
            out(f"  _summarize count of Bids -> {said(r)} {r.json().get('data', {}).get('summaries') if r.ok else ''}")
    left = c.post(f"/entity/{BID}/_search", headers=ARR, json={"filters": MINE, "fields": ["id"]}).json()["data"]
    out(f"\n  zzprobe_163 Bids live before cleanup: {len(left)}")
_lib.emit("163_vendor_rows", "\n".join(rows), env)
