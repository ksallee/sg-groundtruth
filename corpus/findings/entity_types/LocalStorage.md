---
tags: [path, storage, permission, published-file]
scope: api
measured: site-wide rows created and deleted, one sample project read
summary: A named filesystem root, per platform, that the server joins onto a published file's relative path.
verdict: A LocalStorage row is site-wide and admin-only to write: an Artist reads every row and is refused on create, update and delete. `code` must be unique among live rows, and a DELETE frees it for reuse.
---

# LocalStorage

**Type** Schema name `LocalStorage`, REST slug `local_storages`. Site-wide: 12 fields, none of them
`project`, and every project reads the same rows.

| path | result |
|---|---|
| `GET /entity/local_storages` | 200 |
| `GET /entity/local_storage`, `GET /entity/LocalStorage` | 200, the same rows |
| `GET /entity/localstorages`, `GET /entity/storages` | 404 `Entity type 'localstorages' does not exist.` |

| project scope attempted | result |
|---|---|
| `_search` `[["project", "is", {"type": "Project", "id": N}]]` | 400 code 103 `API read() LocalStorage.project doesn't exist.` |
| `GET ?project_id=N` | 200, accepted and ignored: the same rows as the unscoped call |

**Identity** `code` is the name a person and a pipeline both key on, and it is the one thing the
server enforces. The schema says `unique: false` on every field, including `code`; the server
disagrees.

| field | data_type | editable | holds |
|---|---|---|---|
| `code` | text | yes | the storage name, `primary` |
| `mac_path`, `windows_path`, `linux_path` | text | yes | the root on that platform, absent as `null` |
| `description` | text | yes | free text |
| `cached_display_name` | text | yes | mirrors `code` |
| `uuid` | uuid | no | |
| `id`, `created_at`, `created_by`, `updated_at`, `updated_by` | | no | |

All 12 fields read `visible.editable: false`, so none of them is a custom field (probe 056). On the
probed site there is one row, defining `mac_path` and leaving the other two null.

**Create** `POST /entity/local_storages`, `Content-Type: application/json`. `code` is flagged
`mandatory: true` and the server does not require it, the same inversion Asset, Version and
PublishedFile show (probe 012).

| body | result |
|---|---|
| `{}` | 201, `code` generated `"New LocalStorage <id>"`, every path null |
| `{"mac_path": "/zzprobe_057_orphan"}` | 201, a root under a generated name |
| `{"code": "storage_a"}` | 201, no root on any platform |
| `{code, mac_path, windows_path, linux_path, description}` | 201, all five as sent |
| the same `code` while the first row is alive | 400 code 104 |
| the same `code` after the first row was deleted | 201 |

```
POST {"code": "storage_a"} twice
  400 code 104  Create failed for [LocalStorage]: Validation failed: Code is already in use by an
                active or retired local storage
```

A Windows root is stored as sent, backslashes and drive letter included: `Z:\zzprobe_057_three` read
back unchanged. That is the reverse of `PublishedFile.path`, which refuses a backslash in either
`relative_path` or `local_path` (`recipes/004_register_published_file`).

**Delete frees the name.** `DELETE /entity/local_storages/<id>` answered 204, a `GET` of the id
answered 404, and creating a row with the same `code` answered 201. The duplicate error above names
retired rows, and a deleted row did not block the name in practice. A schema field behaves the other
way, and its name stays spent (probe 019).

**Links** None. LocalStorage has no `entity` or `multi_entity` field of its own. It is pointed at
from `PublishedFile.path_cache_storage` and from inside the `local` shape of any `url` field, as
`{"type": "LocalStorage", "id": N, "name": "primary"}` (`field_types/url`).

**Status** None. There is no `sg_status_list` and no `list` field.

**Traps**
- **Writing one is admin-only.** Impersonating an `Artist` on the probed site returned every row on a
  `GET` and refused all three writes, each at 400 code 104: `Entity of type LocalStorage cannot be
  created by this user.`, `The field is not editable for this user: [LocalStorage.mac_path].` and
  `Entity of type LocalStorage can not be deleted by this user.` A client that offers "point at any
  folder" as a setup step has to say that an administrator runs it.
- A row with no root on any platform is a 201, and nothing reports it as incomplete. The path a
  client then sends is refused as matching no defined storage (`recipes/004_register_published_file`).
- The refusal to write is a 400, not a 401 or a 403, so a client branching on the status code reads it
  as a bad body.
- A caller with no root to write under does not need a row at all: `PublishedFile.path` takes the
  three-call upload instead (`recipes/013_publish_file_bytes`).
