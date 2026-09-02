---
tags: [version, media, published-file, path, storage, inspector, query]
verdict: All three tiers exist; only the LAST is reliable, and the first is not testable here. THE REUSABLE TRUTH: `path` on a PublishedFile arrives with the LocalStorage join ALREADY DONE - local_path_mac / local_path_windows / local_path_linux are filled by the server alongside relative_path and the local_storage hash, so a client NEVER reads LocalStorage or reassembles a root. But which types carry a path is not uniform: Maya Scene (5/5) and Alembic Cache (2/2) carry one and the files exist on the mount, Movie (4/4) carries one and NONE of the files exist, and Image, Rendered Image, Texture and USD carry NO path at all - so precisely the types a Fetch node wants are the ones with nothing to load. Traversal is worse: published_files is filled on 2 of 53 Versions and `version` is null on 180 of 182 PFs, so walking Version -> PublishedFile finds nothing on this site. Tier 2 sg_path_to_movie is filled 28/53 and the sampled paths DO exist, but they are ad-hoc user paths under Zenith and Thicket rather than a shared root - readable, not portable - and sg_path_to_frames is 0/53, so the %04d sequence form is untested. Tier 3 always resolves and needs no second call: `image` IS a presigned S3 URL as a plain string and sg_uploaded_movie is a dict carrying the same under `url`. Note sg_uploaded_movie cannot be filtered or summarized `is_not None` at all - 400, "'url' escarp type cannot be" - the same shape of trap as a checkbox (probe 020). Build the Fetch node on tier 3, keep tier 2 as an opt-in, and treat the PublishedFile tier as UNPROVEN until a site with a real cinder history exists to probe.
---

# 021_media_resolution

**Endpoint** `POST /entity/published_files/_search + GET /entity/versions`

**Docs claim** A Version's media resolves through its PublishedFiles, then its path fields, then the upload.

**Actual**

```
=== tier 1: PublishedFiles
  183 on the whole site:
    'GABLE2GABLE Willow Orchard [1765480725]'      1
    'Bo Kestrel'                        182

  by type, and whether `path` resolves to a file that exists:
    Alembic               2 PFs   0/2 sampled carry a path, 0 of those exist on disk
    Alembic Cache         2 PFs   2/2 sampled carry a path, 2 of those exist on disk
    Image                37 PFs   0/5 sampled carry a path, 0 of those exist on disk
    Maya Scene           56 PFs   5/5 sampled carry a path, 5 of those exist on disk
    Movie                 4 PFs   4/4 sampled carry a path, 0 of those exist on disk
    Rendered Image       20 PFs   0/5 sampled carry a path, 0 of those exist on disk
    Texture              12 PFs   0/5 sampled carry a path, 0 of those exist on disk
    USD                  43 PFs   0/5 sampled carry a path, 0 of those exist on disk

  the Version -> PublishedFile link, which is what a Fetch node would traverse:
    Versions carrying published_files      2/53
    PublishedFiles carrying a version link 2/182

=== the `path` field: the server has already done the LocalStorage join
  {
    "link_type": "local",
    "relative_path": "GIRDER/obsidian/Basalt/Gable/RIG/cinder/sable/gable.v003.ma",
    "local_path_mac": "/Updraft/GABLE/GIRDER/obsidian/Basalt/Gable/RIG/cinder/sable/gable.v003.ma",
    "local_path_windows": null,
    "local_path_linux": null,
    "local_storage": {
      "type": "LocalStorage",
      "id": 3,
      "name": "drift"
    }
  }
  LocalStorage entities on this site:
    3 {"code": "drift", "mac_path": "/Updraft/GABLE", "windows_path": null, "linux_path": null}

=== tier 2: the path fields on the Version itself
  sg_path_to_movie     28/53
  sg_path_to_frames    0/53
    exists=True  <home>/Zenith/juniper.juniper
    exists=True  <home>/Zenith/juniper.juniper
    exists=True  <home>/Zenith/juniper.juniper
    exists=True  <home>/Thicket/Nimbus Girder 25/fjord01_willow_prism01_prism_1k_kelp.quill

=== tier 3: uploaded media
  image             str -> presigned S3 URL in the field itself
  sg_uploaded_movie dict keys=['url', 'name', 'content_type', 'link_type', 'type', 'id']
  filtering sg_uploaded_movie is_not None -> 400 API summarize() Version.sg_uploaded_movie's 'url' escarp type cannot be
```

**Verdict** All three tiers exist; only the LAST is reliable, and the first is not testable here. THE REUSABLE TRUTH: `path` on a PublishedFile arrives with the LocalStorage join ALREADY DONE - local_path_mac / local_path_windows / local_path_linux are filled by the server alongside relative_path and the local_storage hash, so a client NEVER reads LocalStorage or reassembles a root. But which types carry a path is not uniform: Maya Scene (5/5) and Alembic Cache (2/2) carry one and the files exist on the mount, Movie (4/4) carries one and NONE of the files exist, and Image, Rendered Image, Texture and USD carry NO path at all - so precisely the types a Fetch node wants are the ones with nothing to load. Traversal is worse: published_files is filled on 2 of 53 Versions and `version` is null on 180 of 182 PFs, so walking Version -> PublishedFile finds nothing on this site. Tier 2 sg_path_to_movie is filled 28/53 and the sampled paths DO exist, but they are ad-hoc user paths under Zenith and Thicket rather than a shared root - readable, not portable - and sg_path_to_frames is 0/53, so the %04d sequence form is untested. Tier 3 always resolves and needs no second call: `image` IS a presigned S3 URL as a plain string and sg_uploaded_movie is a dict carrying the same under `url`. Note sg_uploaded_movie cannot be filtered or summarized `is_not None` at all - 400, "'url' escarp type cannot be" - the same shape of trap as a checkbox (probe 020). Build the Fetch node on tier 3, keep tier 2 as an opt-in, and treat the PublishedFile tier as UNPROVEN until a site with a real cinder history exists to probe.
