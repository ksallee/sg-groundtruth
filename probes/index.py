"""Regenerate corpus/INDEX.md — the cheap layer an agent reads before opening anything.

Four keys, because an agent about to make a call already holds four things: the call, the entity
type, the field's data type, and the task. Each is a way in.
"""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "corpus"
FINDINGS = CORPUS / "findings"
RECIPES = CORPUS / "recipes"
ENDPOINTS = CORPUS / "endpoints"

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


def parse(f, summary_key):
    m = re.match(r"---\n(.*?)\n---", f.read_text(), re.S)
    if not m:
        return None
    head = m.group(1)
    def lst(key):
        g = re.search(rf"{key}:\s*\[(.*?)\]", head)
        return [x.strip() for x in (g.group(1) if g else "").split(",") if x.strip()]
    one = lambda key: (re.search(rf"^{key}:\s*(.+)$", head, re.M) or [None, ""])[1].strip()
    summary = re.search(rf"{summary_key}:\s*(.+)", head)
    return {
        "slug": f.stem,
        "tags": lst("tags"),
        "endpoints": lst("endpoints"),
        "phase": one("phase"),
        "summary": summary.group(1).strip() if summary else "—",
    }


def collect(d, key, pattern="[0-9]*.md"):
    return sorted(filter(None, (parse(f, key) for f in d.glob(pattern))), key=lambda e: e["slug"])


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
    if path == "/" or path.startswith("/auth/"):
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


def endpoint_cards():
    """One card per call, in ENDPOINT_ORDER, then anything the order does not name."""
    cards = []
    for f in sorted(ENDPOINTS.glob("*.md")):
        if f.name == "README.md":
            continue
        e = parse(f, "verdict")
        m = re.search(r"^endpoint:\s*(\S.*?)\s*$", f.read_text(), re.M)
        if not e or not m:
            continue
        e["endpoint"] = m.group(1)
        cards.append(e)
    return sorted(cards, key=lambda e: endpoint_key(e["endpoint"]))


def line(e):
    return f"- **{e['slug']}** — {e['summary']}  \n  `{' '.join(e['tags'])}`"


def main():
    findings = collect(FINDINGS, "verdict")
    recipes = collect(RECIPES, "intent")
    # The two matrices are addressed by type, not by when they were probed, so they are named.
    types = collect(FINDINGS / "field_types", "verdict", "*.md")
    entities = collect(FINDINGS / "entity_types", "verdict", "*.md")
    endpoints = endpoint_cards()
    everything = [("finding", findings), ("recipe", recipes),
                  ("field type", types), ("entity type", entities),
                  ("endpoint", endpoints)]

    by_tag = defaultdict(list)
    by_endpoint = defaultdict(list)
    for kind, items in everything:
        for e in items:
            for t in e["tags"]:
                by_tag[t].append(f"{e['slug']} ({kind})")
            for p in e["endpoints"]:
                by_endpoint[p].append(f"{e['slug']} ({kind})")

    out = [
        "# Corpus index", "",
        "Read this first. Open an entry only when its one-liner does not already answer the "
        "question.", "",
        "Four ways in, one per thing you already know before you call:", "",
        "| you know | look under |",
        "|---|---|",
        "| the call you are about to make | **Endpoints** |",
        "| the entity type you are writing | **Entity types** |",
        "| the field's `data_type` | **Field types** |",
        "| the task | **Recipes** |", "",
        "**Findings** are how the API behaves, grouped by the phase of a session they bite in. "
        "**Recipes** are a verified call and its real response.", "",
        "`silent` is the tag to follow when a call returned 2xx and did nothing.", "",
        "Every measurement here was taken against **`/api/v1`**. The site's own OpenAPI document "
        "advertises `/api/v1.1` instead; the two are the same API, differing only in `api_version` "
        "in the root document and the prefix each echoes in its own `links` (`051_api_version`).",
        "",
        "## Findings", "",
    ]
    for phase, blurb in PHASES.items():
        rows = [e for e in findings if e["phase"] == phase]
        if rows:
            out += [f"### {phase} — {blurb}", ""] + [line(e) for e in rows] + [""]
    stray = [e for e in findings if e["phase"] not in PHASES]
    if stray:
        out += ["### unphased", ""] + [line(e) for e in stray] + [""]

    out += ["## Field types", "",
            "One per `data_type`: how it reads, writes, clears and filters. `field_types/<type>`.", ""]
    out += [line(e) for e in types] or ["- none yet"]
    out += ["", "## Entity types", "",
            "One per standard entity type: what it is, how it is identified, created and linked. "
            "`entity_types/<Type>`.", ""]
    out += [line(e) for e in entities] or ["- none yet"]
    out += ["", "## Recipes", ""]
    out += [line(e) for e in recipes] or ["- none yet"]

    eps = endpoints
    known = {e["endpoint"] for e in eps}
    covered = sum(1 for e in eps if by_endpoint.get(e["endpoint"]))
    out += ["", "## Endpoints", "",
            "One card per call: what it takes, what it answers, a real response and the edge cases "
            "that live on the call. `endpoints/<slug>`.", "",
            f"{covered} of {len(eps)} have a finding or recipe behind them as well. A card with none "
            "is documented and not yet probed, which is the queue.", ""]
    for fam in FAMILIES:
        rows = [e for e in eps if family(e["endpoint"]) == fam]
        if not rows:
            continue
        out += [f"### {fam}", ""]
        for e in rows:
            entries = by_endpoint.get(e["endpoint"])
            out.append(f"- **`{e['endpoint']}`** — {e['summary']}  \n  `{' '.join(e['tags'])}`"
                       + (f"  \n  also: {', '.join(entries)}" if entries else "  \n  *no finding yet*"))
        out.append("")
    unknown = sorted(set(by_endpoint) - known)
    if unknown:
        out += ["", "Named by an entry with no card:", ""]
        out += [f"- `{p}` — {', '.join(by_endpoint[p])}" for p in unknown]

    out += ["", "## By tag", ""]
    out += [f"- **{t}** — {', '.join(by_tag[t])}" for t in sorted(by_tag)]

    (CORPUS / "INDEX.md").write_text("\n".join(out) + "\n")
    print(f"indexed {len(findings)} findings, {len(types)} field types, {len(entities)} entity "
          f"types, {len(recipes)} recipes, {len(eps)} endpoints, {len(by_tag)} tags, "
          f"{covered}/{len(eps)} endpoints with a finding behind them")


if __name__ == "__main__":
    main()
