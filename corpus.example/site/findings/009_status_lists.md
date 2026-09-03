---
tags: [schema, status, list-field, entity-type, inspector]
scope: site
verdict: 28 fields define a vocabulary here, site-wide. Read the codes from this table, never the labels: a label is editable and a code is what the API stores.
---
# 009_status_lists

28 list, status and entity-type fields define a vocabulary on this site. These are site-wide: `valid_values` is byte-identical at every scope, and only `hidden_values` varies by project. Which of these values a given project can actually select is the project level of this same entry.

### Asset

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_asset_type` | list | 12 | `Character`, `Environment`, `Prop`, `FX`, `Graphic`, `Matte Painting`, `Vehicle`, `Weapon`, `Model`, `Theme`, `Zone`, `Part` |  |
| `sg_status_list` | status_list | 8 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `dis (Disabled)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)` | wtg |

### Attachment

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `processing_status` | list | 4 | `thumbnail_pending`, `unverified`, `clean`, `infected` |  |
| `sg_status_list` | status_list | 2 | `fin (Final)`, `na (N/A)` | na |

### Cut

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_cut_type` | list | 4 | `Boards`, `Assembly`, `Director`, `Final` |  |
| `sg_status_list` | status_list | 4 | `ip (In Progress)`, `hld (On Hold)`, `apr (Approved)`, `na (N/A)` | ip |

### Delivery

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_delivery_method` | list | 4 | `FTP`, `Aspera`, `FedEx`, `Sneaker Net` |  |
| `sg_delivery_progress` | list | 11 | `In transit`, `Delivery cancelled`, `Delivery failed`, `Delivered`, `Ingesting`, `Ingest cancelled`, `Ingest failed`, `Ingest suspended`, `Received`, `Received with warnings`, `Transcode cancelled` |  |
| `sg_status_list` | status_list | 4 | `opn (Open)`, `ip (In Progress)`, `dlvr (Delivered)`, `recd (Received)` | opn |

### Note

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_note_type` | list | 2 | `Internal`, `Client` |  |
| `sg_status_list` | status_list | 3 | `opn (Open)`, `ip (In Progress)`, `clsd (Closed)` | opn |

### Playlist

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `media_center_viewed_by_current_user` | list | 2 | `read`, `unread` |  |

### Project

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status` | list | 4 | `Bidding`, `Active`, `Lost`, `Hold` |  |
| `sg_type` | list | 5 | `Commercial`, `Episodic`, `Feature`, `Game`, `Other` |  |

### PublishedFile

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |

### PublishedFileType

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |

### Sequence

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | ip |

### Shot

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_latest_vendor_status` | status_list | 6 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `omt (Omit)`, `hld (On Hold)`, `bid (Bidding)` | wtg |
| `sg_shot_type` | list | 6 | `VFX`, `2D`, `Full CG`, `Trailer`, `Marketing`, `Look Dev` | VFX |
| `sg_status_list` | status_list | 10 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)`, `awd (Awarded)`, `bid (Bidding)`, `to (Turned Over)` | wtg |

### Task

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_priority_1` | list | 3 | `1_Tier`, `2_Tier`, `3_Tier` |  |
| `sg_status_list` | status_list | 10 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `apr (Approved)`, `dis (Disabled)`, `na (N/A)`, `hld (On Hold)`, `rev (Pending Review)`, `omt (Omit)`, `ready (Ready)` | wtg |

### Version

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 16 | `na (N/A)`, `rev (Pending Review)`, `vwd (Viewed)`, `apr (Approved)`, `custom (CustomIcon)`, `fin (Final)`, `ip (In Progress)`, `clsd (Closed)`, `cmpt (Complete)`, `cfrm (Confirmed)`, `pndad (Pending Art Director)`, `pndl (Pending Lead)`, `pndvs (Pending VFX Supervisor)`, `part (partial)` +2 more | rev |
| `sg_version_type` | list | 3 | `Type A`, `Type B`, `Type C` | Type A |
| `viewed_by_current_user` | list | 2 | `read`, `unread` |  |

### CustomEntity19

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | wtg |
| `sg_unit` | list | 3 | `Main Unit`, `Aerial`, `Second Unit` |  |

### CustomEntity29

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_status_list` | status_list | 3 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | wtg |
