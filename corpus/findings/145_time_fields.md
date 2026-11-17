---
tags: [date, timecode, duration, batch, custom-field, trap]
endpoints: [POST /schema/<Type>/fields, POST /entity/<type>, PUT /entity/<type>/<id>, POST /entity/_batch, POST /entity/<type>/_summarize, POST /entity/<type>/_search]
phase: write
scope: api
measured: sandbox project written, 2026-11-11; about 30 rows on a custom slot; three fields created and retired
verdict: date_time rounds to the second on POST and PUT (.999 goes up, .5 stays) but truncates in a _batch create. A new timecode field has no rate property; it is integer ms rendered at the site's fixed rate.
---

# 145_time_fields

**Q** What precision does a `date_time` field keep on create, update and inside `_batch`; what does a
`timecode` and a `duration` field created over REST take, return and declare; and how does
`01:00:00:12` at 24 and at 23.976 fps round-trip?

**Endpoint** `POST /schema/<Type>/fields ; POST /entity/<type> ; PUT /entity/<type>/<id> ; POST /entity/_batch ; POST /entity/<type>/_summarize`

**Docs claim** Silent on precision and on a frame rate. Already measured: `field_types/date_time` (PUT
on a stock field), `field_types/timecode` (integer ms, rate 23.976 solved from group names),
`field_types/duration` (integer minutes). Not repeated here.

**Actual**

```
date_time, on a new field         POST                  PUT                   _batch create
2026-11-11T14:22:05.999Z          14:22:06Z             14:22:06Z             14:22:05Z
2026-11-11T14:22:05.5Z            14:22:05Z             14:22:05Z             14:22:05Z
2026-11-11T14:22:05.123456Z       14:22:05Z             14:22:05Z             14:22:05Z
2026-11-11T09:22:05.999-05:00     14:22:06Z             14:22:06Z             14:22:05Z
2026-11-11T14:22:05,5Z            14:22:05Z             14:22:05Z             14:22:05Z
stored from .999Z by POST: filter is 14:22:05Z -> 0; is 14:22:05.999Z -> 1; is 14:22:06Z -> 1

new timecode, duration, date_time fields: properties {"default_value": null, "summary_default": "none"}
timecode or duration with {"property_name": "frame_rate", "value": 24} -> 400 code 103 invalid property
  'frame_rate' ... Valid property names: ["name", "visible", "description", "summary_default", "custom_metadata"]

timecode, new field          sent          read       _summarize group_name
01:00:00:12 at 24            3600500       3600500    01:00:00:12
  at 23.976, 12 * 1001/24    3600500.5     400 code 103 ... expected [Integer, NilClass] ... got Float: 3600500.5
    rounded                  3600501       3600501    01:00:00:12
  as a frame count at 23.976 3603604       3603604    01:00:03:14
11 / 13 frames at 24         3600458 / 3600542        01:00:00:11 / 01:00:00:13
"01:00:00:12"                400 ... got String: "01:00:00:12"

duration, new field: 90 -> 90; "90" -> 90; 1.5, 1.9, "1.5" -> 1; -30 -> -30;
  "01:30" -> 400 code 103 Invalid data for 'duration' data type
```

**Teaches**
- `date_time` keeps whole seconds and the path decides which second. Round to the second yourself
  before sending, then every path stores the same value. A `.999` capture time sent by `_batch` is
  one second earlier than the same value sent by `POST`.
- The rounding is not half-up: `.5` stayed on its second and `.999` went to the next. Where the cut
  lies between was not measured. A filter value is rounded the same way as a write, so filtering
  with the value that was sent finds the row.
- A timecode field has no rate anywhere: the create refuses a rate property, the schema shows none,
  and the value is milliseconds of wall-clock time. `01:00:00:12` therefore means `3600000 +
  12 * 1000 / fps` ms, rounded to an integer, and `3600500` and `3600501` both render as frame 12.
- Milliseconds are fine enough for frames (one frame at 23.976 is 41.7 ms), but the field stores no
  rate, so a reader cannot tell which rate a value was written at, and the server renders every
  value at its own fixed rate (`field_types/timecode`). Store a frame count in a `number` field and the rate beside it, or the `HH:MM:SS:FF`
  string in `text`, as the stock cut fields do.
- A new duration field behaves as the stock one: integer minutes, a float or numeric string
  truncated toward zero, a clock string refused.
