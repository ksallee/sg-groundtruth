---
tags: [schema, custom-field, discovery]
endpoints: [GET /schema/<Type>/fields, GET /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: site-wide, seven entity types and 439 fields, schema reads only
verdict: A field with `visible.editable` false is stock and safe to depend on; true means the site can hide it, which is every custom field and a few stock ones. The `sg_` prefix decides nothing.
---

# 056_stock_vs_custom_field

**Q** Does `/schema/<Type>/fields` say which fields a client can depend on finding on someone else's
site?

**Endpoint** `GET /schema/<Type>/fields ; GET /schema/<Type>/fields/<field>`

**Docs claim** Silent. The schema is documented as a field listing with no flag distinguishing a
stock field from one the site added.

**Actual**

```
each field carries: custom_metadata data_type description editable entity_type mandatory name
                    properties ui_value_displayable unique visible
each is {"value": …, "editable": …}; `visible.editable` says whether the site may hide the field

type          fields  visible.editable true  named sg_*  true and not sg_*
PublishedFile     33                      7           8  []
Version           71                     14          30  ['platform_status',
                                                          'version_sg_ai_generated_from_versions']
Shot             100                     32          39  ['platform_status']
Task              56                      8          10  []
Asset             72                     26          28  []
Project           42                      9           9  ['code']
HumanUser         65                      1           2  []
                 439                     97         126  4

sg_* with visible.editable false, on Version alone: sg_first_frame sg_last_frame sg_path_to_movie
  sg_path_to_frames sg_path_to_geometry sg_status_list sg_task sg_uploaded_movie
  sg_uploaded_movie_mp4 sg_uploaded_movie_webm sg_uploaded_movie_image
  sg_uploaded_movie_frame_rate sg_uploaded_movie_transcoding_status sg_version_type
  sg_movie_has_slate sg_movie_aspect_ratio sg_frames_have_slate sg_frames_aspect_ratio

Version.sg_status_list    visible {"value": true, "editable": false}   data_type status_list
Version.sg_uploaded_movie visible {"value": true, "editable": false}   data_type url
Project.code              visible {"value": true, "editable": true}    data_type text, name "Code"
Version.platform_status   visible {"value": true, "editable": true}    data_type text
```

**Teaches**
- **`visible.editable` is the flag, and it reads one way round.** `false` means the site cannot hide
  the field, and no custom field on the probed site read `false`. `true` is "the site may hide this",
  which every custom field is and a few stock fields are as well, so it is a strong hint and not a
  proof.
- **The `sg_` prefix decides nothing in either direction.** On the probed site 126 of 439 fields are named
  with it and 33 of those are stock, `sg_status_list` and the whole `sg_uploaded_movie` family among them.
  Probe 019 explains the other half: a field created over REST is named `sg_<display name>` whatever
  the caller passes, so the prefix marks how a field was named, not who added it.
- On the probed site 4 of 97 `visible.editable` fields are not prefixed.
  `version_sg_ai_generated_from_versions` is the reverse side of a custom `multi_entity` field, so it
  is custom under a generated name. `Project.code` and `platform_status` on Version and Shot are stock.
  Reading `visible.editable` as "custom" would have called all four wrong.
- Nothing in the schema names the origin of a field. `custom_metadata` is `""` on all 439, and
  `visible.value` is `true` on all 439, so neither separates anything. A client that needs certainty
  reads `/schema/<Type>/fields` on the site it is about to write to and matches on the programmatic
  name (probe 002), rather than deciding from a name it learned somewhere else.
