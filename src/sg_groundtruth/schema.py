"""Schema cache: raw JSON on disk, a compact digest over it, and a query CLI on top.

The agent asks; it does not read (DESIGN: cheap index, expensive body).

probe 002 — /schema is 13KB and names 113 entity types, but /schema/<Type>/fields is 42KB and ~300ms
for ONE type. So field sets are fetched a type at a time, never in bulk, and cached until refreshed
explicitly. project_id changes both responses (probe 009: hidden_values is what varies), so the cache
is keyed by project as well as by site.
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from .client import FPT
from .env import ROOT, load as load_env

CACHE = ROOT / ".schema-cache"

# probe 008 — enabled custom entities are the ones /schema returns at all; slot numbers are
# non-contiguous and site-specific, so match the shape and read the display name.
CUSTOM_RE = re.compile(r"^Custom(NonProject)?Entity\d+$")


def val(prop, default=None):
    """Schema properties arrive wrapped as {"value": x, "editable": bool}."""
    return prop.get("value", default) if isinstance(prop, dict) else (prop if prop is not None else default)


def usable_values(field_schema):
    """(label, code) actually selectable for a list field, in valid_values order.

    probe 009 — usable is valid_values MINUS hidden_values, and only hidden_values varies by project;
    valid_values alone is identical at every scope and is not the answer. Labels are not decoration:
    a raw code like 'pndvs' means nothing to an operator.
    """
    p = field_schema.get("properties", {})
    valid = val(p.get("valid_values", {}), []) or []
    hidden = val(p.get("hidden_values", {}), []) or []
    shown = val(p.get("display_values", {}), {}) or {}
    return [(shown.get(v, v), v) for v in valid if v not in hidden]


class Schema:
    """Cached schema for one site, optionally scoped to one project."""

    def __init__(self, fpt, project_id=None, cache=CACHE):
        self.fpt = fpt
        self.project_id = int(project_id) if project_id else None
        site = re.sub(r"[^\w.-]", "_", fpt.site.split("//")[-1])
        self.dir = Path(cache) / site / (f"p{self.project_id}" if self.project_id else "site")

    def _params(self):
        return {"project_id": self.project_id} if self.project_id else {}

    def _cached(self, name, path, refresh=False):
        f = self.dir / f"{name}.json"
        if f.is_file() and not refresh:
            return json.loads(f.read_text())
        r = self.fpt.get(path, params=self._params())
        if not r.ok:
            raise RuntimeError(f"{path} -> {r.status_code} {r.text[:200]}")
        blob = {"fetched_at": time.time(), "path": path, "data": r.json()["data"]}
        self.dir.mkdir(parents=True, exist_ok=True)
        f.write_text(json.dumps(blob, indent=2))
        return blob

    def entity_types(self, refresh=False):
        """{EntityType: {"name": {...}, "visible": {...}}} — every type this site exposes."""
        return self._cached("_entity_types", "/schema", refresh)["data"]

    def fields(self, entity_type, refresh=False):
        """{field_name: field_schema} for one entity type. The expensive call; cache it."""
        return self._cached(entity_type, f"/schema/{entity_type}/fields", refresh)["data"]

    def field(self, entity_type, name, refresh=False):
        return self.fields(entity_type, refresh).get(name)

    def statuses(self, entity_type="Version", field="sg_status_list", refresh=False):
        f = self.field(entity_type, field, refresh)
        return usable_values(f) if f else []

    def age(self, name):
        f = self.dir / f"{name}.json"
        return time.time() - json.loads(f.read_text())["fetched_at"] if f.is_file() else None

    def cached_types(self):
        return sorted(p.stem for p in self.dir.glob("*.json") if not p.stem.startswith("_"))


# --- digests: what the CLI prints, and what an agent should read instead of the raw JSON ---

def digest_entities(types, custom_only=False):
    rows = []
    for name in sorted(types):
        display = val(types[name].get("name", {}), name)
        custom = bool(CUSTOM_RE.match(name)) or name.startswith("Custom")
        if custom_only and not custom:
            continue
        rows.append(f"  {name:<34} {display}")
    return rows


def digest_fields(fields, data_type=None, editable_only=False):
    rows = []
    for name in sorted(fields):
        f = fields[name]
        dt = val(f.get("data_type", {}), "?")
        if data_type and dt != data_type:
            continue
        editable = val(f.get("editable", {}), False)
        if editable_only and not editable:
            continue
        flags = "".join(c for c, on in (("E", editable),
                                        ("M", val(f.get("mandatory", {}), False)),
                                        ("U", val(f.get("unique", {}), False))) if on)
        rows.append(f"  {name:<38} {dt:<14} {flags:<3} {val(f.get('name', {}), '')}")
    return rows


def digest_field(name, f):
    """One field, whole. Small enough to read; the raw entry is not."""
    out = [f"{name}  ({val(f.get('entity_type', {}), '?')})"]
    for k in ("name", "data_type", "editable", "mandatory", "unique", "description"):
        if k in f:
            out.append(f"  {k:<12} {val(f[k])}")
    p = f.get("properties", {})
    for k in sorted(p):
        v = val(p[k])
        if v not in (None, "", [], {}):
            out.append(f"  {k:<12} {json.dumps(v)[:300]}")
    return out


def _client_and_schema(args):
    fpt = FPT.from_env(load_env())
    return Schema(fpt, args.project)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="fpt-schema", description=__doc__.split("\n")[0])
    ap.add_argument("--project", type=int, help="scope to one project (statuses need this)")
    ap.add_argument("--refresh", action="store_true", help="re-fetch instead of reading the cache")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("entities", help="entity types this site exposes")
    e.add_argument("--custom", action="store_true", help="only CustomEntityNN slots (probe 008)")

    f = sub.add_parser("fields", help="fields on one entity type")
    f.add_argument("entity_type")
    f.add_argument("--type", dest="data_type", help="filter by data_type")
    f.add_argument("--editable", action="store_true")

    one = sub.add_parser("field", help="one field, in full")
    one.add_argument("entity_type")
    one.add_argument("name")

    s = sub.add_parser("statuses", help="usable status values (probe 009)")
    s.add_argument("entity_type", nargs="?", default="Version")
    s.add_argument("--field", default="sg_status_list")

    sub.add_parser("cache", help="what is cached, and how old")

    args = ap.parse_args(argv)
    sc = _client_and_schema(args)

    if args.cmd == "entities":
        types = sc.entity_types(args.refresh)
        print("\n".join(digest_entities(types, args.custom)))
        print(f"\n{len(types)} entity types")
    elif args.cmd == "fields":
        fields = sc.fields(args.entity_type, args.refresh)
        rows = digest_fields(fields, args.data_type, args.editable)
        print("\n".join(rows))
        print(f"\n{len(rows)} of {len(fields)} fields on {args.entity_type}"
              + (f" (project {sc.project_id})" if sc.project_id else ""))
    elif args.cmd == "field":
        f = sc.field(args.entity_type, args.name, args.refresh)
        if not f:
            raise SystemExit(f"{args.entity_type} has no field {args.name}")
        print("\n".join(digest_field(args.name, f)))
    elif args.cmd == "statuses":
        if not sc.project_id:
            print("no --project: this is the site-wide list, which hides nothing (probe 009)",
                  file=sys.stderr)
        for label, code in sc.statuses(args.entity_type, args.field, args.refresh):
            print(f"  {code:<10} {label}")
    elif args.cmd == "cache":
        print(f"  {sc.dir}")
        for name in ["_entity_types"] + sc.cached_types():
            age = sc.age(name)
            if age is not None:
                print(f"  {name:<24} {age / 3600:.1f}h old")


if __name__ == "__main__":
    main()
