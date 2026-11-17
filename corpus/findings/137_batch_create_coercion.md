---
tags: [batch, create, custom-entity, number, date, trap]
endpoints: [POST /entity/_batch, POST /entity/<type>, POST /schema/<Type>/fields]
phase: write
scope: api
measured: sandbox project written, 2026-11-11; 25 rows on a custom slot, one float field created and retired
verdict: A `_batch` create on a custom entity takes a numeric string in a float and honours `created_at`, as a single POST does. It also takes an Integer and `"1e3"`, which a single POST refuses.
---

# 137_batch_create_coercion

**Q** In a `_batch` create on a custom entity, is a numeric string accepted in a float field, and is
`created_at` honoured, as they are on a single `POST`?

**Endpoint** `POST /entity/_batch ; POST /entity/<type>`

**Docs claim** Silent. `field_types/float` and probe 070 measured single writes; report 001 found a
batch create skipping validation.

**Actual**

```
sent                         single POST                                    _batch create (one request)
float "1.5"                  201 "1.5"                                      200 "1.5"
float " 2.25 "               201 "2.25"                                     200 "2.25"
float "3"                    201 "3.0"                                      200 "3.0"
float 1.5                    201 "1.5"                                      200 "1.5"
float 1 (Integer)            400 code 103 API create() CustomEntityNN.<f>   200 "1.0"
                               expected [String, BigDecimal, Float, NilClass]
                               data type(s) but got Integer: 1
float "1e3"                  400 code 103 Invalid data for 'float' data type 200 "1000.0"
float "abc"                  400 code 103 Invalid data for 'float' ...      400 code 104 Invalid field value, update
                                                                              failed [5 - Update failed for
                                                                              [CustomEntityNN.<f>]: Value is not legal.]
created_at "...03:04:05Z"    201 2020-01-02T03:04:05Z                       200 the same
created_at ".123+05:00"      201 2020-01-01T22:04:05Z                       200 the same
created_at and updated_at    201 both as sent                               200 both as sent
created_at "bogus"           400 code 103 Invalid date time format: bogus.  400 code 104 ... [CustomEntityNN.created_at]:
                               Correct format is 2011-01-21T13:26:09Z ...     Value is not legal.

one _batch, three creates, float "4.5" and created_at -> 200, all three "4.5" and 2020-01-02T03:04:05Z
```

**Teaches**
- Send floats as strings in either path: `"1.5"` is accepted by both and reads back as a string.
- `created_at` and `updated_at` in a batch create are stored as sent, offsets normalised to UTC, as on
  a single `POST` (probe 070). Stamp capture time this way.
- The batch path is wider than the single one: an Integer and an exponent string both store. Code
  that is tested by batch can fail by single `POST`, so validate before sending rather than relying
  on either (report 001).
- A refused batch value is code 104 `Value is not legal.` naming the field; the single path's code
  103 says which types it takes. Debug a batch refusal by sending that request alone.
