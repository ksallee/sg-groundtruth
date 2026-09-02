---
tags: [version, media, published-file, path, storage, inspector, query]
scope: api
verdict: PublishedFile.path is returned with the LocalStorage join already done (local_path_mac/windows/linux are server-filled), so a client never reads LocalStorage or reassembles a root.
---

# 021_media_resolution

**Q** Which of the three media tiers on a Version (its PublishedFiles, its path fields, the upload) can be resolved, and where does `path` come from?

**Endpoint** `POST /entity/published_files/_search + POST /entity/versions/_summarize`

**Docs claim** Silent on resolution order; the operator's claim is PublishedFiles first, then `sg_path_to_movie`/`sg_path_to_frames`, then the upload.

**Actual**

```
=== tier 1: PublishedFiles — 183 site-wide, 182 of them in project demo_show
  by type, and whether `path` resolves to a file that exists on disk:
    Alembic               2 PFs   0/2 sampled carry a path, 0 of those exist on disk
    Alembic Cache         2 PFs   2/2 sampled carry a path, 2 of those exist on disk
    Image                37 PFs   0/5 sampled carry a path, 0 of those exist on disk
    Maya Scene           56 PFs   5/5 sampled carry a path, 5 of those exist on disk
    Movie                 4 PFs   4/4 sampled carry a path, 0 of those exist on disk
    Rendered Image       20 PFs   0/5 sampled carry a path, 0 of those exist on disk
    Texture / USD     12+43 PFs   0/5 sampled carry a path, 0 of those exist on disk
  Versions carrying published_files 2/53 ; PublishedFiles carrying a version link 2/182
=== the `path` field: the server has already done the LocalStorage join
  {
    "link_type": "local",
    "relative_path": "demo_show/assets/Character/charA/RIG/publish/maya/charA.v003.ma",
    "local_path_mac": "/mnt/projects/demo_show/assets/Character/charA/RIG/publish/maya/charA.v003.ma",
    "local_path_windows": null,
    "local_path_linux": null,
    "local_storage": {"type": "LocalStorage", "id": 3, "name": "primary"}
  }
  the only LocalStorage on this site:
    3 {"code": "primary", "mac_path": "/mnt/projects", "windows_path": null, "linux_path": null}
=== tier 2: the path fields on the Version itself
  sg_path_to_movie 28/53 ; sg_path_to_frames 0/53 — all absolute, all ad-hoc user paths:
    exists=True  <home>/Downloads/clipA.jpg   (3 of the 4 sampled)
    exists=True  <home>/Documents/demo_folder/charA01_mixed_var01_basecolor_1k_srgb.png
=== tier 3: uploaded media
  image             str -> presigned S3 URL in the field itself
  sg_uploaded_movie dict keys=['url', 'name', 'content_type', 'link_type', 'type', 'id']
  filtering sg_uploaded_movie is_not None -> 400 API summarize() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter.
  image is_not None 33/53 on this project, 98/1057 site-wide
```

**Teaches**

| tier | what resolves | second call |
|---|---|---|
| 1. `Version.published_files` then `PublishedFile.path` | mac, windows and linux absolute paths at once, the LocalStorage join already done | yes, one `_search` |
| 2. `sg_path_to_movie`, `sg_path_to_frames` | one absolute path, no platform variants | no |
| 3. `image`, `sg_uploaded_movie` | a presigned S3 URL | no |

- **Tier 1 is untested here for two reasons, and only one of them is about the API.** On the probed site, Image, Rendered Image, Texture and USD PublishedFiles have **no `path` at all**, and `Version.published_files` is filled on 2 of 53 Versions: that is Flow PT data. The Movie paths that do exist point at files the operator has since deleted from disk: that is not. Read this as "this site has no publish history", never as "Flow PT paths are unreliable".
- Tier 2 holds one absolute path, so a value cannot resolve on two platforms, unlike `PublishedFile.path`, which returns all three at once. On the probed site `sg_path_to_frames` is 0 of 53, leaving the sequence form untested: it is free text taking printf padding and the Shake `#`/`@` forms, so never assume `%04d`.
- Tier 3 needs no second call: `image` is a presigned S3 URL as a plain string, and `sg_uploaded_movie` is a dict with the same URL under `url`. It does not always resolve. On the probed site `image` is filled on 33 of 53 Versions in the sample project and 98 of 1057 site-wide, so test the field rather than assuming a fallback.
- **Trap.** `sg_uploaded_movie` cannot be filtered or summarized `is_not None`: 400 `API summarize() Version.sg_uploaded_movie's 'url' data type cannot be used in a filter.` Same shape of trap as a checkbox (probe 020).
- Offer the operator whichever tiers a given Version can deliver rather than picking one for them.
