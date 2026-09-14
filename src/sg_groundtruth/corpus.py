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
# that measures it, and a split on any bold line returned nothing for both. A new section label goes
# here, or the section above it swallows it.
LABELS = ("**Q**", "**Endpoint**", "**Docs claim**", "**Actual**", "**Teaches**",
          "**Data type**", "**Read**", "**Write**", "**Clear**", "**Filter**", "**Traps**",
          "**Type**", "**Identity**", "**Create**", "**Links**", "**Status**",
          "**Python equivalent**",
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

    A bullet keeps its continuation lines, so a bullet ending in an indented table keeps the table; a
    paragraph keeps the table it introduces and the sample under it. Never truncate one to its first
    sentence: CLAUDE.md records what two verdicts cost when they dropped the qualifier and read
    finished anyway.
    """
    out, lines = [], text.splitlines()
    i, first = 0, True

    def past_fence(j):
        """The line after the fence opening at j. A `#` inside one is a comment, not a heading."""
        j += 1
        while j < len(lines) and not lines[j].startswith("```"):
            j += 1
        return j + 1

    while i < len(lines):
        ln = lines[i]
        if not ln.strip():
            i += 1
            continue
        if first:                       # the label line itself
            first = False
            if ln.startswith(("**", "#")):
                i += 1
                continue
        if ln.startswith("```"):
            end = past_fence(i)
            if prose:
                block = "\n".join(lines[i:end]).rstrip()
                if out:                 # the sample is evidence for the rule above it
                    out[-1] += "\n\n" + block
                else:
                    out.append(block)
            i = end
            continue
        if ln.startswith("#"):
            out.append(ln.rstrip())     # a heading is a rule where the prose under it is the working
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
            while (i < len(lines) and lines[i].strip() and not lines[i].startswith("```")
                   and lines[i][:2] not in ("- ", "* ")):
                i += 1
            continue
        buf = []
        while i < len(lines):
            run = []
            while (i < len(lines) and lines[i].strip()
                   and not lines[i].startswith(("#", "```"))):
                run.append(lines[i])
                i += 1
            buf += run
            # A paragraph and the table under it are one rule: the sentence states it and the table is
            # the enumeration. Keep them together across the blank line between.
            if (run and i + 1 < len(lines) and not lines[i].strip()
                    and lines[i + 1].startswith("|") and not run[-1].startswith("|")):
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


# The doors, and what a row on one says.
#
# `probes/index.py` writes them and the MCP server answers out of them, so the phase names, the
# families and the shape of a row are spelled here once. A row that differs between the two is a door
# an agent cannot follow: the name it read on one surface has to open on the other.

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

# Endpoints are grouped by the resource they act on, in the order a client meets them, and the family
# is derived from the path rather than declared on the card. A hand-kept list was fine at 23 endpoints
# and wrong at 54: a new card fell off the end of it silently. `site/src/lib/content/corpus.js` holds
# the same rules.
FAMILIES = ["Session", "Site", "Schema", "Records", "Search", "Media", "Attention",
            "Webhooks", "Exports", "Other"]
METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE"]

SITE_PREFIXES = ("/spec.", "/preferences", "/license_info", "/schedule/", "/subscription_seat/")
ATTENTION = ("follow", "activity_stream", "thread_contents")

# Findings first and in phase order, then the matrices, the recipes and the reports: the order a
# session meets them, which is the order the rules under a call are worth reading in.
_RANK = {g: i for i, g in enumerate(
    ["findings", "field_types", "entity_types", "recipes", "reports"])}


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


def entry_order(e):
    phases = list(PHASES)
    return (_RANK.get(e["group"], 9),
            phases.index(e["phase"]) if e.get("phase") in phases else 9, e["slug"])


def mark(e):
    return "" if e.get("coverage", "measured") == "measured" else f" **[{e['coverage']}]**"


def door_of(e):
    """The door holding this entry's rules."""
    if e["group"] == "findings":
        return f"doors/findings-{e.get('phase')}" if e.get("phase") in PHASES else "doors/unphased"
    return f"doors/{e['group']}"


def door_row(e):
    """One entry as a door writes it: the verdict, and where its rules are."""
    return f"- `{e['slug']}` ({e['group']}) — {e['summary']}  \n  rules: `{door_of(e)}`"


def joined(card, behind, order=entry_order):
    """Every entry naming this call, the card itself excluded, in reading order."""
    rows = (e for e in behind.get(card["endpoint"], []) if e["slug"] != card["slug"])
    return sorted(rows, key=order)


def measured_by(rows):
    """The verdicts, not the rules.

    Copying the bullets of every entry naming a call put 18,000 tokens on `POST /entity/<type>/_search`
    alone and made the door dearer than the index it replaced (benchmark, #58). A verdict says whether
    the entry bears on the call; the row names the door that holds its rules.
    """
    if not rows:
        return []
    return ["**Measured by**", ""] + [door_row(e) for e in rows] + [""]


def silent_on(card, rows):
    """A 2xx that did not carry out the request, on this call."""
    silent = [e for e in [card] + rows if "silent" in e["tags"]]
    if not silent:
        return []
    return (["**Silent on this call**", ""]
            + [f"- `{e['slug']}` — {e['summary']}" for e in silent] + [""])
