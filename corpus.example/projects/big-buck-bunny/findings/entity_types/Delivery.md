---
tags: [entity-type, project, page, fill-rate, status, link, inspector]
scope: project
project: Big Buck Bunny
title: Delivery
verdict: On Big Buck Bunny, Delivery has 1 page built for it and populates 0 of 32 rankable fields across 0 sampled rows.
---
# Delivery

What Big Buck Bunny does with `Delivery`. No row of this type belongs to the project.

**Pages**

| id | page | page_type | columns |
|---|---|---|---|
| 5103 | Deliveries | canvas | 8 |

The layout is the `PageSetting` row whose `user` is null (probe 023). The columns are schema field names and go to `?fields` verbatim.

### Deliveries

`Delivery`, page 5103, `page_type` `canvas`. 8 columns, in order.

```
delivery_number,title,sg_status_list,sg_from,addressings_to,sg_delivery_method,sg_due_date,sg_received_date
```

**Usable statuses**

| field | usable | hidden | usable values | default |
|---|---|---|---|---|
| `sg_status_list` | 4 | 0 | `opn (Open)`, `ip (In Progress)`, `dlvr (Delivered)`, `recd (Received)` | opn |

Read with `project_id=70`: `valid_values` minus `hidden_values`. The API accepts a hidden code on a write, so subtract it yourself.
