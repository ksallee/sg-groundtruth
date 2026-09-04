# Endpoint cards

One card per REST call, named by the call. The card holds what is true of the endpoint rather than of a
data type or an entity type: what it takes, what it answers, what a real response looks like, and the
edge cases that live on the call.

It does not restate a finding. Every finding and recipe names its `endpoints:`, and the index and the
site render those verdicts under the card, so the quirks are on the page without being written twice.

`endpoint:` is the canonical spelling and the identity. `<type>` is the plural URL segment, `<Type>` the
schema name, `<id>` a row id, `<field>` a field name.

Every card states `coverage:`: `measured` when every call on it was made and answered, otherwise
`partial` or `untested` with an `unmeasured:` line saying what was not reached. A card is the unit a
docs sweep adds, so it is written before anything has been probed and the key is what keeps that
visible. The index and the site badge anything that is not `measured` and repeat the reason on the
row and on the page.
