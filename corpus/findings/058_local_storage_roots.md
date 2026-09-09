---
tags: [path, storage, published-file, etag, silent]
endpoints: [POST /entity/<type>, PUT /entity/<type>/<id>, GET /entity/<type>/<id>]
phase: write
scope: api
measured: sandbox project written, four LocalStorage roots created site-wide and deleted
verdict: One create fills every `local_path_*` the storage row defines, whichever platform's root the path was under. The server picks the deepest matching root, and no conditional-write header is honoured.
---

# 058_local_storage_roots

**Q** With roots on every platform and roots that nest, which one does a `path` write resolve against,
and is there a conditional write that closes the version race?

**Endpoint** `POST /entity/published_files ; PUT /entity/published_files/<id> ;
POST /entity/local_storages`

**Docs claim** Silent on both. `path` is documented as taking a local path, with nothing on which
storage row a path is matched against, and no conditional request is described anywhere.

**Actual**

```
one row: mac_path '/zzprobe_058_a'  windows_path 'Z:\zzprobe_058_a'  linux_path '/mnt/zzprobe_058_a'

path sent                                                     storage returned
{"local_path": "/zzprobe_058_a/seq/plate.v001.exr"}                 78
{"local_path": "/mnt/zzprobe_058_a/seq/plate.v001.exr"}             78
{"local_path": "Z:/zzprobe_058_a/seq/plate.v001.exr"}               78
{"relative_path": "seq/plate.v001.exr", "local_storage": {id: 78}}  78
all four read back the identical object:
  relative_path      'seq/plate.v001.exr'
  local_path_mac     '/zzprobe_058_a/seq/plate.v001.exr'
  local_path_windows 'Z:\zzprobe_058_a\seq\plate.v001.exr'
  local_path_linux   '/mnt/zzprobe_058_a/seq/plate.v001.exr'

roots that nest, and a path under both
  79 '/zzprobe_058_n' created first, 80 '/zzprobe_058_n/sub' second
    /zzprobe_058_n/sub/deep/plate.v001.exr -> 80, relative_path 'deep/plate.v001.exr'
    /zzprobe_058_n/other/plate.v001.exr    -> 79, relative_path 'other/plate.v001.exr'
  81 '/zzprobe_058_m/sub' created first, 82 '/zzprobe_058_m' second
    /zzprobe_058_m/sub/deep/plate.v001.exr -> 81
  83 and 84 both '/zzprobe_058_d'
    /zzprobe_058_d/plate.v001.exr          -> 84
  the 201 names the choice twice and nowhere else:
    path.local_storage               {"type": "LocalStorage", "id": 84}
    relationships.path_cache_storage {"type": "LocalStorage", "id": 84, "name": "<storage>"}
    attributes.path_cache null ; links {"self": "/api/v1/entity/published_files/<id>"}

PUT /entity/published_files/<id> {"version_number": 2}, six times
  GET returns Etag: W/"1eba9cc1afb8cfc7cdddd77376341158", and no Last-Modified
  no header / If-Match: "definitely-not-an-etag" / If-Match: * / If-None-Match: * /
  If-Unmodified-Since: 1994 / If-Modified-Since: 1994   -> 200 each, version_number 2
```

**Teaches**
- **One create fills every platform the row defines.** A Mac artist publishing under `mac_path` gives
  a Linux farm a working `local_path_linux` in the same write, and the join runs the same way for a
  path given under the Linux or Windows root: the server strips whichever root matched and re-joins
  the remainder onto all three. `local_path_windows` comes back with backslashes and the drive letter
  exactly as the row spells them, even though a backslash in the request is refused
  (`recipes/004_register_published_file`). A platform reading null is a root the row leaves unset
  (probe 021), never a property of the write.
- **A Windows root is matched with forward slashes.** `Z:/zzprobe_058_a/seq/plate.v001.exr` resolved
  against `windows_path` `Z:\zzprobe_058_a`, so a client normalises separators before sending and
  still reaches a drive-letter root.
- **The deepest matching root wins, not the oldest row.** With `/zzprobe_058_n` and
  `/zzprobe_058_n/sub` both defined, a path under `sub` resolved to the `sub` row in both creation
  orders, so id order does not decide it. Two rows on the identical root resolved to the higher id.
  A client that means one specific storage sends `{"relative_path", "local_storage"}`, which names it
  outright, rather than `{"local_path"}`.
- **Nothing in the response signals the choice beyond the id.** `path.local_storage` and
  `path_cache_storage` hold the same row and there is no confidence, no candidate list and no warning,
  so a client checks by comparing that id against the storage it intended
  (`recipes/004_register_published_file` step 5).
- **There is no conditional write.** All six headers were accepted and ignored, each at 200 with the
  write applied. The `GET` does return a weak `Etag`, so it looks like a precondition is available
  and no request built on it is honoured. The read-then-write race on `version_number` cannot be
  closed at the API; it stays a client convention.
