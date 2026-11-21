---
tags: [number, silent, error-handling]
scope: api
measured: sandbox project written, 2026-11-20; one currency field created on a custom slot, 3 rows
summary: A money amount: a number kept to two decimal places, with no currency code.
verdict: A currency stores 2 decimals, rounding half up at 200, reads back as a JSON string and refuses Integer. No currency code exists on the field or the row: the symbol is a site display setting.
---

# currency

**Data type** `currency`, probed on `sg_zzprobe_currency_amount`, created by `probes/_bids.py` on the
Bid Line custom slot and left in place: on the probed site no live field of the type existed, on any of
114 entity types. Created with a name alone (probe 117), `properties` reads
`{"default_value": null, "summary_default": "none"}`. No property, top-level key or row value names a
currency.

| where | what it holds |
|---|---|
| the field's schema | nothing about money: the keys every field has |
| `GET /preferences` | `format_currency_fields_display_dollar_sign` false, `format_currency_fields_decimal_options` `"$1,000.99"`, `format_currency_fields_negative_options` `"- $1,000"`, on the probed site |
| `/spec.json` | the type as `float \| null`, range `-9999999999999.99` to `9999999999999.99`; its example preferences add `format_currency_fields_symbol` `"DOLLAR"`, which the probed site does not return |

The preferences are how the web interface draws every currency field on the site. A row stores a bare
number, so a client holding amounts in several currencies keeps the code in a field of its own.

**Read** Returned under `attributes` as a JSON string with a decimal point, the same shape as `float`:
`"1234.56"`, `"0.0"`, `"1000000000000.0"`. `_summarize` returns a JSON number.

**Write**

| sent | status | read back raw |
|---|---|---|
| `1234.56` | 200 | `"1234.56"` |
| `"1234.56"` | 200 | `"1234.56"` |
| `" 4.5 "` | 200 | `"4.5"`; whitespace trimmed |
| `-99.99` | 200 | `"-99.99"` |
| `0.004` | 200 | `"0.0"` |
| `0.005`, `0.015`, `0.025` | 200 | `"0.01"`, `"0.02"`, `"0.03"`; half up, not half even |
| `1.005`, `2.675` | 200 | `"1.01"`, `"2.68"`; rounded from the decimal sent, not from the nearest binary float |
| `12.345`, `12.3449` | 200 | `"12.35"`, `"12.34"` |
| `1e-09` | 200 | `"0.0"` |
| `9999999999999.99`, `-9999999999999.99` | 200 | stored as sent |
| `10000000000000.0`, `-10000000000000.0`, `1e15` | 400 | code 104 `Update failed for [CustomEntityNN.sg_zzprobe_currency_amount]: Invalid statement.` |
| `1234`, `0` | 400 | `API update() ... expected [String, BigDecimal, Float, NilClass] data type(s) but got Integer: 1234` |
| `True` | 400 | `... but got TrueClass: true` |
| `{"value": 1.0, "currency": "USD"}` | 400 | `... but got Hash: {"value" => 1.0, "currency" => "USD"}` |
| `"1e3"`, `"abc"`, `"$12.00"`, `"12 USD"`, `"1,234.56"` | 400 | code 103 `Invalid data for 'currency' data type`, `source` naming the value |
| `7` inside a `_batch` update | 200 | `"7.0"`: `_batch` coerces the Integer a single `PUT` refuses (probe 137) |

**Clear**

| sent | result |
|---|---|
| `null` | cleared, reads `null` |
| `0.0` | 200, reads `"0.0"`, a value distinct from `null` |
| `""` | 400 `Invalid data for 'currency' data type` |

**Filter** The 400 from a bogus relation:

```
API read() CustomEntityNN.sg_zzprobe_currency_amount's 'currency' data type doesn't support
'definitely_not_an_operator' 'relation' ...
Valid relations: ["is", "is_not", "greater_than", "less_than", "between", "in", "not_in"]
```

Over three rows, `_a` 0.0, `_b` null, `_c` 12.5:

| operator | value | matches |
|---|---|---|
| `is` | `12.5` | 1 |
| `is` | `"12.5"` | 1 |
| `is` | `0.0` | 1 (`_a`) |
| `is` | `None` | 1 (`_b`) |
| `is_not` | `None` | 2 |
| `greater_than` | `0.0` | 1 |
| `less_than` | `100.0` | 2 |
| `between` | `[0.0, 12.5]` | 2; inclusive |
| `in` | `[12.5, 0.0]` | 2 |
| `not_in` | `[12.5]` | 2; the null row is included |
| `is` | `99999.5` | 0 |
| `is` | `12`, `0` (Integer) | 400 `API read() ... but got Integer: 12` |
| `not_between` | `[1.0, 20.0]` | 400 `doesn't support 'not_between' 'relation'`, though `/spec.json` lists it for currency |

The filter value is rounded as a write is: with `_c` written `12.345` (reads `"12.35"`), `is 12.345` and
`is 12.35` match it, `is 12.34` and `is 12.3449` do not.

**Summarize** One `_summarize` per type: several `summary_fields` naming one field return a single key,
holding the last type's answer.

| rows | `sum` | `average` | `minimum` | `maximum` | `count` |
|---|---|---|---|---|---|
| 0.1, 0.2, null | `0.3` | `0.15` | `0.1` | `0.2` | `2` |
| 100.10, 200.20, 0.0 | `300.3` | `100.1` | `0.0` | `200.2` | `3` |
| two of 9999999999999.99, null | `19999999999999.98` | `9999999999999.99` | `9999999999999.99` | `9999999999999.99` | `2` |
| -5.5, 5.5, null | `0.0` | `0.0` | `-5.5` | `5.5` | `2` |

`min` and `max` are 400 `type must be one of: record_count, count, sum, maximum, minimum, average, ...`. The sum is exact to the cent, `0.3` and
not `0.30000000000000004`, and may exceed the range one row can hold.

**Traps**
- Two decimals, applied on write at 200: `0.004` stores `0.0` and `12.345` stores `12.35`. Round to cents
  before writing when the stored value must equal what was computed.
- Integer is refused on write and on filter, as for `float`: send `1234.0`, or a string such as
  `"1234.56"`. A `_batch` update accepts it.
- The value is a string on read and a number in `_summarize`. Cast both before comparing.
- There is no currency code. `format_currency_fields_*` is display for the whole site; store the code
  beside the amount.
