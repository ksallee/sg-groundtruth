"""Write the local overlay: what one Flow Production Tracking site configures, and what one project does.

The site reads `corpus.local/` as its `site` and `project` reading levels. Nothing else produces that
directory. The contract it must match is `site/README.md` and `site/src/lib/content/sources.js`:

    corpus.local/site/findings/<nnn>_<slug>.md          scope: site
    corpus.local/projects/<id>/findings/<nnn>_<slug>.md scope: project, plus a project: key

A slug that matches a shipped entry renders beside that entry's card. A slug that matches nothing
shipped renders in full on /site. Both are used here on purpose.

    python probes/build_overlay.py                 the site, then every FPT_PROBE_SAMPLE_PROJECTS project
    python probes/build_overlay.py --site          the site tier only
    python probes/build_overlay.py --project 70    one project, plus the site tier
    python probes/build_overlay.py --refresh       re-fetch the schema cache instead of reading it

DELIBERATELY UNSCRUBBED. Every other output in this repository goes through `_lib.scrub`, because the
corpus is public documentation. This one is the opposite. `corpus.local/` is gitignored, never
committed and never deployed, and its whole value is the real slot numbers, the real display names and
the real vocabularies of one site. Scrubbing it would leave a reader with what `corpus/` already says.

READ-ONLY. Every call is a GET, a POST to _search or a POST to _summarize. There is no write path here
and none may be added: this runs against a stranger's production site.
"""
import argparse
import json
import re
import shutil
import time
from collections import Counter
from pathlib import Path

import _lib  # first: it is what puts src/ on sys.path

from sg_groundtruth.schema import CUSTOM_RE, Schema, val

OUT = _lib.ROOT / "corpus.local"
CARDS = _lib.ROOT / "corpus" / "findings" / "entity_types"

# probe 004 — _search and _summarize reject application/json with 415 and demand a vendor type.
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}

SAMPLE = 100

# probe 007 — a checkbox reads 100% filled because False is not null, and a summary or calculated
# field is computed rather than entered. Ranking any of them by fill rate says nothing.
RANK_EXCLUDE = {"checkbox", "summary", "calculated", "pivot_column"}
# Summaries and pivots are computed per row on read, so asking for them makes the sample slow for a
# number that is then thrown away.
FETCH_EXCLUDE = {"summary", "pivot_column"}

VOCAB_TYPES = ("list", "status_list", "entity_type")
LINK_TYPES = ("entity", "multi_entity")
# Every row has these and they say nothing about how a project is used.
BOOKKEEPING = {"project", "created_by", "updated_by", "id", "type"}

VALUES_SHOWN = 14
FIELDS_SHOWN = 24


def log(msg):
    print(f"  {msg}", flush=True)


def entity_slug(entity_type):
    """`PublishedFileType` -> `published_file_types`, `Delivery` -> `deliveries`.

    The REST path is the snake-cased schema name, pluralised. Verified against every entity-type card
    in the corpus and against this site's custom slots (`CustomEntity01` -> `custom_entity01s`).
    """
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "_", entity_type).lower()
    if s.endswith("y") and s[-2] not in "aeiou":
        return s[:-1] + "ies"
    if s.endswith(("s", "x", "ch", "sh")):
        return s + "es"
    return s + "s"


def search(c, slug, filters, fields, size=200, sort=None):
    body = {"filters": filters, "fields": fields, "page": {"size": size}}
    if sort:
        body["sort"] = sort
    r = c.post(f"/entity/{slug}/_search", headers=ARR, json=body)
    return r.json()["data"] if r.ok else None


def record_count(c, slug, filters):
    r = c.post(f"/entity/{slug}/_summarize", headers=ARR,
               json={"filters": filters, "summary_fields": [{"field": "id", "type": "record_count"}]})
    return r.json()["data"]["summaries"]["id"] if r.ok else None


def value_of(row, field):
    """probe 003 — an entity field is returned under `relationships`, never under `attributes`."""
    v = row.get("attributes", {}).get(field)
    if v in (None, "", [], {}):
        v = (row.get("relationships", {}).get(field) or {}).get("data")
    return None if v in (None, "", [], {}) else v


# --- markdown ---------------------------------------------------------------

def head(tags, scope, verdict, project=None):
    lines = ["---", f"tags: [{', '.join(tags)}]", f"scope: {scope}"]
    if project:
        lines.append(f"project: {project}")
    # A verdict renders as plain text on the site, one line, so it holds no markup.
    lines += [f"verdict: {verdict.replace('`', '')}", "---", ""]
    return "\n".join(lines)


def table(cols, rows):
    if not rows:
        return []
    return ["| " + " | ".join(cols) + " |",
            "|" + "|".join("---" for _ in cols) + "|"] + \
           ["| " + " | ".join("" if c is None else str(c) for c in r) + " |" for r in rows]


def cell(text):
    """A pipe in a value would end the column, and a value is site data that must not be rewritten."""
    return str(text).replace("|", "\\|")


def joined(values, limit=VALUES_SHOWN):
    shown = ", ".join(f"`{v}`" for v in values[:limit])
    return shown + (f" +{len(values) - limit} more" if len(values) > limit else "")


# --- the site tier ----------------------------------------------------------

def custom_entities(c, types):
    """probe 008 — presence in /schema is the enablement test; an absent slot 404s."""
    custom = {k: v for k, v in types.items() if CUSTOM_RE.match(k) or k.startswith("Custom")}
    enabled = {k: v for k, v in custom.items() if val(v.get("visible", {}), False)}
    plain = sorted(k for k in enabled if not k.endswith("_Connection"))
    connections = sorted(k for k in enabled if k.endswith("_Connection"))

    rows = []
    for k in plain:
        slug = entity_slug(k)
        n = record_count(c, slug, [])
        rows.append((k, cell(val(enabled[k].get("name", {}), k)), f"`{slug}`",
                     "unreadable" if n is None else n))
        log(f"custom {k} -> {slug}: {n} rows")

    body = ["# 008_custom_entities", "",
            f"`/schema` returns {len(types)} entity types on this site, {len(custom)} of them custom "
            "slots. Presence in the listing is the enablement test, so every one of them is enabled "
            "and every other slot 404s when addressed directly.", ""]
    body += ["**Enabled**", ""] + table(["slot", "display name", "REST path", "rows"], rows)
    if connections:
        body += ["", "**Connection slots**", "",
                 "Created by a multi-entity field rather than by an operator, and not addressed "
                 "directly.", ""]
        body += table(["slot", "display name"],
                      [(k, cell(val(enabled[k].get("name", {}), k))) for k in connections])
    body += ["", "The slot numbers are this site's. Nothing about them transfers: read the display "
                 "name from `/schema` and key on it.", ""]
    verdict = (f"{len(plain)} custom entity slots are enabled here"
               + (f", the highest being {plain[-1]}" if plain else "")
               + ". The numbers are non-contiguous and mean nothing on another site.")
    return head(["schema", "custom-entity", "discovery", "inspector"], "site", verdict) + "\n".join(body)


def custom_fields(fields_by_type):
    sections, total, seen = [], 0, 0
    for t, fields in fields_by_type.items():
        rows = []
        for name in sorted(fields):
            if not name.startswith("sg_"):
                continue
            f = fields[name]
            rows.append((f"`{name}`", val(f.get("data_type", {}), "?"),
                         "yes" if val(f.get("editable", {}), False) else "no",
                         cell(val(f.get("name", {}), ""))))
        if rows:
            total += len(rows)
            seen += 1
            sections += [f"### {t}", "", *table(["field", "data type", "editable", "display name"], rows), ""]

    body = ["# 019_create_fields", "",
            f"{total} fields in the `sg_` namespace across {seen} entity types on this "
            "site. `/schema` does not mark which of them shipped with Flow Production Tracking and "
            "which were added here, so this is the whole namespace rather than a list of additions. "
            "It is the input an idempotent `ensure()` reads before deciding whether to create "
            "anything.", ""] + sections
    verdict = (f"{total} `sg_` fields exist across {len(fields_by_type)} entity types here. Read this "
               "before creating one: a duplicate display name silently becomes `<name>_1`.")
    return head(["schema", "custom-field", "discovery", "inspector", "field-type"], "site",
                verdict) + "\n".join(body)


def vocabularies(fields_by_type):
    """probe 009 — valid_values is byte-identical at every scope, so it is a site fact, not a project one."""
    sections, count = [], 0
    for t, fields in fields_by_type.items():
        rows = []
        for name in sorted(fields):
            f = fields[name]
            dt = val(f.get("data_type", {}), "")
            if dt not in VOCAB_TYPES:
                continue
            p = f.get("properties", {})
            values = val(p.get("valid_values", {}), []) or val(p.get("valid_types", {}), []) or []
            if not values:
                continue
            shown = val(p.get("display_values", {}), {}) or {}
            labelled = [f"{v} ({shown[v]})" if shown.get(v) and shown[v] != v else v for v in values]
            count += 1
            rows.append((f"`{name}`", dt, len(values), joined(labelled),
                         val(p.get("default_value", {})) or ""))
        if rows:
            sections += [f"### {t}", "",
                         *table(["field", "data type", "values", "vocabulary", "default"], rows), ""]

    body = ["# 009_status_lists", "",
            f"{count} list, status and entity-type fields define a vocabulary on this site. These are "
            "site-wide: `valid_values` is byte-identical at every scope, and only `hidden_values` "
            "varies by project. Which of these values a given project can actually select is the "
            "project level of this same entry.", ""] + sections
    verdict = (f"{count} fields define a vocabulary here, site-wide. Read the codes from this table, "
               "never the labels: a label is editable and a code is what the API stores.")
    return head(["schema", "status", "list-field", "entity-type", "inspector"], "site",
                verdict) + "\n".join(body)


def storages(c):
    """probes 021 and recipes/004 — the server does the LocalStorage join, so an unset root reads null."""
    rows = c.get("/entity/local_storages",
                 params={"fields": "code,mac_path,windows_path,linux_path,description"}).json()["data"]
    plat = [("mac_path", "local_path_mac"), ("windows_path", "local_path_windows"),
            ("linux_path", "local_path_linux")]
    grid = [(cell(r["attributes"].get("code") or ""), r["id"],
             *[f"`{cell(r['attributes'].get(k))}`" if r["attributes"].get(k) else "null"
               for k, _ in plat]) for r in rows]
    set_on = {k: sum(1 for r in rows if r["attributes"].get(k)) for k, _ in plat}

    body = ["# 021_media_resolution", "",
            f"{len(rows)} LocalStorage row{'' if len(rows) == 1 else 's'} on this site. A "
            "`PublishedFile.path` is returned with the "
            "join already done, so a client never reassembles a root. Which platform paths come back "
            "is decided entirely by this table.", "",
            *table(["storage", "id", "mac_path", "windows_path", "linux_path"], grid), "",
            "**What resolves**", "",
            *table(["path field", "roots set", "reads"],
                   [(f"`{field}`", f"{set_on[k]}/{len(rows)}",
                     "a path" if set_on[k] else "null on every row")
                    for k, field in plat]), ""]
    dead = [field for k, field in plat if not set_on[k]]
    if dead:
        body += [f"{', '.join('`' + d + '`' for d in dead)} read null on every PublishedFile here. "
                 "A client on those platforms falls back to `relative_path` plus a root it holds "
                 "itself.", ""]
    verdict = (f"{len(rows)} LocalStorage root{'' if len(rows) == 1 else 's'} here"
               + (f"; {', '.join(dead)} read null on every row because those roots are unset."
                  if dead else "; every platform path resolves."))
    return head(["storage", "path", "published-file", "media", "inspector"], "site",
                verdict) + "\n".join(body)


def preferences(c):
    """probe 002 — site settings are not under /schema. field_types/duration needs two of these keys."""
    prefs = c.get("/preferences").json()["data"]
    rows = []
    for k in sorted(prefs):
        v = prefs[k]
        s = v if isinstance(v, str) else json.dumps(v)
        rows.append((f"`{k}`", f"`{cell(s[:70])}`" + (f" +{len(s) - 70} chars" if len(s) > 70 else "")))

    hpd, units = prefs.get("hours_per_day"), prefs.get("duration_units")
    body = ["# 101_preferences", "",
            f"`GET /preferences` returns {len(prefs)} keys on this site. Two of them are the only "
            "place the API states what a duration means.", "",
            *table(["key", "value"],
                   [(f"`hours_per_day`", f"`{json.dumps(hpd)}`"),
                    (f"`duration_units`", f"`{json.dumps(units)}`")]), "",
            f"A duration field is a bare integer of minutes and no schema property names the unit "
            f"(`field_types/duration`). Rendering one here means dividing by "
            f"`60 * {hpd}` and labelling it {json.dumps(units)}.", "",
            "**Every key**", "", *table(["key", "value"], rows), ""]
    verdict = (f"{len(prefs)} preference keys here. `hours_per_day` is `{json.dumps(hpd)}` and "
               f"`duration_units` is `{json.dumps(units)}`, which is what a duration has to be "
               "rendered against.")
    return head(["duration", "schema", "inspector", "discovery"], "site", verdict) + "\n".join(body)


# --- the project tier -------------------------------------------------------

def usable_statuses(project, fields_by_type):
    """probe 009 — usable is valid_values minus hidden_values, read with project_id."""
    rows, stray = [], []
    for t, fields in fields_by_type.items():
        for name in sorted(fields):
            f = fields[name]
            if val(f.get("data_type", {}), "") != "status_list":
                continue
            p = f.get("properties", {})
            valid = val(p.get("valid_values", {}), []) or []
            hidden = val(p.get("hidden_values", {}), []) or []
            shown = val(p.get("display_values", {}), {}) or {}
            usable = [v for v in valid if v not in hidden]
            outside = [v for v in hidden if v not in valid]
            if outside:
                stray.append((t, name, outside))
            rows.append((t, f"`{name}`", len(usable), len(hidden),
                         joined([f"{v} ({shown[v]})" if shown.get(v) and shown[v] != v else v
                                 for v in usable]),
                         val(p.get("default_value", {})) or ""))

    hides = [r for r in rows if r[3]]
    body = ["# 009_status_lists", "",
            f"Read with `project_id={project['id']}`. {len(rows)} status fields, {len(hides)} of them "
            "hiding at least one value from this project. `valid_values` is identical at every scope, "
            "so this subtraction is the only project-specific part of the answer.", "",
            *table(["entity type", "field", "usable", "hidden", "usable values", "default"], rows), ""]
    if stray:
        body += ["**`hidden_values` is not a subset of `valid_values`** (`recipes/005`). Subtracting "
                 "is still correct; these codes are simply not on offer either way.", "",
                 *table(["entity type", "field", "hidden but not valid"],
                        [(t, f"`{n}`", joined(v)) for t, n, v in stray]), ""]
    verdict = (f"On {project['name']}, {len(hides)} of {len(rows)} status fields hide values. Subtract "
               "`hidden_values` yourself; the API accepts a hidden code on a write.")
    return head(["status", "list-field", "schema", "project", "inspector"], "project", verdict,
                project["name"]) + "\n".join(body)


def fill_rates(project, sampled, fields_by_type):
    """probe 007 — rank by fill, but drop the data types that read filled because False is not null."""
    summary, sections = [], []
    for t, rows in sampled.items():
        fields = fields_by_type[t]
        ranked = [f for f in fields if val(fields[f].get("data_type", {}), "") not in RANK_EXCLUDE]
        filled = Counter()
        for row in rows:
            filled.update(f for f in ranked if value_of(row, f) is not None)
        used = [(f, filled[f]) for f in sorted(ranked, key=lambda f: (-filled[f], f)) if filled[f]]
        summary.append((t, len(rows), len(ranked), len(used), len(ranked) - len(used)))
        if not used:
            continue
        sections += [f"### {t}", "",
                     *table(["field", "data type", "filled"],
                            [(f"`{f}`", val(fields[f].get("data_type", {}), "?"),
                              f"{n}/{len(rows)}") for f, n in used[:FIELDS_SHOWN]]), ""]
        if len(used) > FIELDS_SHOWN:
            sections += [f"+{len(used) - FIELDS_SHOWN} more populated, "
                         f"{len(ranked) - len(used)} never populated.", ""]
        else:
            sections += [f"{len(ranked) - len(used)} never populated.", ""]

    body = ["# 007_fill_rates", "",
            f"The {SAMPLE} most recent rows per entity type on {project['name']}, counted non-null "
            "field by field. Checkbox, summary, calculated and pivot fields are excluded: `False` and "
            "`0` are not null, so they read as fully populated and cannot be ranked.", "",
            *table(["entity type", "sampled", "fields ranked", "populated", "never populated"], summary),
            "", "A field that is never populated here is one this project does not use. It is not a "
                "field the API refuses.", ""] + sections
    live = [r for r in summary if r[1]]
    verdict = (f"On {project['name']}, {len(summary) - len(live)} of {len(summary)} sampled entity "
               "types hold no rows. "
               + ", ".join(f"{t} populates {pop} of {ranked} rankable fields"
                           for t, _, ranked, pop, _ in sorted(live, key=lambda r: -r[3])[:2]) + ".")
    return head(["fill-rate", "inspector", "schema", "project", "query"], "project", verdict[:200],
                project["name"]) + "\n".join(body)


def link_usage(project, sampled, fields_by_type):
    """probe 005 — which field a row actually hangs off, measured rather than assumed."""
    sections, live = [], 0
    for t, rows in sampled.items():
        if not rows:
            continue
        fields = fields_by_type[t]
        links = [f for f in sorted(fields)
                 if val(fields[f].get("data_type", {}), "") in LINK_TYPES and f not in BOOKKEEPING]
        grid = []
        for f in links:
            targets = Counter()
            for row in rows:
                v = value_of(row, f)
                for item in (v if isinstance(v, list) else [v]):
                    if isinstance(item, dict) and item.get("type"):
                        targets[item["type"]] += 1
            present = sum(1 for row in rows if value_of(row, f) is not None)
            if present:
                grid.append((f"`{f}`", val(fields[f].get("data_type", {}), "?"),
                             f"{present}/{len(rows)}",
                             ", ".join(f"{k} {v}" for k, v in targets.most_common(4))))
        live += len(grid)
        dead = len(links) - len(grid)
        sections += [f"### {t}", ""]
        sections += table(["field", "data type", "set on", "points at"], grid) if grid else \
            ["No link field on this type is set on any sampled row."]
        sections += ["", f"{dead} of {len(links)} link fields are empty on every sampled row.", ""]

    body = ["# 005_link_usage", "",
            f"Which entity and multi-entity fields actually hold anything on {project['name']}, from "
            f"the same {SAMPLE}-row sample as the fill rates. `project`, `created_by` and `updated_by` "
            "are excluded: every row has them and they say nothing about how the project is used.", "",
            "A client that hardcodes a link field is guessing. Read the field that is set here, and "
            "read what it points at rather than assuming the type.", ""] + sections
    verdict = (f"On {project['name']}, {live} link fields hold a value across "
               f"{len([t for t in sampled if sampled[t]])} entity types. Measure the link field per "
               "project rather than hardcoding one.")
    return head(["link", "entity-field", "multi-entity", "inspector", "project"], "project", verdict,
                project["name"]) + "\n".join(body)


def pages(c, project, schemas):
    """probe 023 — a page's layout is the PageSetting row whose `user` is null; the grid is at
    children.body.children.list_content.settings.columns, as schema field names."""
    fields = ["name", "page_type", "entity_type", "ui_category", "system_owned", "description"]
    rows = search(c, "pages", [["project", "is", {"type": "Project", "id": project["id"]}]],
                  fields, size=500) or []
    log(f"pages: {len(rows)}")
    settings = []
    if rows:
        ids = [{"type": "Page", "id": p["id"]} for p in rows]
        settings = search(c, "page_settings", [["page", "in", ids]],
                          ["page", "user", "settings_json"], size=500) or []
    shared = {}
    for s in settings:
        page = (s["relationships"].get("page") or {}).get("data")
        user = (s["relationships"].get("user") or {}).get("data")
        if page and user is None:
            shared[page["id"]] = s["attributes"]["settings_json"]

    def columns(tree):
        if not isinstance(tree, dict):
            return None
        body = (tree.get("children") or {}).get("body") or {}
        grid = (body.get("children") or {}).get("list_content") or {}
        return (grid.get("settings") or {}).get("columns")

    grid, detail, laid_out = [], [], 0
    def order(p):
        cols = columns(shared.get(p["id"]))
        return (0 if cols else 1, p["attributes"].get("entity_type") or "",
                p["attributes"].get("name") or "")

    for p in sorted(rows, key=order):
        a = p["attributes"]
        cols = columns(shared.get(p["id"]))
        grid.append((p["id"], cell(a.get("name") or "unnamed"), a.get("page_type") or "",
                     a.get("entity_type") or "", len(cols) if cols else 0))
        if not cols:
            continue
        laid_out += 1
        known = schemas.get(a.get("entity_type"))
        missing = [x for x in cols if known is not None and x.split(".")[0] not in known]
        detail += [f"### {cell(a.get('name') or 'Page ' + str(p['id']))}", "",
                   f"`{a.get('entity_type')}`, page {p['id']}, `page_type` "
                   f"`{a.get('page_type')}`. {len(cols)} columns, in order.", "",
                   "```", ",".join(cols), "```", ""]
        if missing:
            detail += [f"{len(missing)} of these are absent from `/schema/{a.get('entity_type')}"
                       f"/fields`: {joined(missing)}. `?fields` ignores a name a type does not have, "
                       "so a stale column is silent rather than a 400.", ""]

    body = ["# 023_pages", "",
            f"{len(rows)} Pages belong to {project['name']}, {laid_out} of them with a column "
            "list. The layout is the `PageSetting` row whose `user` is null; a per-user row is a patch "
            "over it, not a tree. The columns are schema field names and can be handed to `?fields` "
            "verbatim.", "",
            *table(["id", "page", "page_type", "entity type", "columns"], grid), ""]
    if detail:
        body += ["This is what the team looks at, in the order they look at it.", ""] + detail
    verdict = (f"{laid_out} of {len(rows)} Pages on {project['name']} hold a column list. Read it "
               "from the PageSetting whose `user` is null and feed it straight to `?fields`.")
    return head(["page", "project", "query", "inspector", "schema"], "project", verdict,
                project["name"]) + "\n".join(body)


# --- assembly ---------------------------------------------------------------

def profile_types(sc, refresh):
    """The entity types the corpus documents, plus the custom slots this site enabled.

    probe 002 — /schema/<Type>/fields is 48KB and ~330ms each, so the set is bounded and cached rather
    than looped over all 114 types.
    """
    documented = sorted(p.stem for p in CARDS.glob("*.md"))
    types = sc.entity_types(refresh)
    custom = sorted(k for k, v in types.items()
                    if (CUSTOM_RE.match(k) or k.startswith("Custom"))
                    and val(v.get("visible", {}), False) and not k.endswith("_Connection"))
    return [t for t in documented + custom if t in types], types


def read_fields(sc, types, refresh, label):
    out = {}
    for i, t in enumerate(types, 1):
        t0 = time.time()
        try:
            out[t] = sc.fields(t, refresh)
        except RuntimeError as e:
            log(f"{label} {t}: {e}")
            continue
        log(f"{label} {i}/{len(types)} {t}: {len(out[t])} fields ({(time.time() - t0) * 1000:.0f}ms)")
    return out


def sample_rows(c, project_id, fields_by_type):
    out = {}
    for i, (t, fields) in enumerate(fields_by_type.items(), 1):
        if "project" not in fields:
            continue
        wanted = [f for f in sorted(fields)
                  if val(fields[f].get("data_type", {}), "") not in FETCH_EXCLUDE]
        t0 = time.time()
        rows = search(c, entity_slug(t), [["project", "is", {"type": "Project", "id": project_id}]],
                      wanted, size=SAMPLE, sort=["-id"])
        if rows is None:
            log(f"sample {t}: unreadable, skipped")
            continue
        out[t] = rows
        log(f"sample {i}/{len(fields_by_type)} {t}: {len(rows)} rows ({(time.time() - t0) * 1000:.0f}ms)")
    return out


def write_tier(root, files):
    """Replace one tier wholesale. Every file is built in memory first, so a run that fails partway
    leaves the previous overlay untouched rather than half of a new one."""
    if root.exists():
        shutil.rmtree(root)
    for rel, text in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text if text.endswith("\n") else text + "\n")
    return sorted(files)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--site", action="store_true", help="the site tier only")
    ap.add_argument("--project", type=int, action="append",
                    help="one project id; repeatable. Defaults to FPT_PROBE_SAMPLE_PROJECTS")
    ap.add_argument("--refresh", action="store_true", help="re-fetch the schema cache")
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args(argv)

    started = time.time()
    env = _lib.load_env()
    c = _lib.client()

    print(f"site tier -> {args.out}/site")
    sc = Schema(c)
    types, all_types = profile_types(sc, args.refresh)
    log(f"{len(all_types)} entity types on this site; profiling {len(types)}")
    fields = read_fields(sc, types, args.refresh, "schema")

    written = write_tier(args.out / "site", {
        "findings/008_custom_entities.md": custom_entities(c, all_types),
        "findings/009_status_lists.md": vocabularies(fields),
        "findings/019_create_fields.md": custom_fields(fields),
        "findings/021_media_resolution.md": storages(c),
        "findings/101_preferences.md": preferences(c),
    })
    for w in written:
        log(f"wrote site/{w}")

    if args.site:
        print(f"\ndone in {time.time() - started:.0f}s")
        return 0

    # Project ids are site data, so they are never hardcoded: `_lib.sample_projects` reads
    # FPT_PROBE_SAMPLE_PROJECTS and fails naming the variable when it is unset.
    ids = args.project or _lib.sample_projects(c, env)
    names = {p["id"]: p["attributes"].get("name") or str(p["id"])
             for p in c.get("/entity/projects", params={"fields": "name", "page[size]": 500}).json()["data"]}

    schemas = {t: set(f) for t, f in fields.items()}
    for pid in ids:
        project = {"id": pid, "name": names.get(pid, str(pid))}
        print(f"\nproject {pid} {project['name']} -> {args.out}/projects/p{pid}")
        psc = Schema(c, pid)
        pfields = read_fields(psc, types, args.refresh, "schema")
        sampled = sample_rows(c, pid, pfields)
        written = write_tier(args.out / "projects" / f"p{pid}", {
            "findings/005_link_usage.md": link_usage(project, sampled, pfields),
            "findings/007_fill_rates.md": fill_rates(project, sampled, pfields),
            "findings/009_status_lists.md": usable_statuses(project, pfields),
            "findings/023_pages.md": pages(c, project, schemas),
        })
        for w in written:
            log(f"wrote projects/p{pid}/{w}")

    print(f"\ndone in {time.time() - started:.0f}s. Build the site: cd site && npm run dev")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
