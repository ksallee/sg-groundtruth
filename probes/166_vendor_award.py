"""Q: does adding a Group to `Shot.sg_vendor_groups` make the Shot visible to that Group's people at
once, does removing it hide it again, and does membership through `Group.sg_people` count the same as
`Group.users`?

sg-bids awards a Shot by adding the winning vendor's Group to the Shot. On the probed site the Vendor
group's see rule on Shot names `sg_vendor_groups.Group.users` and `sg_vendor_groups.Group.sg_people`
(probe 162). The script makes one Shot in the sandbox awarded to nobody, then adds and removes the
two Groups with `multi_entity_update_mode` (recipe 009) and moves vendor A between `users` and
`sg_people`. After each write, vendor A and vendor B fetch the Shot on the bearer they already hold,
at once and again for up to 3 s if the answer is not the expected one. The Groups' Shots in projects
the vendors are not assigned to are counted, read only, for the "assigned projects only" setting.

Writes behind `--write`: the probe's Shot, deleted on exit, and the two people's permission group and
Groups, restored.

    python probes/166_vendor_award.py --write --people A,B --groups GA,GB
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _bids  # noqa: E402
import _lib  # noqa: E402
from _bids import ARR, said  # noqa: E402

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 166 writes; run with --write --people A,B --groups GA,GB")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
GA, GB = _bids._ids("--groups")
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def group(g):
    return {"type": "Group", "id": g}


def award(shot, mode, g):
    return c.put(f"/entity/shots/{shot}", json={"sg_vendor_groups": {"multi_entity_update_mode": mode, "value": [group(g)]}})


def sees(v, shot, expect):
    """(status at once, ms after the write, and the status after up to 3 s when it differed)."""
    t0 = time.time()
    r = v.get(f"/entity/shots/{shot}", params={"fields": "code,sg_vendor_groups"})
    first = r.status_code
    late = None
    if (first == 200) != expect:
        for _ in range(6):
            time.sleep(0.5)
            r = v.get(f"/entity/shots/{shot}", params={"fields": "code"})
            if (r.status_code == 200) == expect:
                late = f"{r.status_code} after {time.time() - t0:.1f}s"
                break
        late = late or f"still {r.status_code} after {time.time() - t0:.1f}s"
    return first, late, r


with _lib.Created(c) as made:
    shot = made.add("shots", c.post("/entity/shots", json={"project": P, "code": "zzprobe_166_shot"}).json()["data"]["id"])
    with _bids.vendors(c, env, SB, out) as vs:
        (pa, va, _, snap), (pb, vb, _, _) = vs
        out("\n===== one Shot, written by the script; each vendor fetches it on the bearer it already holds")
        out("  step                                         vendor A        vendor B")

        def step(label, expect_a, expect_b, write=None):
            t = time.time()
            w = write() if write else None
            a, la, ra = sees(va, shot, expect_a)
            b, lb, _ = sees(vb, shot, expect_b)
            out(f"  {label:<44} {a}{' -> ' + la if la else '':<14} {b}{' -> ' + lb if lb else ''}"
                + (f"   (write {said(w)}, {1000 * (time.time() - t):.0f} ms for write and both reads)" if w is not None else ""))
            return ra

        step("awarded to nobody", False, False)
        step("add group A", True, False, lambda: award(shot, "add", GA))
        ra = step("add group B", True, True, lambda: award(shot, "add", GB))
        if ra.ok:
            vg = [x["id"] for x in ra.json()["data"]["relationships"]["sg_vendor_groups"]["data"]]
            out(f"    vendor A reads sg_vendor_groups as {['A' if x == GA else 'B' if x == GB else x for x in vg]}")
        step("remove group A", False, True, lambda: award(shot, "remove", GA))
        step("add group A back", True, True, lambda: award(shot, "add", GA))
        step("vendor A: users -> sg_people", True, True,
             lambda: _bids.set_membership(c, snap, GA, pa, users=False, sg_people=True))
        step("vendor A: in neither", False, True,
             lambda: _bids.set_membership(c, snap, GA, pa, users=False, sg_people=False))
        step("vendor A: users again", True, True,
             lambda: _bids.set_membership(c, snap, GA, pa, users=True, sg_people=False))
        step("set [] (both groups removed)", False, False,
             lambda: c.put(f"/entity/shots/{shot}", json={"sg_vendor_groups": []}))

        out("\n===== the Groups' Shots outside the sandbox, read only")
        for g, v, who in ((GA, va, "A"), (GB, vb, "B")):
            mine = c.post("/entity/shots/_search", headers=ARR, json={
                "filters": [["sg_vendor_groups", "is", group(g)]], "fields": ["project"], "page": {"size": 200}}).json()["data"]
            other = [x for x in mine if x["relationships"]["project"]["data"]["id"] != SB]
            seen = v.post("/entity/shots/_search", headers=ARR, json={
                "filters": [["sg_vendor_groups", "is", group(g)]], "fields": ["project"], "page": {"size": 200}})
            seen_other = [x for x in seen.json()["data"] if x["relationships"]["project"]["data"]["id"] != SB] if seen.ok else said(seen)
            projects = sorted({x["relationships"]["project"]["data"]["id"] for x in other})
            assigned = snap["people"][pa if g == GA else pb]["projects"]
            out(f"  group {who}: script reads {len(other)} Shots in {len(projects)} other project(s), "
                f"none of them in vendor {who}'s projects: {not set(projects) & set(assigned)}; "
                f"vendor {who} reads {len(seen_other) if isinstance(seen_other, list) else seen_other}")
_lib.emit("166_vendor_award", "\n".join(rows), env)
