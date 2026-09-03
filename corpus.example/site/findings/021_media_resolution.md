---
tags: [storage, path, published-file, media, inspector]
scope: site
verdict: 1 LocalStorage root here; local_path_windows, local_path_linux read null on every row because those roots are unset.
---
# 021_media_resolution

1 LocalStorage row on this site. A `PublishedFile.path` is returned with the join already done, so a client never reassembles a root. Which platform paths come back is decided entirely by this table.

| storage | id | mac_path | windows_path | linux_path |
|---|---|---|---|---|
| primary | 3 | `/Volumes/FPT` | null | null |

**What resolves**

| path field | roots set | reads |
|---|---|---|
| `local_path_mac` | 1/1 | a path |
| `local_path_windows` | 0/1 | null on every row |
| `local_path_linux` | 0/1 | null on every row |

`local_path_windows`, `local_path_linux` read null on every PublishedFile here. A client on those platforms falls back to `relative_path` plus a root it holds itself.
