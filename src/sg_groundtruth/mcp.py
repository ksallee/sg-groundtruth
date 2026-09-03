"""The corpus over MCP: stdio, JSON-RPC 2.0, standard library only.

An agent already holding a Flow Production Tracking MCP server can call the API. This one answers what
the API does, which is a different question and the one the other server cannot answer. The two are
meant to be mounted together.

No dependency. The corpus is markdown with frontmatter, and reading it needs nothing that is not in the
standard library, so mounting this costs an operator no install beyond the clone.

Only `scope: api` entries are served. A `site` or `project` measurement is true of one installation, and
an agent that cannot tell the difference will state one as general behaviour. `--overlay` opts in to the
local ones, which is the same decision the reading level makes on the site.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PROTOCOL = "2025-06-18"
SUPPORTED = {"2025-06-18", "2025-03-26", "2024-11-05"}

FRONT_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)
# Both quote forms the cards use, because three types quote the raw JSON body with the quotes still
# escaped. See the site's filter page for why this pattern is one and not two.
RELATIONS_RE = re.compile(r"Valid relations:\s*\[(.*?)\]", re.S)
TOKEN_RE = re.compile(r'\\?"([a-z_]+)\\?"')


def _front(text):
    m = FRONT_RE.match(text)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line and not line.startswith((" ", "\t", "-")):
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip()
    return out


def _load(overlay):
    """Every entry, keyed by slug. Later roots do not overwrite earlier ones: a slug that exists at two
    levels is two entries, and the level is part of what an answer has to carry."""
    roots = [("api", ROOT / "corpus")]
    if overlay:
        local = ROOT / "corpus.local"
        if (local / "site").is_dir():
            roots.append(("site", local / "site"))
        pdir = local / "projects"
        if pdir.is_dir():
            roots += [("project", d) for d in sorted(pdir.iterdir()) if d.is_dir()]

    entries = []
    for level, root in roots:
        for f in sorted(root.rglob("*.md")):
            if f.name == "INDEX.md":
                continue
            text = f.read_text()
            fm = _front(text)
            if not fm.get("verdict"):
                continue
            if level == "api" and fm.get("scope") != "api":
                continue  # a site or project measurement never ships as general behaviour
            entries.append(
                {
                    "slug": f.stem,
                    "group": f.parent.name if f.parent.name != root.name else f.parent.name,
                    "level": level,
                    "scope": fm.get("scope", ""),
                    "project": fm.get("project", ""),
                    "measured": fm.get("measured", ""),
                    "verdict": fm["verdict"],
                    "tags": [t.strip() for t in fm.get("tags", "").strip("[]").split(",") if t.strip()],
                    "title": fm.get("title", ""),
                    "path": str(f.relative_to(ROOT)),
                    "body": text,
                }
            )
    return entries


def _line(e):
    where = "" if e["level"] == "api" else f"  [{e['project'] or e['level']}]"
    return f"- {e['slug']} ({e['group']}) — {e['verdict']}{where}\n  tags: {' '.join(e['tags'])}"


TOOLS = [
    {
        "name": "corpus_index",
        "description": (
            "Every entry's slug, one-line verdict and tags. Read this before anything else and open an "
            "entry only when its one-liner falls short. Optionally filter by tag or group."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Only entries carrying this tag."},
                "group": {
                    "type": "string",
                    "description": "findings, field_types, entity_types or recipes.",
                },
            },
        },
    },
    {
        "name": "corpus_entry",
        "description": "One entry in full, by slug. The body is the measured evidence, verbatim.",
        "inputSchema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "corpus_search",
        "description": (
            "Entries whose verdict, slug, tags or body mention every word given. Returns one-liners, "
            "not bodies."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "filter_operators",
        "description": (
            "The filter relations the API accepts for a data type, as the API itself printed them when "
            "it rejected an unknown one. An operator outside the list is HTTP 400. A type that accepts "
            "none returns an empty list, which is an answer and not a gap. Omit data_type for all of "
            "them, which is the call to make before building any filter UI."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "data_type": {"type": "string", "description": "e.g. text, date, multi_entity."}
            },
        },
    },
]


def _operators(entries, data_type):
    cards = {e["slug"]: e for e in entries if e["group"] == "field_types"}
    want = [data_type] if data_type else sorted(cards)
    out = {}
    for name in want:
        card = cards.get(name)
        if card is None:
            out[name] = None
            continue
        m = RELATIONS_RE.search(card["body"])
        if m:
            out[name] = sorted(set(TOKEN_RE.findall(m.group(1))))
        elif "cannot be used in a filter" in card["body"]:
            out[name] = []
        else:
            out[name] = None
    return out


def _call(name, args, entries):
    if name == "corpus_index":
        rows = entries
        if args.get("tag"):
            rows = [e for e in rows if args["tag"] in e["tags"]]
        if args.get("group"):
            rows = [e for e in rows if e["group"] == args["group"]]
        if not rows:
            return "No entry matches. Call corpus_index with no arguments to see the vocabulary."
        return f"{len(rows)} entries.\n\n" + "\n".join(_line(e) for e in rows)

    if name == "corpus_entry":
        for e in entries:
            if e["slug"] == args.get("slug"):
                return f"{e['path']}  scope: {e['scope']}  measured: {e['measured']}\n\n{e['body']}"
        near = [e["slug"] for e in entries if args.get("slug", "") in e["slug"]]
        return f"No entry {args.get('slug')!r}." + (f" Did you mean: {', '.join(near)}" if near else "")

    if name == "corpus_search":
        words = args.get("query", "").lower().split()
        if not words:
            return "Give a query."
        hits = [
            e
            for e in entries
            if all(w in (e["slug"] + " " + e["verdict"] + " " + " ".join(e["tags"]) + " " + e["body"]).lower() for w in words)
        ]
        if not hits:
            return f"Nothing matches {args['query']!r}."
        return f"{len(hits)} entries.\n\n" + "\n".join(_line(e) for e in hits)

    if name == "filter_operators":
        got = _operators(entries, args.get("data_type"))
        lines = []
        for k, v in got.items():
            if v is None:
                lines.append(f"{k}: not recorded")
            elif not v:
                lines.append(f"{k}: no relation accepted; the API refuses to filter this type")
            else:
                lines.append(f"{k}: {', '.join(v)}")
        return "\n".join(lines) + "\n\nValue shapes per operator are in each field_types entry."

    return f"No tool named {name!r}."


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    entries = _load(overlay="--overlay" in argv)

    def send(obj):
        sys.stdout.write(json.dumps(obj) + "\n")
        sys.stdout.flush()

    for raw in sys.stdin:
        raw = raw.strip()
        if not raw:
            continue
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            continue

        method, mid = msg.get("method"), msg.get("id")
        if mid is None:
            continue  # a notification; nothing to answer

        if method == "initialize":
            asked = (msg.get("params") or {}).get("protocolVersion")
            send({
                "jsonrpc": "2.0",
                "id": mid,
                "result": {
                    "protocolVersion": asked if asked in SUPPORTED else PROTOCOL,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "sg-groundtruth", "version": "0.1.0"},
                },
            })
        elif method == "tools/list":
            send({"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}})
        elif method == "tools/call":
            p = msg.get("params") or {}
            text = _call(p.get("name", ""), p.get("arguments") or {}, entries)
            send({
                "jsonrpc": "2.0",
                "id": mid,
                "result": {"content": [{"type": "text", "text": text}]},
            })
        elif method == "ping":
            send({"jsonrpc": "2.0", "id": mid, "result": {}})
        else:
            send({
                "jsonrpc": "2.0",
                "id": mid,
                "error": {"code": -32601, "message": f"no method {method!r}"},
            })


if __name__ == "__main__":
    main()
