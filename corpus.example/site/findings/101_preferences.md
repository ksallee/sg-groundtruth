---
tags: [duration, schema, inspector, discovery]
scope: site
verdict: 17 preference keys here. hours_per_day is 8.0 and duration_units is "days", which is what a duration has to be rendered against.
---
# 101_preferences

`GET /preferences` returns 17 keys on this site. Two of them are the only place the API states what a duration means.

| key | value |
|---|---|
| `hours_per_day` | `8.0` |
| `duration_units` | `"days"` |

A duration field is a bare integer of minutes and no schema property names the unit (`field_types/duration`). Rendering one here means dividing by `60 * 8.0` and labelling it "days".

**Every key**

| key | value |
|---|---|
| `creative_review_settings` | `{"status_groups":[{"name":"Upcoming","code":"upc_stgr","status_list":[` +2043 chars |
| `date_component_order` | `month_day` |
| `duration_units` | `days` |
| `enable_rv_integration` | `true` |
| `enable_shotgun_review_for_rv` | `false` |
| `format_currency_fields_decimal_options` | `$1,000.99` |
| `format_currency_fields_display_dollar_sign` | `false` |
| `format_currency_fields_negative_options` | `- $1,000` |
| `format_date_fields` | `08/04/22 OR 04/08/22 (depending on the Month order preference)` |
| `format_float_fields` | `9,999.99` |
| `format_float_fields_rounding` | `9.999999` |
| `format_footage_fields` | `10-05` |
| `format_number_fields` | `1,000` |
| `format_time_hour_fields` | `12 hour` |
| `hours_per_day` | `8.0` |
| `support_local_storage` | `true` |
| `view_master_settings` | `{"status_groups":[{"name":"Upcoming","code":"upc_stgr","status_list":[` +2462 chars |
