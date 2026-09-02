---
tags: [field-type, password, filter, operator, schema, dotted-field, inspector, trap]
scope: api
summary: An account credential, which reads back as a constant mask and is never returned.
verdict: A password field reads as a constant seven-asterisk mask on every row, including through a dotted path; it cannot be filtered, sort is accepted and ignored, and it must never be written.
---

# password

**Data type** `password`, probed read-only on `HumanUser.password_proxy` and `ClientUser.password_proxy`.
On the probed site those are the only two `password` fields across all 114 entity types, and both are stock:

| field | `editable` | rows on the probed site |
|---|---|---|
| `HumanUser.password_proxy` | `false` | 24 |
| `ClientUser.password_proxy` | `true` | 0, so its write path is unmeasured |

| operation | outcome |
|---|---|
| read | 200, the constant string `"*******"`, never `null`, never absent |
| dotted read through a link | 200, the same mask, flat in `attributes` |
| create, update, clear | not attempted; see **Write** |
| filter, any relation, flat or dotted | 400 code 103 `data type cannot be used in a filter` |
| sort, `_search` and `GET`, both directions | 200, order unchanged |

`GET /schema/HumanUser/fields/password_proxy` returns eleven keys and nothing type-specific:

| key | value | same on `ClientUser` |
|---|---|---|
| `name` | `"Password"`, editable | yes |
| `data_type` | `password`, not editable | yes |
| `editable` | `false`, not editable | no, `true` |
| `mandatory`, `unique` | `false`, not editable | yes |
| `visible`, `ui_value_displayable` | `true`, not editable | yes |
| `description`, `custom_metadata` | `""`, editable | yes |
| `entity_type` | the type, not editable | yes |
| `properties` | `{default_value: null, summary_default: "none"}` | yes |

`properties` holds the two keys every field gets: no hash algorithm, no policy, no minimum length.

**Read** A plain string in `attributes`, never under `relationships`, returned when named in `fields` and
in `fields=*`. The mask is one shared constant, not a rendering of the stored value:

| measurement, on the probed site | result |
|---|---|
| distinct values across 24 `HumanUser` rows | 1 |
| lengths seen | `[7]` |
| `null` values | 0 |

The mask leaks neither the credential nor its length, and never says whether an account has a password:
do not read `password_proxy` as a set or unset flag. It survives a dotted path like any attribute (probe 003):

| `?fields=` on `/entity/versions` | in the 200 |
|---|---|
| `created_by.HumanUser.password_proxy`, creator is a `HumanUser` | `"*******"`, flat under that literal key |
| `created_by.HumanUser.password_proxy`, creator is not a `HumanUser` | `null` |
| `sg_not_a_real_field` | absent, the unknown-field behaviour of probe 004 |

A row-copy job that walks `/schema/<Type>/fields` and reads every key will put `"*******"` in its output.
That is a fake value, not a credential: writing it back would set the literal string as someone's password.

**Write** Not attempted, at any flag, on either field. A `password` field holds the credential of a real
account on a live site, and there is no sandbox account to spend: setting one locks out the person or
script that owns it, and no prior value is returned to restore. What the schema claims, unverified:

| field | `editable` | what that implies |
|---|---|---|
| `ClientUser.password_proxy` | `true` | the schema admits a write; the site has no `ClientUser` to try it on |
| `HumanUser.password_proxy` | `false` | a write would be refused, on the `is read only` path of `calculated` |

`editable` itself is `editable: false` on both, so a client cannot flip the flag through
`PUT /schema/<Type>/fields/<field>` first.

**Clear** Not attempted, for the same reason. Clearing a credential is a write, and an account whose
password is cleared is an account nobody can sign into.

**Filter** No relation is accepted, and none is enumerated. `password` is one of the types that answers a
bogus operator with no `Valid relations` list, the way `calculated` does rather than the way `text` does
(probe 017):

```
["password_proxy", "definitely_not_an_operator", null] -> 400
 status: 400  code: 103
 title:  "API read() HumanUser.password_proxy's 'password' data type cannot be used in a filter."
 source: {"HumanUser.password_proxy": " data type cannot be used in a filter. Value:
          {"path" => "password_proxy", "relation" => "definitely_not_an_operator",
           "values" => [nil]}"}
```

Every form returns that identical `title`, with only `path`, `relation` and `values` differing in `source`:

| filter | result |
|---|---|
| `["password_proxy", "is", null]` | 400 code 103 |
| `["password_proxy", "is_not", null]` | 400, same string |
| `["password_proxy", "is", "<string>"]` | 400, same string |
| `["password_proxy", "contains", "<string>"]` | 400, same string |
| `GET ?filter[password_proxy]=<string>` | 400, same string |
| `["created_by.HumanUser.password_proxy", "is", "<string>"]` on `Version` | 400, same string |

The dotted form is refused by the same check, so linking through another entity is not a way around it.
No relation returns rows, so there is no oracle to binary-search a credential with.

**Sort** Accepted and ignored, which is the one place this type is quiet about refusing:

| call | ids returned |
|---|---|
| `_search {"sort": "password_proxy"}` | `[3, 17, 18, 19, 21]` |
| `_search {"sort": "-password_proxy"}` | `[3, 17, 18, 19, 21]` |
| `GET ?sort=password_proxy` | `[3, 17, 18, 19, 21]` |
| `GET ?sort=id`, control | `[3, 17, 18, 19, 21]` |
| `GET ?sort=-id`, control | `[418, 385, 352, 319, 287]` |

Ascending and descending are identical and both match default order, while `-id` reorders. No ordering
information is disclosed, and no error tells the caller the sort key did nothing.

**Traps**
- The field passes every generic inspector test (`visible: true`, `ui_value_displayable: true`, present in
  `/schema/<Type>/fields`) and returns a value, so exclude `data_type == "password"` by name from field
  pickers, from row exports and from anything that echoes a read back into a write.
- Fill-rate scanning reads 100%, and the `is_not None` correction 400s. Drop the type before ranking,
  the way probe 007 drops `checkbox`.
- A sort on a `password` field is a silent no-op. Validate a user-supplied sort key against the schema
  rather than trusting a 200 to mean the rows came back ordered.
- `ClientUser.password_proxy` reports `editable: true`. Treat that as a schema claim only: no probe writes
  a `password` field, and neither should a client.
