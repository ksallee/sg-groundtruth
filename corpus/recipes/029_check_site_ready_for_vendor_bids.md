---
intent: Check that a site's Vendor permission group is set up for bidding, from its rules, before an app relies on it
tags: [permission, sudo, custom-entity, group]
endpoints: [GET /schema, GET /schema/<Type>/fields, GET /schema/permission_groups/<code>/entity_types/<Type>]
scope: api
measured: site-wide, 2026-11-20, read only, as an Admin person via sudo; the person form from probe 162
---

# 029_check_site_ready_for_vendor_bids

A bidding app needs three things from the site: its fields, a see rule that shows a Shot to the vendor
it was awarded to, and see rules that keep one vendor's Bids from another. Rules are readable over REST
and never writable (probe 162), so the app checks them and reports what an administrator has to add in
the web interface.

## Call

```python
import json
import sys

sys.path.insert(0, "src")
from sg_groundtruth.client import FPT
from sg_groundtruth.env import load

env = load(".")
c = FPT.from_env(env, sudo_as_login="<an active Admin's login>")   # the script alone reads no HumanUser group
GROUP = "vendor"                                       # the code of the Vendor permission group
VENDOR_FIELD = "sg_zzprobe_163_vendor_groups"           # the app's multi_entity of Group on Bid
LINK_TO_BID = "sg_zzprobe_163_bid"                      # the app's entity link from Bid Line to Bid


def slots():
    """Custom entities by display name: the slot differs per site."""
    return {v["name"]["value"]: t for t, v in c.get("/schema").json()["data"].items()
            if t.startswith("CustomEntity") and v["name"]["value"] in ("Bid", "Bid Line")}


def rights(entity_type):
    r = c.get(f"/schema/permission_groups/{GROUP}/entity_types/{entity_type}")
    if r.status_code in (403, 404):
        raise SystemExit(f"cannot read group {GROUP!r}: {r.json()['errors'][0]}")
    return r.json()["data"]


def leaves(cond):
    if not cond:
        return []
    if "conditions" in cond:
        return [x for k in cond["conditions"] for x in leaves(k)]
    return [cond]


def is_me(value, me):
    """An Admin reads the token; the person reading their own group reads their own row."""
    return value.get("valid") == "logged_in_user_token" or (
        me is not None and value.get("type") == "HumanUser" and value.get("id") == me)


def seen_through(r, path, me=None):
    """True when the group's read is conditional on `path` holding the signed-in person."""
    read = r["actions"]["read"]
    return read["access"] == "conditional" and any(
        x.get("path") == path and x.get("relation") == "is" and any(is_me(v, me) for v in x.get("values", []))
        for x in leaves(read.get("condition")))


s = slots()
if set(s) != {"Bid", "Bid Line"}:
    raise SystemExit(f"enable custom entities displayed Bid and Bid Line; found {s}")
bid, line, shot = rights(s["Bid"]), rights(s["Bid Line"]), rights("Shot")
fields = {t: c.get(f"/schema/{s[t]}/fields").json()["data"] for t in s}
check = {
    "Bid has the vendor Group field": VENDOR_FIELD in fields["Bid"],
    "Bid Line links its Bid": LINK_TO_BID in fields["Bid Line"],
    "a Shot is seen through sg_vendor_groups.Group.users": seen_through(shot, "sg_vendor_groups.Group.users"),
    "a Shot is seen through sg_vendor_groups.Group.sg_people": seen_through(shot, "sg_vendor_groups.Group.sg_people"),
    "a Bid is seen only by its vendor": seen_through(bid, f"{VENDOR_FIELD}.Group.users"),
    "a Bid Line is seen only by its Bid's vendor": seen_through(line, f"{LINK_TO_BID}.{s['Bid']}.{VENDOR_FIELD}.Group.users"),
    "the vendor may create Bid Lines": line["actions"]["create"]["access"] != "denied",
}
for k, v in check.items():
    print(f"{'ok  ' if v else 'MISS'} {k}")
print("Bid read:", json.dumps(bid["actions"]["read"]), "| Bid Line create:", json.dumps(line["actions"]["create"]))
```

## Response

On the probed site, with the probe's fields in place and the Vendor group as it stands:

```
ok   Bid has the vendor Group field
ok   Bid Line links its Bid
ok   a Shot is seen through sg_vendor_groups.Group.users
ok   a Shot is seen through sg_vendor_groups.Group.sg_people
MISS a Bid is seen only by its vendor
MISS a Bid Line is seen only by its Bid's vendor
MISS the vendor may create Bid Lines
Bid read: {"access": "allowed"} | Bid Line create: {"access": "denied"}
```

## Notes

- Read as an Admin person, or as the vendor themselves with `me` set to their HumanUser id: a person
  reading their own group gets their own row in place of `logged_in_user_token`, so a check matching the
  token alone answers `MISS` for a rule that is there (probe 162). The script, an API Admin, gets 404
  `Unknown permission group code 'vendor'`; a person asking for another group gets 403.
- `read: allowed` is every row (probe 163). A `MISS` on the two Bid lines means every vendor reads every
  Bid, whatever the app filters.
- A rule on Bid alone is not enough. A Bid Line visible to everyone still answers a filter on its Bid's
  fields and groups its total, and the event log shows values written to hidden rows (probe 165).
  Check Bid Line, and whether Vendor reads `EventLogEntry`.
- The rule's path must be the one the app writes. A rule naming `users` ignores `sg_people` (probe 166).
- "See entities in assigned Projects only" has no key in these responses. Its effect is that an award
  reaches a vendor only in a project they are assigned to (probe 166); check `HumanUser.projects`.
- No REST call adds a missing rule (probe 162). Report the `MISS` lines to an administrator.
