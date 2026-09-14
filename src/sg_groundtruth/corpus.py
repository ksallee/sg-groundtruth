"""The corpus as data: frontmatter, sections, and the rules each group states.

Three tiers, and this module is what separates them. The map names every entry. A door carries one
line per entry and that entry's rules, copied whole. The entry carries the transcript, the sample and
the tables that prove the rule. An agent that stops at a door has the rule; it opens the entry when it
needs the evidence.

The split already existed inside every entry, under a different label per group: `Teaches` on a
finding, `Traps` on a matrix card, `Notes` on a recipe, `Edge cases` on an endpoint card. Those four
names are spelled here and nowhere else, so `probes/index.py`, the MCP server and the site cannot
disagree about where a rule lives.

Standard library only: the corpus is markdown with frontmatter and reading it needs nothing else.
"""
import re
from collections import namedtuple
from pathlib import Path

# `glob` is the files under corpus/, `summary` the frontmatter key the one-liner is under, `rules` the
# section the group states its rules in, `prose` whether a paragraph and a table under that section are
# rules too.
#
# Four groups state a rule as a bullet, as a bolded sentence over the table that measures it, or as
# both, so the whole section is the rules there. A recipe is the one that does not: its `## Notes` is
# the commentary on a sample that is already in the entry, and copying all of it would put the entry
# in the door. Its bullets and its `###` headings are the rules; the paragraphs under them are the
# working.
Spec = namedtuple("Spec", "glob summary rules prose")

GROUPS = {
    "findings": Spec("findings/[0-9]*.md", "verdict", "**Teaches**", True),
    "field_types": Spec("findings/field_types/*.md", "verdict", "**Traps**", True),
    "entity_types": Spec("findings/entity_types/*.md", "verdict", "**Traps**", True),
    "recipes": Spec("recipes/[0-9]*.md", "intent", "## Notes", False),
    "endpoints": Spec("endpoints/*.md", "verdict", "**Edge cases**", True),
    "reports": Spec("reports/[0-9]*.md", "summary", None, False),
}

FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
LIST_KEYS = ("tags", "endpoints", "evidence")
# Every bold label any group uses as a section, so a section ends at the next one and not at the next
# bolded sentence. Two findings state their first rule as `**Boolean logic needs ...**` over the table
# that measures it, and a split on any bold line returned nothing for both.
LABELS = ("**Q**", "**Endpoint**", "**Docs claim**", "**Actual**", "**Teaches**",
          "**Data type**", "**Read**", "**Write**", "**Clear**", "**Filter**", "**Traps**",
          "**Type**", "**Identity**", "**Create**", "**Links**", "**Status**",
          "**Params**", "**Sample requests**", "**Response codes**", "**Edge cases**",
          "**Expected**", "**Reproduce**", "**Impact**", "**Proposed change**")


def frontmatter(text):
    """Every `key: value` above the first body line. List keys come back as lists."""
    m = FRONT_RE.match(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" not in line or line.startswith((" ", "\t", "-")):
            continue
        k, v = line.split(":", 1)
        k, v = k.strip(), v.strip()
        if k in LIST_KEYS:
            out[k] = [x.strip() for x in v.strip("[]").split(",") if x.strip()]
        else:
            out[k] = v
    return out


def section(text, label):
    """One section, label line included. A `##` heading runs to the next one; a bold label to the
    next bold label, which is how every card is written."""
    if not label:
        return ""
    if label.startswith("#"):
        depth = len(label) - len(label.lstrip("#"))
        pat = rf"^{re.escape(label)}\s*$.*?(?=^#{{1,{depth}}} |\Z)"
    else:
        nxt = "|".join(re.escape(x) for x in LABELS if x != label)
        pat = rf"^{re.escape(label)}.*?(?=^(?:{nxt})|\Z)"
    m = re.search(pat, text, re.M | re.S)
    return m.group(0) if m else ""


def blocks(text, prose=True):
    """The rules in a section, each copied whole.

    A bullet keeps its continuation lines, so a bullet ending in an indented table keeps the table, and
    a paragraph keeps the table it introduces. Never truncate one to its first sentence: CLAUDE.md
    records what two verdicts cost when they dropped the qualifier and read finished anyway.
    """
    out, lines = [], text.splitlines()
    i, first = 0, True
    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if first:                       # the label line itself, and whatever trails it
            first = False
            if ln.startswith(("**", "#")):
                i += 1
                continue
        if ln.startswith("#"):
            out.append(ln.lstrip("# ").strip())
            i += 1
            continue
        if ln[:2] in ("- ", "* "):
            buf, i = [ln], i + 1
            while i < len(lines):
                nxt = lines[i]
                if not nxt.strip():
                    if i + 1 < len(lines) and lines[i + 1].startswith(("  ", "\t")):
                        buf.append(nxt)
                        i += 1
                        continue
                    break
                if not nxt.startswith((" ", "\t")):
                    break
                buf.append(nxt)
                i += 1
            out.append("\n".join(buf).rstrip())
            continue
        if not prose:                   # a paragraph or a table nothing points at
            while i < len(lines) and lines[i].strip() and lines[i][:2] not in ("- ", "* "):
                i += 1
            continue
        buf = []
        while i < len(lines):
            run = []
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("#"):
                run.append(lines[i])
                i += 1
            buf += run
            # A paragraph and the table under it are one rule: the sentence states it and the table
            # is the enumeration. Keep them together across the blank line between.
            if (i + 1 < len(lines) and not lines[i].strip() and lines[i + 1].startswith("|")
                    and not run[-1].startswith("|")):
                buf.append("")
                i += 1
                continue
            break
        out.append("\n".join(buf).rstrip())
    return out


def rules(entry):
    """The rule blocks of one entry, in the order it states them."""
    spec = GROUPS[entry["group"]]
    return blocks(section(entry["text"], spec.rules), spec.prose)


def attribute(block, slug):
    """A joined rule names where it came from. A table is attributed on its own line, because a
    trailing cell is a cell."""
    lines = block.rstrip().splitlines()
    if not lines:
        return block
    if lines[-1].lstrip().startswith("|"):
        return f"{block}\n\n  from `{slug}`"
    return f"{block} ({slug})"


def load(corpus):
    """Every entry under corpus/, one dict each, grouped by the directory it sits in."""
    corpus = Path(corpus)
    out = []
    for group, spec in GROUPS.items():
        for f in sorted(corpus.glob(spec.glob)):
            if f.name == "README.md":
                continue
            text = f.read_text()
            fm = frontmatter(text)
            if not fm:
                continue
            e = dict(fm)
            e.update(
                group=group,
                slug=f.stem,
                path=str(f.relative_to(corpus)),
                text=text,
                summary=fm.get(spec.summary, "—"),
                tags=fm.get("tags", []),
                endpoints=fm.get("endpoints", []),
                coverage=fm.get("coverage", "measured"),
            )
            out.append(e)
    return out


def by_endpoint(entries):
    """Every entry naming a call, keyed by the call's canonical spelling.

    The join the doors are for. The rule an agent needed for `url` sat in a recipe while the agent
    read the finding, and no door led from one to the other (#9).
    """
    out = {}
    for e in entries:
        for ep in e["endpoints"]:
            out.setdefault(ep, []).append(e)
        if e["group"] == "endpoints" and e.get("endpoint"):
            out.setdefault(e["endpoint"], [])
    return out
