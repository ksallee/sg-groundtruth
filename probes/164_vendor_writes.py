"""Q: can a person in the Vendor group create or update a row of a custom entity, and which fields?

sg-bids wants a vendor to enter their own Bid Lines. Probe 143 measured an Artist on custom slots and
read the Vendor group's rights without exercising them; probe 162 read Vendor's rights on Bid and Bid
Line as create denied, update denied except `sg_status_list`. This sends the writes as vendor A, on a
Bid and a Bid Line the script made for group A: a create of each, by `POST` and inside `_batch`; an
update of every probe field and of `code`, `description` and `sg_status_list`; a delete. Next to
each, what the two calls a client could ask first predicted: `editable` in
`GET /schema/<Type>/fields?project_id=` read as the vendor, and the field's `update` in
`GET /schema/permission_groups/vendor/entity_types/<Type>/fields`.

Writes behind `--write`: the probe's fields if absent, rows `zzprobe_164_*` deleted on exit, and the
two people's permission group and Groups, restored.

    python probes/164_vendor_writes.py --write --people A,B --groups GA,GB
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
    raise SystemExit("probe 164 writes; run with --write --people A,B --groups GA,GB")
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
VG, LBID, LSHOT, AMT = (F["zzprobe 163 vendor groups"], F["zzprobe 163 bid"], F["zzprobe 163 shot"],
                        F["zzprobe currency amount"])
GA, GB = _bids._ids("--groups")

with _lib.Created(c) as made:
    shot = made.add("shots", c.post("/entity/shots", json={"project": P, "code": "zzprobe_164_shot",
                                                           "sg_vendor_groups": [{"type": "Group", "id": GA}]}).json()["data"]["id"])
    bid = made.add(BID, c.post(f"/entity/{BID}", json={"project": P, "code": "zzprobe_164_bid_A",
                                                        VG: [{"type": "Group", "id": GA}]}).json()["data"]["id"])
    line = made.add(LINE, c.post(f"/entity/{LINE}", json={
        "project": P, "code": "zzprobe_164_line_A", LBID: {"type": S["Bid"], "id": bid},
        LSHOT: {"type": "Shot", "id": shot}, AMT: 100.0}).json()["data"]["id"])
    out("\n===== rows, as the script: a Shot awarded to group A, Bid A for group A, a Bid Line on both")

    with _bids.vendors(c, env, SB, out) as vs:
        (pa, va, _, _), _ = vs
        for t, sl, row in ((S["Bid"], BID, bid), (S["Bid Line"], LINE, line)):
            name = "<Bid>" if t == S["Bid"] else "<Bid Line>"
            out(f"\n===== {name}, as vendor A")
            sch = va.get(f"/schema/{t}/fields", params={"project_id": SB}).json()["data"]
            ed = sorted(k for k, v in sch.items() if v["editable"]["value"])
            perm = va.get(f"/schema/permission_groups/vendor/entity_types/{t}/fields").json()["data"]["fields"]
            up = sorted(x["field_name"] for x in perm if x["update"]["access"] != "denied")
            out(f"  schema editable for the vendor: {ed}")
            out(f"  permission group fields, update not denied: {up}")
            body = {"project": P, "code": "zzprobe_164_vendor_create"}
            if t == S["Bid"]:
                body[VG] = [{"type": "Group", "id": GA}]
            else:
                body.update({LBID: {"type": S["Bid"], "id": bid}, AMT: 5.0})
            r = va.post(f"/entity/{sl}", json=body)
            out(f"  POST create -> {said(r)}")
            if r.status_code == 201:
                made.add(sl, r.json()["data"]["id"])
            r = va.post("/entity/_batch", json={"requests": [
                {"request_type": "create", "entity": t, "data": body}]})
            out(f"  _batch [create] -> {said(r)}")
            if r.ok:
                for x in r.json()["data"]:
                    made.add(sl, x["id"])
            vals = {"code": "zzprobe_164_by_vendor", "description": "by vendor", "sg_status_list": None}
            if t == S["Bid"]:
                vals[VG] = [{"type": "Group", "id": GA}, {"type": "Group", "id": GB}]
            else:
                vals.update({AMT: 250.0, LSHOT: None, LBID: {"type": S["Bid"], "id": bid}})
            for k, v in vals.items():
                r = va.put(f"/entity/{sl}/{row}", json={k: v})
                out(f"  PUT {k} -> {said(r)}")
            r = va.delete(f"/entity/{sl}/{row}")
            out(f"  DELETE -> {said(r)}; GET as the script after -> {c.get(f'/entity/{sl}/{row}').status_code}")
            if r.ok:
                made.rows.remove((sl, row))
_lib.emit("164_vendor_writes", "\n".join(rows), env)
