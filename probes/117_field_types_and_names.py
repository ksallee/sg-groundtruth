"""Q: can `currency`, `timecode`, `footage` and `color` fields be created with a name alone, and
what programmatic name does the server derive from a display name with accents, non-Latin letters,
repeated punctuation, a leading digit, outer spaces or great length?

Writes only, behind `--write`, on Version. `status_list`, `entity` and `multi_entity` are in probe
116, with their settings.

**The first run stopped at its first create.** `currency` with the display name
`zzprobe 117 Durée Écran ñ` answered 201 and the field was named `sg_currency`: the display name
gave nothing to the programmatic name. This probe's guard refuses to touch a name without `zzprobe`
in it, so the run ended there with `sg_currency` live. That name was not meant to be spent.

This version starts from that state. It reports `sg_currency` and retires it only if its display
name is the one this probe sent. Every naming case after it is then sent as a `currency` field: if
the server falls back to the data type again, the name it wants is the retired `sg_currency` and the
create is refused, so no second name outside `zzprobe` can be spent.

Two display names cannot begin `zzprobe 117`: the leading digit and the leading spaces are what is
measured. Both still hold `zzprobe`.

The last section takes back `sg_zzprobe_116_list`, a name probe 116 spent, to send the
default_value clears 116 did not send, and retires it again.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
out = []
TYPE = "Version"
ACCENTED = "zzprobe 117 Durée Écran ñ"
FALLBACK = "sg_currency"
made = []

if not _lib.writes_allowed():
    raise SystemExit("probe 117 only writes; run with --write")


def errs(r):
    if not r.content:
        return "(empty body)"
    try:
        j = r.json()
    except ValueError:
        return r.text[:400]
    if isinstance(j, dict) and "errors" in j:
        return json.dumps([{k: e.get(k) for k in ("status", "code", "title", "source", "detail")
                            if e.get(k) is not None} for e in j["errors"]], ensure_ascii=False)
    return ""


def head(t):
    out.append(f"\n\n===== {t}")


def prop(**kv):
    return [{"property_name": k, "value": v} for k, v in kv.items()]


def rec(name):
    r = c.get(f"/schema/{TYPE}/fields/{name}")
    return r.json()["data"] if r.status_code == 200 else None


def mine(name):
    """A name this probe may write to: one holding `zzprobe`, or the fallback under our display name."""
    if "zzprobe" in name and ("116" in name or "117" in name):
        return True
    d = rec(name)
    return name == FALLBACK and (d is None or d["name"]["value"] == ACCENTED)


def path(name):
    assert mine(name), name
    return f"/schema/{TYPE}/fields/{name}"


def litter():
    d = c.get(f"/schema/{TYPE}/fields").json()["data"]
    return sorted(k for k, v in d.items() if "zzprobe" in k or "zzprobe" in v["name"]["value"])


def create(data_type, display, **extra):
    body = {"data_type": data_type, "properties": prop(name=display, **extra)}
    r = c.post(f"/schema/{TYPE}/fields", json=body)
    out.append(f"POST  data_type={data_type}  name={json.dumps(display, ensure_ascii=False)} "
               f"({len(display)} chars){'  ' + json.dumps(extra) if extra else ''}\n"
               f"  -> {r.status_code}  {errs(r)}")
    if r.status_code != 201:
        out.append(f"  fields with zzprobe in either name, listed after the refusal: {litter()}")
        return None
    name = r.json()["links"]["self"].rsplit("/", 1)[-1]
    made.append(name)
    d = r.json()["data"]
    out.append(f"  created {name} ({len(name)} chars)\n"
               f"  name reads {json.dumps(d['name']['value'], ensure_ascii=False)}; data_type "
               f"{d['data_type']['value']}; properties "
               f"{json.dumps({k: v['value'] for k, v in d['properties'].items()})}")
    return name


def retire(name):
    p = path(name)
    r = c.delete(p)
    out.append(f"  DELETE {name} -> {r.status_code}; live after: {rec(name) is not None}")
    if name in made:
        made.remove(name)


def update(name, label, body, watch):
    before = rec(name)
    r = c.put(path(name), json=body)
    after = rec(name)
    b, a = before, after
    for k in watch.split("."):
        b, a = (b or {}).get(k), (a or {}).get(k)
    out.append(f"PUT  {json.dumps(body)}\n  [{label}] -> {r.status_code}  {errs(r)}\n"
               f"  {watch}: {'changed to ' + json.dumps(a) if a != b else 'unchanged, ' + json.dumps(a)}")


try:
    head(f"currency, name alone, display name {ACCENTED!r}: the first run's create")
    d = rec(FALLBACK)
    if d is None:
        out.append(f"{FALLBACK} is not live")
    elif d["name"]["value"] != ACCENTED:
        raise SystemExit(f"{FALLBACK} is live under another display name: not this probe's field")
    else:
        out.append(f"{FALLBACK} is live; name reads {json.dumps(d['name']['value'], ensure_ascii=False)}; "
                   f"data_type {d['data_type']['value']}; properties "
                   f"{json.dumps({k: v['value'] for k, v in d['properties'].items()})}")
        retire(FALLBACK)

    head("the same create again, and a non-Latin name, now that sg_currency is retired")
    for display in (ACCENTED, "zzprobe 117 日本語 поле"):
        n = create("currency", display)
        if n:           # a name was spent after all: send no second one
            retire(n)
            break

    head("currency with ASCII display names")
    n = create("currency", "zzprobe 117 currency")
    ascii_named = bool(n)   # false would mean the type, not the accents, decided the name
    if n:
        update(n, "unique true", {"properties": prop(unique=True)}, "unique")
        update(n, "default_value", {"properties": prop(default_value=1.5)}, "properties.default_value")
        retire(n)
    for display in ("zzprobe 117 a--b..c!!d  e_f", "117 zzprobe digit", "  zzprobe 117 spaces  ",
                    "zzprobe 117 MiXed CASE"):
        n = create("currency", display)
        if n:
            retire(n)
    for length in (120, 70, 60):
        n = create("currency", ("zzprobe 117 long " + "abcdefghij" * 12)[:length])
        if n:
            retire(n)
            break

    head("the other types, each with a name alone")
    for dt in ("timecode", "footage", "color") if ascii_named else ():
        n = create(dt, f"zzprobe 117 {dt}")
        if n:
            retire(n)

    head("sg_zzprobe_116_list revived: clearing a default_value")
    old = "sg_zzprobe_116_list"
    r = c.post(path(old), json={"revive": True})
    out.append(f"POST revive -> {r.status_code}  {errs(r)}")
    if rec(old):
        made.append(old)
        d = rec(old)
        out.append(f"  after the revive: name {json.dumps(d['name']['value'])}, properties "
                   f"{json.dumps({k: v['value'] for k, v in d['properties'].items()})}")
        DV = "properties.default_value"
        update(old, "default_value \"\"", {"properties": prop(default_value="")}, DV)
        update(old, "default_value back to a valid value", {"properties": prop(default_value="beta")}, DV)
        update(old, "default_value null, sent with valid_values", {"properties": prop(
            valid_values=["beta", "gamma"], default_value=None)}, DV)
        retire(old)
finally:
    for name in list(made):
        retire(name)
    out.append(f"\nfields with zzprobe in either name still listed on {TYPE}: {litter()}")

_lib.emit("117_field_types_and_names", "\n".join(out), env)
