---
tags: [status, icon, discovery, enumeration]
endpoints: [GET /schema/<Type>/fields, GET /entity/<type>, POST /entity/<type>/_search]
phase: schema
scope: api
measured: site-wide, the Status listing live and retired, joined to the Icon listing
verdict: Nothing in the schema marks a shipped Status. `system` is true on a minority of them; the stock set is `created_by is null`, plus `options[return_only]=retired` for the rows a site retired.
---

# 061_shipped_statuses

**Q** Which `Status` rows does a site start with, and does anything in the schema mark them?

**Endpoint** `GET /schema/Status/fields ; GET /entity/statuses ; POST /entity/statuses/_search`

**Docs claim** Silent. `Status` is listed as an ordinary entity type, `system` is not documented, and nothing says which rows a fresh site holds.

**Actual**

```
GET /schema/Status/fields -> 11 fields
  code        text       editable False  "Short Code"
  created_at  date_time  editable False  "Date Created"
  created_by  entity     editable False  "Created by"
  system      checkbox   editable False  "Locked by System"
  icon        entity     editable True   "Icon"

GET /entity/statuses?fields=code,name,system,created_by,created_at,icon -> 32 rows
    id  code   system  created_at            created_by  image_map_key
     1  act    True    null                  null        null  (custom_status/html)
     2  apr    False   null                  null        "icon_apr"
   ... 15 rows, ids 4-19: created_at and created_by null, system True on dis, ip and na
    23  cfrm   True    2014-08-06T15:06:24Z  null        "icon_thumb_up"
    24  pndng  True    2014-08-06T15:06:25Z  null        "icon_voice_command"
    32  pass   False   2025-12-21T07:48:36Z  a person    "icon_apr"
   ... 12 rows, ids 33-198: created_at set, created_by a person, system False

                    system true  system false
  created_by null   6            13
  created_by set    0            13

POST /entity/statuses/_search, hash Content-Type
  created_by is null   -> 200  19 rows
  system is true       -> 200   6 rows
  an `or` of the two   -> 200  19 rows

GET /entity/statuses?options[return_only]=retired -> 200 9 rows
     3 cbb, 13 rdy, 21 blk, 22 plsh, 25 late, 26 rsk, 30 rrq, 31 out   created_by null
    20 tkt                                                             created_by a person
```

**Teaches**
- `created_by is null` selects the shipped rows and is the only mark that does. It is one filter at
  200, so the split costs no extra call. A row an operator added names them in `created_by`, and
  `created_by` is `editable: false`, so nobody can blank it afterwards.
- `system` is a checkbox whose display name is `Locked by System`, and it does not mean "shipped":

  | selection | on the probed site |
  |---|---|
  | `created_by is null` | 19 rows |
  | `system is true` | 6 rows, `act` `dis` `ip` `na` `cfrm` `pndng` |
  | `system is true` and `created_by` set | 0 rows |
  | an `or` of the two | 19 rows, the same set as `created_by is null` alone |

  `system` is a subset, so an `or` adds nothing and `system` alone drops 13 shipped codes.
- `created_at` is not a mark either. On the probed site it is null on 17 of the 19 shipped rows and
  `2014-08-06` on `cfrm` and `pndng`, which no creator names, while every operator-added row from
  id 32 up has both a date and a person.
- The live listing is what the site kept, not what it started with. On the probed site 9 further
  rows are retired, 8 of them with no `created_by` (`cbb`, `rdy`, `blk`, `plsh`, `late`, `rsk`,
  `rrq`, `out`), and only `options[return_only]=retired` returns them. A low id proves nothing on
  its own: retired id 20, `tkt`, names a person.
- The 19 shipped codes on the probed site, with the stock `image_map_key` each points at. Resolve a
  key against the site's own stylesheet and the `/images/sg_icon_image_map.png` sprite, both of
  which answer an unauthenticated GET at 200; probe 010 and `recipes/010_status_picker` record that
  rediscovery and the offsets.

  | code | name | `image_map_key` |
  |---|---|---|
  | `act` | Active | none. On the probed site it points at a `custom_status`/`html` icon |
  | `apr` | Approved | `icon_apr` |
  | `clsd` | Closed | `icon_fin` |
  | `cmpt` | Complete | `icon_cmpt` |
  | `dis` | Disabled | `icon_na` |
  | `fin` | Final | `icon_fin` |
  | `hld` | On Hold | `icon_hld` |
  | `ip` | In Progress | `icon_ip` |
  | `na` | N/A | `icon_na` |
  | `omt` | Omit | `icon_omt` |
  | `opn` | Open | `icon_rdy` |
  | `res` | Resolved | `icon_fin` |
  | `rev` | Pending Review | `icon_rev` |
  | `wtg` | Waiting to Start | `icon_wtg` |
  | `vwd` | Viewed | `icon_fin` |
  | `recd` | Received | `icon_recd` |
  | `dlvr` | Delivered | `icon_dlvr` |
  | `cfrm` | Confirmed | `icon_thumb_up` |
  | `pndng` | Pending | `icon_voice_command` |

  15 distinct keys over 19 codes: `icon_fin` draws `clsd`, `fin`, `res` and `vwd`, and `icon_na`
  draws `dis` and `na`. The icon does not identify the status, and `icon` is the one editable field
  on the row, so a stock code can point at a custom icon.
- Which codes a site holds is site configuration, and only the shape transfers. Read the split per
  site rather than hardcoding the 19: this site retired 8 shipped rows and added 13 of its own, and
  a shipped code is still only offered where a type's `valid_values` lists it (probe 009).
