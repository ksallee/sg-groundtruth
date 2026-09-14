"""Regenerate corpus/INDEX.md and corpus/doors/ — the two cheap tiers, generated from the entries.

The map is the file an agent is told to read first, so it names every entry, groups them the four ways
a caller can already address them, and says which door to open. It is capped at 8,000 bytes by
`check_corpus.py`, because a map that grows with the corpus is a fixed cost every session pays before
asking anything.

A door carries one line per entry and that entry's rules, copied whole. The endpoint doors also carry
the join: the rules of every entry naming a call, whatever group it lives in. The one retrieval miss a
consumer filed was a rule sitting in a recipe while the agent read the finding, and no door led from
one to the other.

The section each group states its rules in is spelled in `sg_groundtruth.corpus`, not here.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from sg_groundtruth import corpus as C  # noqa: E402

CORPUS = ROOT / "corpus"
DOORS = CORPUS / "doors"

# The order a client meets them, so the listing itself teaches the shape of a session.
PHASES = {
    "auth": "getting a token, and what it is",
    "protocol": "headers, and what a status code is worth",
    "schema": "what the site has, and adding to it",
    "read": "getting rows back",
    "filter": "selecting the rows you want",
    "write": "creating and updating",
    "upload": "getting bytes in and out",
    "observe": "what changed",
    "render": "showing it to a person",
}

# Endpoints are grouped by the resource they act on, in the order a client meets
# them, and the family is derived from the path rather than declared on the card.
# A hand-kept list was fine at 23 endpoints and wrong at 54: a new card fell off
# the end of it silently. `site/src/lib/content/corpus.js` holds the same rules.
FAMILIES = ["Session", "Site", "Schema", "Records", "Search", "Media", "Attention",
            "Webhooks", "Exports", "Other"]
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

SITE_PREFIXES = ("/spec.", "/preferences", "/license_info", "/schedule/", "/subscription_seat/")
ATTENTION = ("follow", "activity_stream", "thread_contents")


def family(endpoint):
    """The resource an endpoint acts on. Order matters: a path can match twice."""
    method, _, path = endpoint.partition(" ")
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


def mark(e):
    return "" if e["coverage"] == "measured" else f" **[{e['coverage']}]**"


# A door an agent has to page through is the cost the map was written to remove. A family whose join
# passes this is written one door per call instead; the map says so and names the calls.
DOOR_MAX = 32 * 1024


def slugify(endpoint):
    return re.sub(r"[^a-z0-9]+", "-", endpoint.lower()).strip("-")


def write(name, lines):
    (DOORS / name).write_text("\n".join(lines).rstrip() + "\n")
    return name


def entry_door(title, blurb, entries, heading=lambda e: e["slug"], name=None):
    """One door: a heading and a one-liner per entry, then that entry's own rules."""
    out = [f"# {title}", "", blurb, ""]
    for e in entries:
        out += [f"## {heading(e)}", "", f"{e['summary']}{mark(e)}", ""]
        if e.get("unmeasured"):
            out += [f"not measured: {e['unmeasured']}", ""]
        rules = C.rules(e)
        out += ["\n\n".join(rules) if rules else "No rule beyond the entry.", ""]
        out += [f"`corpus/{e['path']}`", ""]
    return write(name, out)


# The door that holds an entry's rules, so a line on an endpoint door says where to read on.
def rules_door(e):
    if e["group"] == "findings":
        return f"doors/findings-{e['phase']}" if e["phase"] in PHASES else "doors/unphased"
    return f"doors/{e['group']}"


def call_section(card, behind, order, level="##"):
    """One call: what the card says it takes and answers, its own edge cases, and what measured it.

    The verdicts, not the rules. Copying the bullets of every entry naming a call put 18,000 tokens
    on `POST /entity/<type>/_search` alone and made the door dearer than the index it replaced
    (benchmark, #58). A verdict says whether the entry bears on the call; the line names the door
    that holds its rules.
    """
    ep = card["endpoint"]
    rows = sorted((e for e in behind.get(ep, []) if e["slug"] != card["slug"]), key=order)
    out = ([f"{level} `{ep}`{mark(card)}", ""] if level else []) + [card["summary"], ""]
    if card.get("unmeasured"):
        out += [f"not measured: {card['unmeasured']}", ""]
    rules = C.rules(card)
    out += ["\n\n".join(rules) if rules else "No edge case recorded on the card.", ""]
    if rows:
        out += ["**Measured by**", ""]
        out += [f"- `{e['slug']}` ({e['group']}) — {e['summary']}  \n  rules: `{rules_door(e)}`"
                for e in rows] + [""]
    silent = [e for e in [card] + rows if "silent" in e["tags"]]
    if silent:
        out += ["**Silent on this call**", ""]
        out += [f"- `{e['slug']}` — {e['summary']}" for e in silent] + [""]
    return out + [f"`corpus/{card['path']}`", ""]


HEAD = ("Every call in this family: what the card records, the edge cases that live on the call, and "
        "the verdict of every entry that measured it. Each of those lines names the door holding "
        "that entry's rules. The map is `corpus/INDEX.md`.")


def endpoint_doors(fam, cards, behind, order):
    """One door for the family, split when it grows past what an agent should read to answer one call.

    A caller holds the call. What bites on it is spread over a card, findings in four phases and a
    recipe, and reading one of those is how a caller ships an empty icon (#9). The seam is the method,
    which keeps the reads together and the writes together; a method group still over the cap splits
    again, one door per call.
    """
    def door(name, title, rows):
        out = [f"# {title}", "", HEAD, ""]
        for card in rows:
            out += call_section(card, behind, order)
        return out, len("\n".join(out))

    whole, size = door(fam, f"Endpoints — {fam}", cards)
    if size <= DOOR_MAX or len(cards) == 1:
        return [write(f"endpoints-{fam.lower()}.md", whole)], ""

    names, per_call = [], False
    for method in METHODS:
        rows = [c for c in cards if c["endpoint"].split(" ", 1)[0] == method]
        if not rows:
            continue
        lines, size = door(method, f"Endpoints — {fam}, {method}", rows)
        if size <= DOOR_MAX or len(rows) == 1:
            names.append(write(f"endpoints-{fam.lower()}-{method.lower()}.md", lines))
            continue
        per_call = True
        for card in rows:
            out = [f"# `{card['endpoint']}`", "", HEAD, ""]
            out += call_section(card, behind, order, level="")
            names.append(write(f"endpoints-{slugify(card['endpoint'])}.md", out))
    return names, ("call" if per_call else "method")


def main():
    entries = C.load(CORPUS)
    by = defaultdict(list)
    for e in entries:
        by[e["group"]].append(e)
    findings, recipes = by["findings"], by["recipes"]
    types, entities, reports = by["field_types"], by["entity_types"], by["reports"]
    cards = sorted(by["endpoints"], key=lambda e: endpoint_key(e["endpoint"]))

    behind = C.by_endpoint(entries)
    by_tag = defaultdict(list)
    for e in entries:
        for t in e["tags"]:
            by_tag[t].append(f"{e['slug']} ({e['group']})")

    DOORS.mkdir(exist_ok=True)
    written = set()

    for phase, blurb in PHASES.items():
        rows = [e for e in findings if e["phase"] == phase]
        if rows:
            written.add(entry_door(
                f"Findings — {phase}: {blurb}",
                "How the API behaves in this part of a session. Each rule is the entry's own "
                "**Teaches**, copied whole.",
                rows, name=f"findings-{phase}.md"))
    stray = [e for e in findings if e["phase"] not in PHASES]
    if stray:
        written.add(entry_door("Findings — unphased", "A finding whose `phase:` names no part of a "
                              "session. Fix the key on the entry.", stray, name="unphased.md"))

    written.add(entry_door(
        "Field types",
        "One per `data_type`: how it reads, writes, clears and filters. Each rule is the card's own "
        "**Traps**, copied whole. The matrices behind them are in the cards.",
        types, name="field_types.md"))
    written.add(entry_door(
        "Entity types",
        "One per standard entity type: what it is, how it is identified, created and linked. Each "
        "rule is the card's own **Traps**, copied whole.",
        entities, name="entity_types.md"))
    written.add(entry_door(
        "Recipes",
        "A verified call and its real response, addressed by the task. The heading is the intent and "
        "the rules are the recipe's own **Notes**. The code is in the entry.",
        recipes, name="recipes.md"))

    # Findings first and in phase order, then the matrices, the recipes and the reports: the order a
    # session meets them, which is the order the rules under a call are worth reading in.
    rank = {g: i for i, g in enumerate(
        ["findings", "field_types", "entity_types", "recipes", "reports"])}
    phases = list(PHASES)

    def order(e):
        return (rank.get(e["group"], 9),
                phases.index(e["phase"]) if e.get("phase") in phases else 9, e["slug"])

    split = {}
    for fam in FAMILIES:
        rows = [e for e in cards if family(e["endpoint"]) == fam]
        if rows:
            names, seam = endpoint_doors(fam, rows, behind, order)
            written.update(names)
            if seam:
                split[fam] = seam

    out = ["# Reports", "",
           "Behaviour that should change, addressed to the team that owns the API. Each names the "
           "entries that measured it, states what was expected, and proposes the fix. It is also the "
           "re-probe queue: each one dates the last time the behaviour was seen.", ""]
    for e in reports:
        chased = f", {e['ticket']}" if e.get("ticket") else ""
        out.append(f"- **{e['slug']}** [{e['kind']}, {e['status']}{chased}] — {e['summary']}  \n"
                   f"  evidence: {', '.join(e['evidence'])}, confirmed {e['confirmed']}  \n"
                   f"  `corpus/{e['path']}`")
    written.add(write("reports.md", out or ["- none yet"]))

    out = ["# By tag", "",
           "Every entry carrying each tag. A tag selects or it is noise: no subject tag is on more "
           "than 25 entries, and `silent`, `destructive` and `trap` name what kind of failure an "
           "entry is rather than what it is about, so they span.", ""]
    out += [f"- **{t}** — {', '.join(by_tag[t])}" for t in sorted(by_tag)]
    written.add(write("tags.md", out))

    for f in DOORS.glob("*.md"):
        if f.name not in written:
            f.unlink()

    index(findings, types, entities, recipes, cards, reports, by_tag, behind, split)
    sizes = {f.name: f.stat().st_size for f in sorted(DOORS.glob("*.md"))}
    print(f"indexed {len(findings)} findings, {len(types)} field types, {len(entities)} entity "
          f"types, {len(recipes)} recipes, {len(cards)} endpoints, {len(reports)} reports, "
          f"{len(by_tag)} tags")
    print(f"map {(CORPUS / 'INDEX.md').stat().st_size} bytes, {len(sizes)} doors, "
          f"largest {max(sizes.values())} bytes ({max(sizes, key=sizes.get)})")


def index(findings, types, entities, recipes, cards, reports, by_tag, behind, split):
    """The map: every entry by name, and the door to open for each way in.

    Capped at 8,000 bytes by `check_corpus.py`. Every session pays for this file before it asks
    anything, so a line here has to earn its place against the door it points at.
    """
    covered = sum(1 for e in cards if behind.get(e["endpoint"]))
    names = lambda rows: ", ".join(e["slug"] for e in rows)
    out = [
        "# Corpus index", "",
        "Read this first. It names every entry and says which door to open. A group door carries one "
        "line per entry and that entry's rules, copied whole.", "",
        "| you know | open |",
        "|---|---|",
        "| the call | its family under **Endpoints** |",
        "| the entity type | `doors/entity_types.md` |",
        "| the `data_type` | `doors/field_types.md` |",
        "| the task | `doors/recipes.md` |",
        "| the phase of a session | `doors/findings-<phase>.md` |", "",
        "An endpoint door holds the edge cases that live on the call and the verdict of every entry "
        "that measured it, each naming the group door its rules are on. Read the verdicts, open that "
        "door for the rules, the entry for a transcript, a sample or a table. A 2xx that did nothing "
        "is under **Silent on this call**. Measured against `/api/v1` (`051_api_version`).", "",
        "## Findings", "",
    ]
    for phase in list(PHASES) + ["unphased"]:
        rows = [e for e in findings
                if e["phase"] == phase or (phase == "unphased" and e["phase"] not in PHASES)]
        if rows:
            out += [f"**{phase}** {names(rows)}", ""]

    out += ["## Field types", "", names(types) or "none yet", "",
            "## Entity types", "", names(entities) or "none yet", "",
            "## Recipes", ""]
    out += [f"- {e['slug']} — {e['summary']}" for e in recipes] or ["none yet"]

    out += ["", "## Endpoints", "",
            f"One card per call, {covered} of {len(cards)} with an entry behind them; a card with "
            "none is the queue. A family's door is `doors/endpoints-<family>.md`, in lower case.",
            ""]
    for fam in FAMILIES:
        rows = [e for e in cards if family(e["endpoint"]) == fam]
        if not rows:
            continue
        seam = {"method": f", one door per method: `doors/endpoints-{fam.lower()}-<method>.md`",
                "call": ", one door per call: `doors/endpoints-<call>.md`, the call in lower case "
                        "with `-` for every other run"}.get(split.get(fam), "")
        out += [f"**{fam}**{seam}", "", "```"] + [e["endpoint"] for e in rows] + ["```", ""]
    unknown = sorted(set(behind) - {e["endpoint"] for e in cards})
    if unknown:
        out += ["Named by an entry with no card: " + ", ".join(f"`{p}`" for p in unknown), ""]

    out += ["## Reports", "", names(reports) or "none yet", "",
            "## Tags", "", "`doors/tags.md` holds the entries under each.", "",
            " ".join(sorted(by_tag))]
    (CORPUS / "INDEX.md").write_text("\n".join(out) + "\n")


if __name__ == "__main__":
    main()
