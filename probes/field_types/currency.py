"""Q: how does a `currency` field read, write, clear, filter and summarize, and does it carry a
currency code or only a number?

sg-bids stores bid amounts. No live `currency` field exists on the probed site, so this uses the one
`_bids` creates on Bid Line, `sg_zzprobe_currency_amount`, left in place. `/spec.json` gives the type
as `float | null`, range -9999999999999.99 to 9999999999999.99; that is the claim tested.

Read-only half: the field's schema, the site's currency display preferences, and the operator list
(a bogus relation, probe 017). `--write` runs the matrix on three Bid Lines `zzprobe_currency_*` in
the sandbox, deleted on exit; it also creates the probe fields if absent.

    python probes/field_types/currency.py [--write]
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _bids  # noqa: E402
import _lib  # noqa: E402
from _bids import ARR  # noqa: E402

env = _lib.load_env()
c = _lib.client()
S = _bids.slots(c)
T, SL = S["Bid Line"], _bids.slug(S["Bid Line"])
F = _bids.field_name("zzprobe currency amount")
CODE = "zzprobe_currency"
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def raw(text, key):
    """The value as it came over the wire: json.loads would erase the string/number split."""
    m = re.search(rf'"{key}":\s*("(?:[^"\\]|\\.)*"|[^,}}]+)', text)
    return m.group(1) if m else "<absent>"


def err(r):
    return json.dumps(r.json()["errors"][0])


if _lib.writes_allowed():
    _bids.ensure_fields(c, S, out)
live = c.get(f"/schema/{T}/fields").json()["data"]
if F not in live:
    raise SystemExit(f"{F} not on <Bid Line>; run with --write to create it")
d = c.get(f"/schema/{T}/fields/{F}").json()["data"]
out("=== schema, GET /schema/<Bid Line>/fields/" + F)
out(f"  data_type {d['data_type']['value']}, editable {d['editable']['value']}, "
    f"properties {json.dumps({k: v['value'] for k, v in d['properties'].items()})}")
out(f"  top-level keys {sorted(d)}")
prefs = c.get("/preferences").json()["data"]
out(f"  /preferences currency keys: {json.dumps({k: v for k, v in prefs.items() if 'currency' in k})}")
spec = json.dumps(c.get("/spec.json").json())
m = re.search(r"\| currency \|[^|]*\|[^|]*\|[^|\n]*\|", spec)
out(f"  /spec.json row: {m.group(0) if m else 'none'}")
r = c.post(f"/entity/{SL}/_search", headers=ARR, json={"filters": [[F, "definitely_not_an_operator", None]], "fields": [F]})
out(f"\n=== bogus relation -> {r.status_code}\n  {err(r)}")

if not _lib.writes_allowed():
    _lib.emit("field_types/currency", "\n".join(rows), env)
    raise SystemExit("\n(read-only; --write for the write, clear, filter and summarize half)")

SANDBOX = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SANDBOX}
MINE = [["project", "is", P], ["code", "starts_with", CODE]]

with _lib.Created(c) as made:
    A, B, C = (made.add(SL, c.post(f"/entity/{SL}", json={"project": P, "code": f"{CODE}_{s}"}).json()["data"]["id"])
               for s in "abc")

    def put(i, value):
        r = c.put(f"/entity/{SL}/{i}", json={F: value})
        if not r.ok:
            return r.status_code, err(r)
        return r.status_code, raw(c.get(f"/entity/{SL}/{i}", params={"fields": F}).text, F)

    out("\n=== write: sent -> status, read back raw")
    for v in [1234.56, "1234.56", " 4.5 ", 1234, 0, -99.99, 0.004, 0.005, 0.015, 0.025, 1.005, 2.675,
              12.345, 12.3449, 0.1, 1e12, 9999999999999.99, 10000000000000.0, -9999999999999.99,
              -10000000000000.0, 1e15, 1e-9, "1e3", "abc", "", True, "$12.00", "12 USD", "1,234.56",
              {"value": 1.0, "currency": "USD"}]:
        st, got = put(A, v)
        out(f"  {v!r:<38} {st}  {got}")

    r = c.post("/entity/_batch", json={"requests": [{"request_type": "update", "entity": T, "record_id": A, "data": {F: 7}}]})
    out(f"  _batch update with 7 (Integer) -> {r.status_code} {raw(c.get(f'/entity/{SL}/{A}', params={'fields': F}).text, F)}")

    out("\n=== clear")
    for i, label, v in ((A, "_a", 0.0), (B, "_b", None), (C, "_c", 12.5)):
        st, got = put(i, v)
        out(f"  {label} <- {v!r:<6} {st}  reads {got}")
    st, got = put(B, "")
    out(f"  _b <- '' {st}  reads {got}")
    put(B, None)

    def n(filt):
        r = c.post(f"/entity/{SL}/_search", headers=ARR, json={"filters": MINE + [filt], "fields": [F]})
        return len(r.json()["data"]) if r.ok else f"400 {err(r)}"

    out("\n=== filter: _a=0.0, _b=null, _c=12.5")
    for filt in ([F, "is", 12.5], [F, "is", "12.5"], [F, "is", 12], [F, "is", 0.0], [F, "is", 0], [F, "is", None],
                 [F, "is_not", None], [F, "greater_than", 0.0], [F, "less_than", 100.0], [F, "between", [0.0, 12.5]],
                 [F, "not_between", [1.0, 20.0]], [F, "in", [12.5, 0.0]], [F, "not_in", [12.5]], [F, "is", 99999.5]):
        out(f"  {filt[1]:<12} {filt[2]!r:<16} {n(filt)}")
    put(C, 12.345)
    out(f"  _c <- 12.345 reads {raw(c.get(f'/entity/{SL}/{C}', params={'fields': F}).text, F)}")
    for v in (12.345, 12.35, 12.34, 12.3449):
        out(f"  is {v!r:<10} {n([F, 'is', v])}")

    out("\n=== _summarize over the three rows, one call per type: several summary_fields on one field")
    out("    are returned under one key, the last type's (count)")
    for vals in ((0.1, 0.2, None), (100.10, 200.20, 0.0), (9999999999999.99, 9999999999999.99, None),
                 (-5.5, 5.5, None), (0.01, 0.01, 0.01)):
        for i, v in zip((A, B, C), vals):
            put(i, v)
        got = []
        for k in ("sum", "average", "minimum", "maximum", "count"):
            r = c.post(f"/entity/{SL}/_summarize", headers=ARR, json={
                "filters": MINE, "summary_fields": [{"field": F, "type": k}]})
            got.append(f"{k} {raw(r.text, F) if r.ok else err(r)}")
        out(f"  rows {vals}: " + ", ".join(got))
_lib.emit("field_types/currency", "\n".join(rows), env)
