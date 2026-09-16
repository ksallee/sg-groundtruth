"""Regenerate corpus/INDEX.md and corpus/doors/ — the two cheap tiers, generated from the entries.

The map is the file an agent is told to read first, so it names every entry, groups them the four ways
a caller can already address them, and says which door to open. It is capped at 8 KiB by
`check_corpus.py`, because a map that grows with the corpus is a fixed cost every session pays before
asking anything.

A group door carries one line per entry and that entry's rules, copied whole. An endpoint door carries
the join: the verdict of every entry naming a call, whatever group it lives in, and the group door its
rules are on. The one retrieval miss a consumer filed was a rule sitting in a recipe while the agent
read the finding, and no door led from one to the other.

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

# The phases, the families and the shape of a door row are `sg_groundtruth.corpus`: the MCP server
# answers out of the same doors, and a row that differs between the two is a door an agent cannot
# follow.
PHASES, FAMILIES, METHODS = C.PHASES, C.FAMILIES, C.METHODS


def endpoint_key(endpoint):
    method, _, path = endpoint.partition(" ")
    rank = METHODS.index(method) if method in METHODS else len(METHODS)
    return (FAMILIES.index(C.family(endpoint)), path, rank)


# A door an agent has to page through is the cost the map was written to remove. A family over this is
# written one door per method, and a method still over it one door per call; the map says which.
DOOR_MAX = 32 * 1024


def slugify(endpoint):
    return re.sub(r"[^a-z0-9]+", "-", endpoint.lower()).strip("-")


def write(name, lines):
    (DOORS / name).write_text("\n".join(lines).rstrip() + "\n")
    return name


def entry_door(name, title, blurb, entries):
    """One door: a heading and a one-liner per entry, then that entry's own rules."""
    out = [f"# {title}", "", blurb, ""]
    for e in entries:
        out += [f"## {e['slug']}", "", f"{e['summary']}{C.mark(e)}", ""]
        if e.get("unmeasured"):
            out += [f"not measured: {e['unmeasured']}", ""]
        rules = C.rules(e)
        out += ["\n\n".join(rules) if rules else "No rule beyond the entry.", ""]
        out += [f"`corpus/{e['path']}`", ""]
    return write(name, out)


def call_section(card, behind, level="##"):
    """One call: what the card says it takes and answers, its own edge cases, and what measured it."""
    rows = C.joined(card, behind)
    out = ([f"{level} `{card['endpoint']}`{C.mark(card)}", ""] if level else []) + [card["summary"], ""]
    if card.get("unmeasured"):
        out += [f"not measured: {card['unmeasured']}", ""]
    rules = C.rules(card)
    out += ["\n\n".join(rules) if rules else "No edge case recorded on the card.", ""]
    out += C.measured_by(rows) + C.silent_on(card, rows)
    return out + [f"`corpus/{card['path']}`", ""]


HEAD = ("Every call in this family: what the card records, the edge cases that live on the call, and "
        "the verdict of every entry that measured it. Each of those lines names the door holding "
        "that entry's rules. The map is `corpus/INDEX.md`.")


def endpoint_doors(fam, cards, behind):
    """One door for the family, split when it grows past what an agent should read to answer one call.

    A caller holds the call. What bites on it is spread over a card, findings in four phases and a
    recipe, and reading one of those is how a caller ships an empty icon (#9). The seam is the method,
    which keeps the reads together and the writes together; a method group still over the cap splits
    again, one door per call.
    """
    def door(title, rows):
        out = [f"# {title}", "", HEAD, ""]
        for card in rows:
            out += call_section(card, behind)
        return out, len("\n".join(out))

    whole, size = door(f"Endpoints — {fam}", cards)
    if size <= DOOR_MAX or len(cards) == 1:
        return [write(f"endpoints-{fam.lower()}.md", whole)], ""

    names, per_call = [], False
    for method in METHODS:
        rows = [c for c in cards if c["endpoint"].split(" ", 1)[0] == method]
        if not rows:
            continue
        lines, size = door(f"Endpoints — {fam}, {method}", rows)
        if size <= DOOR_MAX or len(rows) == 1:
            names.append(write(f"endpoints-{fam.lower()}-{method.lower()}.md", lines))
            continue
        per_call = True
        for card in rows:
            out = [f"# `{card['endpoint']}`", "", HEAD, ""]
            out += call_section(card, behind, level="")
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
                f"findings-{phase}.md", f"Findings — {phase}: {blurb}",
                "How the API behaves in this part of a session. Each rule is the entry's own "
                "**Teaches**, copied whole.", rows))
    stray = [e for e in findings if e["phase"] not in PHASES]
    if stray:
        written.add(entry_door(
            "unphased.md", "Findings — unphased",
            "A finding whose `phase:` names no part of a session. Fix the key on the entry.", stray))

    written.add(entry_door(
        "field_types.md", "Field types",
        "One per `data_type`: how it reads, writes, clears and filters. Each rule is the card's own "
        "**Traps**, copied whole. The matrices behind them are in the cards.", types))
    written.add(entry_door(
        "entity_types.md", "Entity types",
        "One per standard entity type: what it is, how it is identified, created and linked. Each "
        "rule is the card's own **Traps**, copied whole.", entities))
    written.add(entry_door(
        "recipes.md", "Recipes",
        "A verified call and its real response, addressed by the task. The heading is the intent and "
        "the rules are the recipe's own **Notes**. The code is in the entry.", recipes))

    split = {}
    for fam in FAMILIES:
        rows = [e for e in cards if C.family(e["endpoint"]) == fam]
        if rows:
            names, seam = endpoint_doors(fam, rows, behind)
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

    Capped at 8 KiB by `check_corpus.py`. Every session pays for this file before it asks
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
        rows = [e for e in cards if C.family(e["endpoint"]) == fam]
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
