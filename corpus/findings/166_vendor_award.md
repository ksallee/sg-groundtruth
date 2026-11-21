---
tags: [permission, sudo, group, shot, multi-entity]
endpoints: [PUT /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2026-11-20; one Shot, two Groups; two people re-roled to Vendor via sudo, restored
verdict: On the probed site a Group added to `Shot.sg_vendor_groups` shows the Shot to its people on their next request; removing it hides it. `sg_people` grants as `users` does; other projects stay hidden.
---

# 166_vendor_award

**Q** Does adding a Group to `Shot.sg_vendor_groups` make the Shot visible to that Group's people at
once, does removing it hide it, and does membership through `Group.sg_people` count as `Group.users`?

**Endpoint** `PUT /entity/shots/<id> ; PUT /entity/groups/<id> ; GET /entity/shots/<id> ; POST /entity/shots/_search`

**Docs claim** Silent. On the probed site the Vendor rule on Shot names both
`sg_vendor_groups.Group.users` and `sg_vendor_groups.Group.sg_people` (probe 162).

**Actual**

```
one sandbox Shot, written by the script; each vendor fetches it on the bearer it already holds,
straight after the write (about 1 s for the write and both reads)

step                                                   vendor A   vendor B
awarded to nobody                                      404        404
{"sg_vendor_groups": {"multi_entity_update_mode": "add", "value": [group A]}}   200   404
add group B                                            200        200
  vendor A reads sg_vendor_groups as [group A, group B]
remove group A                                         404        200
add group A back                                       200        200
vendor A moved from group A's users to its sg_people   200        200
vendor A in neither                                    404        200
vendor A back in users                                 200        200
{"sg_vendor_groups": []}                               404        404
no answer differed when asked again for up to 3 s

the Groups' Shots outside the sandbox, in a project neither vendor is assigned to
  group A: 10 Shots, vendor A reads 0          group B: 5 Shots, vendor B reads 0
```

**Teaches**
- Award with `{"multi_entity_update_mode": "add", "value": [<group>]}` and withdraw with `remove`
  (recipe 009). A bare list replaces the field, and with it every other vendor's award.
- The rule is evaluated per request: a bearer minted before the change sees the new answer on its next
  call, both ways. There is no token to refresh and no delay to wait out.
- `sg_people` counts because the rule names it. On another site read the rule first (probe 162): one
  naming only `users` ignores `sg_people`, which is a site field, not a stock one.
- On the probed site "See entities in assigned Projects only" holds: a Group's Shots in a project the
  person is not assigned to stay hidden. Here both vendors' `HumanUser.projects` held the sandbox
  alone; assign the vendor to the project before an award there can reach them.
- Vendor reads Groups (probe 162), so each vendor sees which other Groups hold a Shot they see.
