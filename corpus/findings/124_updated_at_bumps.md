---
tags: [observe, upload, link, multi-entity, on-set]
endpoints: [PUT /entity/<type>/<id>, POST /entity/<type>, POST /entity/<type>/_search, POST <links.complete_upload>]
phase: observe
scope: api
measured: sandbox project written, 2026-11-11; one Slate, Scene, Shot, Version and Note, all deleted
verdict: `updated_at` moves on a write, a finished upload and its transcode, and on a link set from either end, but not on a no-op PUT and not when a Note names the row in `note_links`.
---

# 124_updated_at_bumps

**Q** Which writes move a record's `updated_at`: a finished upload, a link added from the other side,
a write that changes nothing?

**Endpoint** `PUT /entity/<type>/<id> ; POST /entity/<type> ; POST <links.complete_upload>`

**Docs claim** Silent. `updated_at` is described as the time the record was last updated.

**Actual**

```
on a Slate                                                     updated_at
  PUT description "a"                                    200   moved
  PUT description "a" again                              200   same
  image: _upload, PUT, complete_upload                   201   moved, at the complete
  image: transcode finishes, placeholder replaced              moved again, 35 s later
  a Version created with entity=<the Slate>              201   moved
  a Note created with note_links=[<the Slate>]           201   same
  that Version's entity set to null                      200   moved

on a Scene, the stock pair Shot.sg_scene / Scene.shots
  PUT Shot.sg_scene = <the Scene>                        200   Scene moved
  PUT Shot.sg_scene = null                               200   Scene moved
  PUT Scene.shots = [<the Shot>]                         200   Scene moved, and the Shot moved
                                                               to the same second

on a Version
  sg_uploaded_movie: _upload, PUT, complete_upload       201   moved
  transcode finishes                                           moved again, 36 s later

POST /entity/versions/_search  [["updated_at", "greater_than", <stamp before the transcode>]]
  -> 200, 2 rows
```

**Teaches**
- A `greater_than` cursor on `updated_at` sees a finished upload twice: once at `complete_upload`
  and once when the server finishes the thumbnail. Treat the second as a server write, not an edit
  to merge.
- A link written on one end moves the stamp on both rows: `Shot.sg_scene` and `Scene.shots` each
  moved the other. On the probed site a Version's `entity` moved the Slate it named; that Slate has
  a site field `sg_versions` listing the Version, and whether a Slate without it moves is unmeasured.
- A new Note whose `note_links` names a Slate leaves the Slate's stamp alone, although every
  on-set type has a stock `notes` field (probe 122). Poll Notes by their own `updated_at` or `created_at`, filtered on `note_links`.
- A PUT that sends the stored value is a no-op and does not move the stamp, so the cursor does not
  echo a client's own idempotent re-sends. Stamps are to the second; probe 024 covers read-after-write.
