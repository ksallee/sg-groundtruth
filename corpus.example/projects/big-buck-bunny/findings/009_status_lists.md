---
tags: [status, list-field, schema, project, inspector]
scope: project
project: Big Buck Bunny
verdict: On Big Buck Bunny, 1 of 14 status fields hide values. Subtract hidden_values yourself; the API accepts a hidden code on a write.
---
# 009_status_lists

Read with `project_id=70`. 14 status fields, 1 of them hiding at least one value from this project. `valid_values` is identical at every scope, so this subtraction is the only project-specific part of the answer.

| entity type | field | usable | hidden | usable values | default |
|---|---|---|---|---|---|
| Asset | `sg_status_list` | 8 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `dis (Disabled)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)` | wtg |
| Attachment | `sg_status_list` | 2 | 0 | `fin (Final)`, `na (N/A)` | na |
| Cut | `sg_status_list` | 4 | 0 | `ip (In Progress)`, `hld (On Hold)`, `apr (Approved)`, `na (N/A)` | ip |
| Delivery | `sg_status_list` | 4 | 0 | `opn (Open)`, `ip (In Progress)`, `dlvr (Delivered)`, `recd (Received)` | opn |
| Note | `sg_status_list` | 3 | 0 | `opn (Open)`, `ip (In Progress)`, `clsd (Closed)` | opn |
| PublishedFile | `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |
| PublishedFileType | `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `cmpt (Complete)` | wtg |
| Sequence | `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | ip |
| Shot | `sg_latest_vendor_status` | 6 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `omt (Omit)`, `hld (On Hold)`, `bid (Bidding)` | wtg |
| Shot | `sg_status_list` | 10 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)`, `awd (Awarded)`, `bid (Bidding)`, `to (Turned Over)` | wtg |
| Task | `sg_status_list` | 10 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `apr (Approved)`, `dis (Disabled)`, `na (N/A)`, `hld (On Hold)`, `rev (Pending Review)`, `omt (Omit)`, `ready (Ready)` | wtg |
| Version | `sg_status_list` | 14 | 2 | `na (N/A)`, `rev (Pending Review)`, `vwd (Viewed)`, `apr (Approved)`, `custom (CustomIcon)`, `fin (Final)`, `ip (In Progress)`, `clsd (Closed)`, `cmpt (Complete)`, `cfrm (Confirmed)`, `pndad (Pending Art Director)`, `part (partial)`, `pass`, `pndng (Pending)` | rev |
| CustomEntity19 | `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | wtg |
| CustomEntity29 | `sg_status_list` | 3 | 0 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)` | wtg |
