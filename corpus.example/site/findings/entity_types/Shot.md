---
tags: [entity-type, schema, custom-field, inspector, list-field]
scope: site
title: Shot
verdict: On this site Shot has 39 sg_ fields and 3 vocabularies over 749 rows. The codes here are what the API stores; the labels are editable.
---
# Shot

What this site configures on top of the shipped `Shot` card. The card above is the API layer; everything here is one site's own.

749 rows site-wide, across every project. The 100 most recent were read for the link census below.

**`sg_` fields**

| field | data type | editable | display name |
|---|---|---|---|
| `sg___complete` | percent | yes | %_complete |
| `sg_ad_approval_required` | checkbox | yes | AD Approval Required |
| `sg_bid___ani` | duration | yes | Bid - ANI |
| `sg_bid___comp` | duration | yes | Bid - COMP |
| `sg_bid___fx` | duration | yes | Bid - FX |
| `sg_bid___lit` | duration | yes | Bid - LIT |
| `sg_bid___total` | duration | yes | Bid - TOTAL |
| `sg_client_turnover_date` | date | yes | Client Turnover date |
| `sg_creative_final_due` | date | yes | Creative Final Due |
| `sg_cut_duration` | number | yes | Cut Duration |
| `sg_cut_in` | number | yes | Cut In |
| `sg_cut_order` | number | yes | Cut Order |
| `sg_cut_out` | number | yes | Cut Out |
| `sg_date_next_version_expected` | date | yes | Date Next Version Expected |
| `sg_final_anim_due` | date | yes | Final Anim Due |
| `sg_final_notes_due` | date | yes | Final Notes Due |
| `sg_head_in` | number | yes | Head In |
| `sg_latest_vendor_notes` | text | yes | Latest Vendor Notes |
| `sg_latest_vendor_status` | status_list | yes | Latest Vendor Status |
| `sg_layout_due` | date | yes | Layout Due |
| `sg_published_files` | multi_entity | yes | Published File <-> Link |
| `sg_reel` | entity | yes | Reel |
| `sg_report_date` | date | yes | Report Date |
| `sg_scene` | entity | yes | Scene |
| `sg_sequence` | entity | yes | Sequence |
| `sg_shot_type` | list | yes | Type |
| `sg_status_list` | status_list | yes | Status |
| `sg_tail_out` | number | yes | Tail Out |
| `sg_tech_check_final_due` | date | yes | Tech Check Final Due |
| `sg_test_unique` | text | yes | Test Unique |
| `sg_turnover` | entity | yes | Turnover |
| `sg_turnover_date` | date | yes | Turnover Date |
| `sg_vendor_groups` | multi_entity | yes | Vendor Groups |
| `sg_vendor_percentage_complete` | percent | yes | Vendor Percentage Complete |
| `sg_versions` | multi_entity | yes | Version <-> Link |
| `sg_vfx_production_notes` | text | yes | VFX Production Notes |
| `sg_weekly_report_custom_entity_s` | multi_entity | yes | Weekly Report Custom Entity  <-> WSR Link |
| `sg_wip_comp_due` | date | yes | WIP Comp Due |
| `sg_working_duration` | number | yes | Working Duration |

`/schema` does not mark which of these shipped with Flow Production Tracking and which were added here, so this is the whole namespace on the type.

**Vocabularies**

| field | data type | values | vocabulary | default |
|---|---|---|---|---|
| `sg_latest_vendor_status` | status_list | 6 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `omt (Omit)`, `hld (On Hold)`, `bid (Bidding)` | wtg |
| `sg_shot_type` | list | 6 | `VFX`, `2D`, `Full CG`, `Trailer`, `Marketing`, `Look Dev` | VFX |
| `sg_status_list` | status_list | 10 | `wtg (Waiting to Start)`, `ip (In Progress)`, `fin (Final)`, `rev (Pending Review)`, `apr (Approved)`, `hld (On Hold)`, `omt (Omit)`, `awd (Awarded)`, `bid (Bidding)`, `to (Turned Over)` | wtg |

Site-wide: `valid_values` is byte-identical at every scope (probe 009). Which of these values a project can select is the project layer of this card.

**Links populated site-wide**

| field | data type | set on | points at |
|---|---|---|---|
| `image_source_entity` | entity | 1/100 | Version 1 |
| `reel` | entity | 20/100 | Reel 20 |
| `sg_reel` | entity | 20/100 | Reel 20 |
| `sg_scene` | entity | 20/100 | Scene 20 |
| `sg_sequence` | entity | 79/100 | Sequence 79 |
| `sg_turnover` | entity | 14/100 | Launch 14 |
| `sg_vendor_groups` | multi_entity | 40/100 | Group 40 |
| `sg_versions` | multi_entity | 1/100 | Version 15 |
| `tasks` | multi_entity | 39/100 | Task 153 |

12 of 21 link fields are empty on every sampled row. Which ones a single project fills is the project layer.
