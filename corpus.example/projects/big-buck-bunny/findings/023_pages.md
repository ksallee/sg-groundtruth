---
tags: [page, project, query, inspector, schema]
scope: project
project: Big Buck Bunny
verdict: 19 of 53 Pages on Big Buck Bunny hold a column list. Read it from the PageSetting whose user is null and feed it straight to ?fields.
---
# 023_pages

53 Pages belong to Big Buck Bunny, 19 of them with a column list. The layout is the `PageSetting` row whose `user` is null; a per-user row is a patch over it, not a tree. The columns are schema field names and can be handed to `?fields` verbatim.

| id | page | page_type | entity type | columns |
|---|---|---|---|---|
| 5106 | Assets | canvas | Asset | 6 |
| 5108 | Files | canvas | Attachment | 8 |
| 5110 | Bookings | canvas | Booking | 8 |
| 5115 | Cameras | canvas | Camera | 6 |
| 5103 | Deliveries | canvas | Delivery | 8 |
| 5111 | Departments | canvas | Department | 5 |
| 5102 | Episodes | canvas | Episode | 6 |
| 5101 | Event Log Entries | canvas | EventLogEntry | 7 |
| 5097 | People | canvas | HumanUser | 9 |
| 5095 | Launches | canvas | Launch | 6 |
| 5116 | Notes | canvas | Note | 9 |
| 5119 | Pages | canvas | Page | 5 |
| 5107 | Review | canvas | Playlist | 5 |
| 5098 | Published Files | canvas | PublishedFile | 6 |
| 5096 | Scenes | canvas | Scene | 7 |
| 5104 | Sequences | canvas | Sequence | 5 |
| 5099 | Shots | canvas | Shot | 6 |
| 5114 | Time Logs | canvas | TimeLog | 9 |
| 5105 | Versions | canvas | Version | 8 |
| 5090 | Media | media_center |  | 0 |
| 3074 | Media Center Right Pane | media_center_right_pane |  | 0 |
| 4370 | Media Center Right Pane Cut | media_center_right_pane_cut |  | 0 |
| 3085 | Project UI Visibility Settings | project_ui_visibility |  | 0 |
| 4560 | Versions Tray | review_app_versions_tray |  | 0 |
| 5126 | unnamed | stream_detail | Asset | 0 |
| 5129 | unnamed | stream_detail | Asset | 0 |
| 5151 | unnamed | detail | Asset | 0 |
| 5127 | unnamed | stream_detail | Cut | 0 |
| 5124 | unnamed | stream_detail | Episode | 0 |
| 5146 | unnamed | stream_detail | MocapSetup | 0 |
| 5157 | unnamed | detail | MocapSetup | 0 |
| 5141 | unnamed | stream_detail | MocapTake | 0 |
| 5145 | unnamed | detail | MocapTake | 0 |
| 5136 | unnamed | detail | Performer | 0 |
| 5147 | unnamed | stream_detail | Performer | 0 |
| 5133 | unnamed | stream_detail | Playlist | 0 |
| 5150 | unnamed | detail | Playlist | 0 |
| 5089 | Overview | project_overview | Project | 0 |
| 5093 | Overview | canvas | Project | 0 |
| 5125 | unnamed | stream_detail | PublishedFile | 0 |
| 5142 | unnamed | detail | Scene | 0 |
| 5148 | unnamed | stream_detail | Scene | 0 |
| 5137 | unnamed | detail | Sequence | 0 |
| 5153 | unnamed | stream_detail | Sequence | 0 |
| 5131 | unnamed | detail | ShootDay | 0 |
| 5139 | unnamed | stream_detail | ShootDay | 0 |
| 5128 | unnamed | stream_detail | Shot | 0 |
| 5152 | unnamed | detail | Shot | 0 |
| 5094 | Tasks | canvas | Task | 0 |
| 5123 | unnamed | stream_detail | Task | 0 |
| 5144 | unnamed | detail | Task | 0 |
| 5134 | unnamed | stream_detail | Version | 0 |
| 5156 | unnamed | detail | Version | 0 |

This is what the team looks at, in the order they look at it.

### Assets

`Asset`, page 5106, `page_type` `canvas`. 6 columns, in order.

```
image,sg_status_list,code,sg_asset_type,description,shots
```

### Files

`Attachment`, page 5108, `page_type` `canvas`. 8 columns, in order.

```
this_file,image,attachment_links,sg_status_list,description,created_by,created_at,tags
```

### Bookings

`Booking`, page 5110, `page_type` `canvas`. 8 columns, in order.

```
user,start_date,end_date,project,vacation,note,updated_at,updated_by
```

### Cameras

`Camera`, page 5115, `page_type` `canvas`. 6 columns, in order.

```
code,image,sg_status_list,description,updated_by,updated_at
```

### Deliveries

`Delivery`, page 5103, `page_type` `canvas`. 8 columns, in order.

```
delivery_number,title,sg_status_list,sg_from,addressings_to,sg_delivery_method,sg_due_date,sg_received_date
```

### Departments

`Department`, page 5111, `page_type` `canvas`. 5 columns, in order.

```
name,code,color,list_order,users
```

### Episodes

`Episode`, page 5102, `page_type` `canvas`. 6 columns, in order.

```
code,image,sg_status_list,tank_type,entity,version_number
```

### Event Log Entries

`EventLogEntry`, page 5101, `page_type` `canvas`. 7 columns, in order.

```
description,user,created_at,entity,project,event_type,id
```

### People

`HumanUser`, page 5097, `page_type` `canvas`. 9 columns, in order.

```
name,sg_status_list,image,email,login,password_proxy,permission_rule_set,projects,groups
```

### Launches

`Launch`, page 5095, `page_type` `canvas`. 6 columns, in order.

```
code,image,sg_status_list,description,updated_by,updated_at
```

### Notes

`Note`, page 5116, `page_type` `canvas`. 9 columns, in order.

```
subject,sg_status_list,note_links,user,addressings_to,content,sg_note_type,updated_at,read_by_current_user
```

1 of these are absent from `/schema/Note/fields`: `read_by_current_user`. `?fields` ignores a name a type does not have, so a stale column is silent rather than a 400.

### Pages

`Page`, page 5119, `page_type` `canvas`. 5 columns, in order.

```
name,current_user_favorite,description,tags,folder
```

### Review

`Playlist`, page 5107, `page_type` `canvas`. 5 columns, in order.

```
code,sg_status,description,updated_at,updated_by
```

1 of these are absent from `/schema/Playlist/fields`: `sg_status`. `?fields` ignores a name a type does not have, so a stale column is silent rather than a 400.

### Published Files

`PublishedFile`, page 5098, `page_type` `canvas`. 6 columns, in order.

```
code,image,sg_status_list,tank_type,entity,version_number
```

1 of these are absent from `/schema/PublishedFile/fields`: `tank_type`. `?fields` ignores a name a type does not have, so a stale column is silent rather than a 400.

### Scenes

`Scene`, page 5096, `page_type` `canvas`. 7 columns, in order.

```
code,image,sg_status_list,description,assets,shots,sg_scene_type
```

### Sequences

`Sequence`, page 5104, `page_type` `canvas`. 5 columns, in order.

```
code,sg_status_list,description,cuts,created_by.HumanUser.email
```

### Shots

`Shot`, page 5099, `page_type` `canvas`. 6 columns, in order.

```
image,sg_status_list,code,sg_sequence,description,created_by
```

### Time Logs

`TimeLog`, page 5114, `page_type` `canvas`. 9 columns, in order.

```
id,user,entity,entity.Task.entity,description,date,duration,updated_at,updated_by
```

### Versions

`Version`, page 5105, `page_type` `canvas`. 8 columns, in order.

```
image,sg_status_list,code,entity,sg_task,user,description,created_at
```
