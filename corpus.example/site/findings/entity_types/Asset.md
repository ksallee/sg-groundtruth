---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Asset
verdict: On this site Asset has 28 sg_ fields and 2 vocabularies over 802 rows. The codes here are what the API stores; the labels are editable.
---
# Asset

What this site configures on top of the shipped `Asset` card. The card above is the API layer; everything here is one site's own.

802 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg___complete` | percent | yes | %_complete |
| `sg_ad_approval_required` | checkbox | yes | AD Approval Required |
| `sg_ad_approval_required_1` | checkbox | yes | AD Approval Required |
| `sg_asset_type` | list | yes | Type |
| `sg_bid___mod` | duration | yes | Bid - MOD |
| `sg_bid___rig` | duration | yes | Bid - RIG |
| `sg_bid___tex` | duration | yes | Bid - TEX |
| `sg_bid___total` | duration | yes | Bid - TOTAL |
| `sg_calculated` | calculated | no | Calculated |
| `sg_creative_brief` | url | yes | Creative Brief |
| `sg_fp_test_checkbox` | checkbox | yes | FP Test Checkbox |
| `sg_fp_test_checkbox_1` | checkbox | yes | FP Test Checkbox |
| `sg_fp_test_checkbox_v2` | checkbox | yes | FP Test Checkbox V2 |
| `sg_fp_test_checkbox_v2_1` | checkbox | yes | FP Test Checkbox V2 |
| `sg_keep` | checkbox | yes | Keep |
| `sg_l_approval_required` | checkbox | yes | L Approval Required |
| `sg_latest_version` | summary | yes | Latest Version |
| `sg_outsource` | checkbox | yes | Outsource |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_query` | summary | yes | query |
| `sg_skip_art_director_approval` | checkbox | yes | Skip Art Director Approval |
| `sg_skip_lead_approval` | checkbox | yes | Skip Lead Approval |
| `sg_skip_vfx_supervisor_approval` | checkbox | yes | Skip Vfx Supervisor Approval |
| `sg_status_list` | status_list | yes | Status |
| `sg_vendor_groups` | multi_entity | yes | Vendor Groups |
| `sg_versions` | multi_entity | yes | Version <-> Link |
| `sg_vs_approval_required` | checkbox | yes | Vs Approval Required |
| `sg_weekly_report_custom_entity_s` | multi_entity | yes | Weekly Report Custom Entity  <-> WSR Link |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_asset_type` | list | 12 | `Character`, `Environment`, `Prop`, `FX`, `Graphic`, `Matte Painting`, `Vehicle`, `Weapon`, `Model`, `Theme`, `Zone`, `Part` |  |
| `sg_status_list` | status_list | 8 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `dis (Disabled)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)` | wtg |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `image_source_entity` | entity | 13/100 | Asset 9, Version 4 |
| `sg_versions` | multi_entity | 6/100 | Version 10 |
| `task_template` | entity | 3/100 | TaskTemplate 3 |
| `tasks` | multi_entity | 94/100 | Task 227 |

17 of 21 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
