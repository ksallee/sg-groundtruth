#!/usr/bin/env python3
"""Score three reading strategies against the tasks in tasks.json.

    python experiments/retrieval/score.py              per-task tables, then the summary
    python experiments/retrieval/score.py --doors      what each door holds and what it costs
    python experiments/retrieval/score.py --per-call   `doors` reads one call's block, not the family
    python experiments/retrieval/score.py --no-recipes `doors` does not open the recipes door

A task is a brief, a plan an agent holds before it reads anything, and the entries whose rules the
brief needs. A strategy is a rule for deciding what to read from the plan alone. Two numbers come
out: whether the required rule was in what was read, and how much was read, as chars/4.

`corpus/doors/` is read when it exists (issue #56). Until it lands the same tiers are built here
from each entry's own rule section, so the number is the layout's and not the generator's.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CORPUS = ROOT / "corpus"
DOORS_DIR = CORPUS / "doors"

# Mirrors probes/index.py. Copied rather than imported: this file is read next to the issue it
# scores, and the import would drag the index generator in behind it.
FAMILIES = ["Session", "Site", "Schema", "Records", "Search", "Media", "Attention",
            "Webhooks", "Exports", "Other"]
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]
SITE_PREFIXES = ("/spec.", "/preferences", "/license_info", "/schedule/", "/subscription_seat/")
ATTENTION = ("follow", "activity_stream", "thread_contents")
PHASES = ["auth", "protocol", "schema", "read", "filter", "write", "upload", "observe", "render"]

# group -> (glob under corpus/, the key holding the one-liner, the heading its rules sit under)
GROUPS = {
    "finding": ("findings/[0-9]*.md", "verdict", "**Teaches**"),
    "field type": ("findings/field_types/*.md", "verdict", "**Traps**"),
    "entity type": ("findings/entity_types/*.md", "verdict", "**Traps**"),
    "recipe": ("recipes/*.md", "intent", "## Notes"),
    "endpoint": ("endpoints/*.md", "verdict", "**Edge cases**"),
    "report": ("reports/*.md", "summary", None),
}


def family(endpoint):
    path = endpoint.partition(" ")[2]
    if path == "/" or path.startswith(("/auth/", "/internal_api/app_session_request")):
        return "Session"
    if path.startswith(SITE_PREFIXES):
        return "Site"
    if path.startswith("/schema"):
        return "Schema"
    if "_search" in path or "_summarize" in path or path.startswith("/hierarchy/"):
        return "Search"
    if "_upload" in path or path.startswith(("<links.", "/transcode/")):
        return "Media"
    if any(k in path for k in ATTENTION):
        return "Attention"
    if path.startswith("/webhook"):
        return "Webhooks"
    if path.startswith("/exports/"):
        return "Exports"
    if path.startswith("/entity"):
        return "Records"
    return "Other"


def endpoint_key(endpoint):
    method, _, path = endpoint.partition(" ")
    rank = METHODS.index(method) if method in METHODS else len(METHODS)
    return (FAMILIES.index(family(endpoint)), path, rank)


def section(text, heading):
    """The lines under one heading, down to the next heading of any kind."""
    if not heading:
        return ""
    out, on = [], False
    for ln in text.splitlines():
        if on and (ln.startswith(("## ", "# ")) or re.match(r"^\*\*[A-Z]", ln)):
            break
        if not on and ln.startswith(heading):
            on = True
            continue
        if on:
            out.append(ln)
    return "\n".join(out).strip()


def load_entries():
    entries = {}
    for group, (pattern, key, heading) in GROUPS.items():
        for f in sorted(CORPUS.glob(pattern)):
            text = f.read_text()
            m = re.match(r"---\n(.*?)\n---", text, re.S)
            if not m:                       # README.md in endpoints/ and reports/
                continue
            head = m.group(1)

            def lst(name, head=head):
                g = re.search(rf"{name}:\s*\[(.*?)\]", head, re.S)
                return [x.strip() for x in (g.group(1) if g else "").split(",") if x.strip()]

            def one(name, head=head):
                g = re.search(rf"^{name}:\s*(.+)$", head, re.M)
                return g.group(1).strip() if g else ""

            path = str(f.relative_to(ROOT))
            entries[path] = {
                "path": path, "group": group, "slug": f.stem,
                "tags": lst("tags"), "endpoints": lst("endpoints"),
                "phase": one("phase"), "coverage": one("coverage") or "measured",
                "endpoint": one("endpoint"), "headline": one(key),
                "rules": section(text, heading), "text": text,
            }
    return entries


def build_map(entries):
    """The map tier of issue #56: the protocol, every entry's name by group, the tag vocabulary."""
    by = lambda g: [e for e in entries.values() if e["group"] == g]
    lines = [
        "# Corpus map",
        "",
        "Read this, then one door. You hold the call: `doors/endpoints-<family>`. The entity type:",
        "`doors/entity_types`. The field's `data_type`: `doors/field_types`. The task:",
        "`doors/recipes`. A phase of a session: `doors/findings-<phase>`. Read the door's rules.",
        "Open an entry only when a rule needs its transcript, its sample or its table. A call that",
        "returned 2xx and did nothing: the door's **Silent on this call**.",
        "",
        "## Findings, by phase",
    ]
    for ph in PHASES:
        names = sorted(e["slug"] for e in by("finding") if e["phase"] == ph)
        if names:
            lines.append(f"- **{ph}** — {', '.join(names)}")
    lines += ["", "## Field types", ", ".join(sorted(e["slug"] for e in by("field type"))),
              "", "## Entity types", ", ".join(sorted(e["slug"] for e in by("entity type"))),
              "", "## Recipes", ", ".join(sorted(e["slug"] for e in by("recipe"))),
              "", "## Endpoints, by family"]
    for fam in FAMILIES:
        calls = sorted((e["endpoint"] for e in by("endpoint") if family(e["endpoint"]) == fam),
                       key=endpoint_key)
        if calls:
            lines.append(f"- **{fam}** — {', '.join('`%s`' % c for c in calls)}")
    lines += ["", "## Reports", ", ".join(sorted(e["slug"] for e in by("report")))]
    lines += ["", "## Tags", ", ".join(sorted({t for e in entries.values() for t in e["tags"]}))]
    return "\n".join(lines) + "\n"


def build_doors(entries):
    """The door tier of issue #56, built from the entries' own rule sections.

    An endpoints door carries every card in the family as a row, then one block per call: the
    card's own **Edge cases**, then the rule bullets of every entry whose `endpoints:` names that
    call, whatever group it lives in, then the verdicts of the `silent` entries naming it.
    """
    doors = {}
    cards = [e for e in entries.values() if e["group"] == "endpoint"]
    for fam in FAMILIES:
        fam_cards = sorted([c for c in cards if family(c["endpoint"]) == fam],
                           key=lambda c: endpoint_key(c["endpoint"]))
        if not fam_cards:
            continue
        header = [f"# Endpoints — {fam}", ""]
        for c in fam_cards:
            mark = "" if c["coverage"] == "measured" else f" **[{c['coverage']}]**"
            header.append(f"- `{c['endpoint']}`{mark} — {c['headline']}")
        blocks = [{"call": c["endpoint"], "card": c,
                   "joined": [e for e in entries.values()
                              if c["endpoint"] in e["endpoints"] and e["rules"]]}
                  for c in fam_cards]
        doors[f"endpoints-{fam}"] = {"kind": "endpoints", "header": "\n".join(header) + "\n",
                                     "blocks": blocks}

    def rule_door(name, title, rows):
        parts, members = [f"# {title}", ""], set()
        parts += [f"- **{e['slug']}** — {e['headline']}" for e in rows]
        for e in rows:
            if e["rules"]:
                parts += ["", f"## {e['slug']}", "", e["rules"]]
                members.add(e["path"])
        doors[name] = {"kind": "rules", "text": "\n".join(parts) + "\n", "members": members}

    for ph in PHASES:
        rows = sorted([e for e in entries.values()
                       if e["group"] == "finding" and e["phase"] == ph], key=lambda e: e["slug"])
        if rows:
            rule_door(f"findings-{ph}", f"Findings — {ph}", rows)
    for group, name in (("field type", "field_types"), ("entity type", "entity_types"),
                        ("recipe", "recipes")):
        rows = sorted([e for e in entries.values() if e["group"] == group],
                      key=lambda e: e["slug"])
        rule_door(name, name.replace("_", " ").title(), rows)
    return doors


def assemble(door, calls=None):
    """One door as it is read, and the entries whose rules are in it.

    `calls` selects the blocks of an endpoints door; None is the whole file. An entry joined onto
    several calls in the same door is written once and paid for once.
    """
    if door["kind"] != "endpoints":
        return door["text"], door["members"]
    parts, members, written = [door["header"]], set(), set()
    for b in door["blocks"]:
        if calls is not None and b["call"] not in calls:
            continue
        members.add(b["card"]["path"])
        parts += ["", f"## `{b['call']}`", ""]
        if b["card"]["rules"]:
            parts += [b["card"]["rules"], f"  ({b['card']['slug']})"]
        for e in b["joined"]:
            if e["path"] in written:
                continue
            written.add(e["path"])
            members.add(e["path"])
            parts += [e["rules"], f"  ({e['group'].replace(' ', '_')}/{e['slug']})"]
        silent = [e["headline"] for e in b["joined"] if "silent" in e["tags"]]
        if silent:
            parts += ["", "**Silent on this call**", ""] + [f"- {s}" for s in silent]
    return "\n".join(parts) + "\n", members


def read_doors(entries):
    """corpus/doors/ when it exists, else the same tiers built here."""
    if DOORS_DIR.is_dir():
        doors = {}
        for f in sorted(DOORS_DIR.glob("*.md")):
            text = f.read_text()
            doors[f.stem] = {"kind": "rules", "text": text,
                             "members": {e["path"] for e in entries.values() if e["rules"]
                                         and re.search(rf"\b{re.escape(e['slug'])}\b", text)}}
        return doors, (CORPUS / "INDEX.md").read_text(), "corpus/doors"
    return build_doors(entries), build_map(entries), "built"


def tag_forms(name):
    hyphen = re.sub(r"(?<!^)(?=[A-Z])", "-", name).lower().replace("_", "-")
    return {name.lower(), hyphen, hyphen.replace("-", "")}


def doors_named(plan, doors, opts):
    names = set() if opts["no_recipes"] else {"recipes"}
    for call in plan["calls"]:
        names.add(f"endpoints-{family(call)}")
    for ph in plan["phases"]:
        names.add(f"findings-{ph}")
    if plan["entity_types"]:
        names.add("entity_types")
    if plan["data_types"]:
        names.add("field_types")
    return sorted(n for n in names if n in doors)


def grep_matches(plan, entries):
    calls = set(plan["calls"])
    terms = {t for n in plan["entity_types"] + plan["data_types"] for t in tag_forms(n)}
    terms |= set(plan["phases"])
    return [e for e in entries.values()
            if e["rules"] and (calls & set(e["endpoints"]) or terms & set(e["tags"]))]


def tokens(n):
    return round(n / 4)


def score(task, entries, doors, map_text, opts):
    required, plan = task["required"], task["plan"]
    out = {}

    index = (CORPUS / "INDEX.md").read_text()
    chars = len(index) + sum(len(entries[p]["text"]) for p in required if p in entries)
    out["index"] = {
        "door": {p for p in required if re.search(rf"\b{re.escape(Path(p).stem)}\b", index)},
        "entry": {p for p in required if p in entries},
        "tokens": tokens(chars),
        "read": [f"corpus/INDEX.md, then {len(required)} entries in full"],
    }

    names = doors_named(plan, doors, opts)
    calls = set(plan["calls"]) if opts["per_call"] else None
    chars, opened = len(map_text), set()
    for n in names:
        text, members = assemble(doors[n], calls)
        chars += len(text)
        opened |= members
    out["doors"] = {"door": {p for p in required if p in opened}, "entry": set(),
                    "tokens": tokens(chars), "read": ["map"] + names}

    hits = grep_matches(plan, entries)
    out["grep"] = {"door": {p for p in required if p in {e["path"] for e in hits}}, "entry": set(),
                   "tokens": tokens(sum(len(e["rules"]) for e in hits)),
                   "read": [f"{len(hits)} entries, rules only"]}
    return out


def pct(hit, required):
    share = f" ({round(100 * len(hit) / len(required))}%)" if required else ""
    return f"{len(hit)}/{len(required)}{share}"


def sizes(doors, map_text, source):
    print(f"doors: {source}, map {tokens(len(map_text))} tokens, {len(map_text)} bytes\n")
    print("| door | entries | tokens | bytes | tokens if every join were written out |")
    print("|---|---|---|---|---|")
    for name in sorted(doors):
        door = doors[name]
        text, members = assemble(door)
        repeat = ""
        if door["kind"] == "endpoints":
            everything = len(door["header"]) + sum(len(e["rules"]) for b in door["blocks"]
                                                   for e in b["joined"])
            repeat = f"{tokens(everything):,}"
        print(f"| `{name}` | {len(members)} | {tokens(len(text)):,} | {len(text):,} | {repeat} |")


def main():
    opts = {"per_call": "--per-call" in sys.argv, "no_recipes": "--no-recipes" in sys.argv}
    entries = load_entries()
    doors, map_text, source = read_doors(entries)
    tasks = json.loads((HERE / "tasks.json").read_text())

    if "--doors" in sys.argv:
        sizes(doors, map_text, source)
        return

    for t in tasks:
        for p in t["required"]:
            if p not in entries:
                print(f"MISSING {t['id']}: {p}", file=sys.stderr)

    rows = [(t, score(t, entries, doors, map_text, opts)) for t in tasks]
    for t, s in rows:
        print(f"\n### {t['id']}\n\nFrom {t['source']}.\n")
        print("| strategy | door-tier recall | entry-tier recall | tokens | read |")
        print("|---|---|---|---|---|")
        for name in ("index", "doors", "grep"):
            r = s[name]
            print(f"| `{name}` | {pct(r['door'], t['required'])} | {pct(r['entry'], t['required'])}"
                  f" | {r['tokens']:,} | {', '.join(r['read'])} |")
        for name in ("doors", "grep"):
            missed = sorted(set(t["required"]) - s[name]["door"])
            if missed:
                print(f"\n`{name}` missed: {', '.join(missed)}")

    print("\n## Summary\n")
    print("| task | required | `index` tokens | `doors` recall | `doors` tokens | "
          "`grep` recall | `grep` tokens |")
    print("|---|---|---|---|---|---|---|")
    for t, s in rows:
        print(f"| {t['id']} | {len(t['required'])} | {s['index']['tokens']:,} | "
              f"{pct(s['doors']['door'], t['required'])} | {s['doors']['tokens']:,} | "
              f"{pct(s['grep']['door'], t['required'])} | {s['grep']['tokens']:,} |")
    n = len(rows)
    req = sum(len(t["required"]) for t, _ in rows)
    hit = lambda k: sum(len(s[k]["door"]) for _, s in rows)
    tok = lambda k: sum(s[k]["tokens"] for _, s in rows)
    print(f"| **all {n}** | {req} | {tok('index'):,} | "
          f"{hit('doors')}/{req} ({round(100 * hit('doors') / req)}%) | {tok('doors'):,} | "
          f"{hit('grep')}/{req} ({round(100 * hit('grep') / req)}%) | {tok('grep'):,} |")
    print(f"\nmean tokens per task: index {round(tok('index') / n):,}, "
          f"doors {round(tok('doors') / n):,}, grep {round(tok('grep') / n):,}")
    print(f"doors: {source}" + ", one call's block" * opts["per_call"]
          + ", no recipes door" * opts["no_recipes"])


if __name__ == "__main__":
    main()
