---
tags: [schema, custom-field, create, trap, silent, error-handling]
endpoints: [POST /schema/<Type>/fields, PUT /schema/<Type>/fields/<field>, POST /schema/<Type>/fields/<field>]
phase: schema
scope: api
measured: site-wide, 2026-11-10; nine fields created on Version and retired, one of them named sg_currency
coverage: partial
unmeasured: a non-ASCII display name on a data type other than currency. Not sent: it would spend sg_<data_type> on the site. Blocked on the work.
verdict: One non-ASCII character in the display name and the field is named `sg_<data_type>`, at 201. ASCII names are lowercased, every other character becomes `_`, nothing is trimmed or cut.
---

# 117_field_types_and_names

**Q** Can `currency`, `timecode`, `footage` and `color` fields be created with a name alone, and what
programmatic name does the server derive from a display name with accents, non-Latin letters,
repeated punctuation, a leading digit, outer spaces or great length?

**Endpoint** `POST /schema/<Type>/fields`

**Docs claim** `/spec.json` lists `currency`, `timecode`, `footage`, `status_list`, `uuid` and
`calculated` among the creatable types and not `color`. It says nothing about how the name is derived.

**Actual**

```
POST currency  name "zzprobe 117 Durée Écran ñ" -> 201
  links.self .../schema/Version/fields/sg_currency      name reads "zzprobe 117 Durée Écran ñ"
DELETE sg_currency -> 204
POST currency  name "zzprobe 117 Durée Écran ñ" -> 400 code 105
POST currency  name "zzprobe 117 日本語 поле" -> 400 code 105
  "API schema_field_create() failed, there is a retired field with the same field_name: sg_currency.
   Delete the retired field forever from the Trash Page in Shotgun and try again."

POST currency  "zzprobe 117 currency"         -> 201  sg_zzprobe_117_currency
POST currency  "zzprobe 117 a--b..c!!d  e_f"  -> 201  sg_zzprobe_117_a__b__c__d__e_f
POST currency  "117 zzprobe digit"            -> 201  sg_117_zzprobe_digit
POST currency  "  zzprobe 117 spaces  "       -> 201  sg___zzprobe_117_spaces__
POST currency  "zzprobe 117 MiXed CASE"       -> 201  sg_zzprobe_117_mixed_case
POST currency  "zzprobe 117 long abcdefghij..." (120 chars) -> 201  sg_zzprobe_117_long_abc... (123 chars)
POST timecode  "zzprobe 117 timecode" -> 201   properties {"default_value": null, "summary_default": "none"}
POST footage   "zzprobe 117 footage"  -> 201   the same properties
POST color     "zzprobe 117 color"    -> 400 code 103 "Request Parameters invalid."
  source {"data_type": ["data_type is not valid"]}

POST .../sg_zzprobe_116_list {"revive": true} -> 204
  name "zzprobe 116 list renamed", default_value "alpha", summary_default "count", valid_values ["beta"]
```

**The name rule**

| display name | programmatic name |
|---|---|
| ASCII letters | lowercased |
| a digit, `_` | kept |
| a space or any other ASCII character | one `_` each. Runs are not collapsed |
| leading and trailing spaces | one `_` each, not trimmed. The display name keeps them |
| a leading digit | kept: `sg_117_...` |
| 120 characters | 123, uncut |
| **any character outside ASCII, anywhere** | **the whole name is discarded: `sg_<data_type>`** |

The prefix is `sg_`. For ASCII input the rule is `"sg_" + re.sub(r"[^a-z0-9_]", "_", display.lower())`.

**The non-ASCII fallback**

A display name holding `é`, `É` and `ñ` created `sg_currency` on a `currency` field: nothing of the
display name is in it. The response is a plain 201, and the display name reads back intact. With
`sg_currency` retired, the same name and a Japanese and Cyrillic one were both refused, naming
`sg_currency` as the retired field in the way. Two different display names derive one programmatic
name, and it is a name a real field would want.

**Types, each created with a name alone**

| `data_type` | result | `properties` |
|---|---|---|
| `currency` | 201 | `default_value` null, `summary_default` "none" |
| `timecode` | 201 | the same |
| `footage` | 201 | the same |
| `color` | 400 `data_type is not valid` | |
| `status_list` | 400, needs `valid_values` (probe 116) | |

**Teaches**

| do | why |
|---|---|
| Refuse a non-ASCII display name at creation, or create under an ASCII name and rename | the create succeeds under `sg_<data_type>`, and the rename leaves the programmatic name alone (probe 116) |
| Read the name from `links.self` and compare it with the one you predicted | a 201 does not mean the name you expected |
| Predict ASCII names with the one-line rule | it held for punctuation, digits, outer spaces, case and 120 characters |
| Expect a revive to return the field as it was retired | the rename, the default, the values and `summary_default` all came back |

`sg_currency` on Version was spent by this probe and is in the trash under the display name
`zzprobe 117 Durée Écran ñ`.
