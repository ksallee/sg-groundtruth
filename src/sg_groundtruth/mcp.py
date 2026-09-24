"""The corpus over MCP: stdio, JSON-RPC 2.0, standard library only.

An agent already holding a Flow Production Tracking MCP server can call the API. This one answers what
the API does, which is a different question and the one the other server cannot answer. The two are
meant to be mounted together.

Three tiers, the same ones a reader of the clone gets. `corpus_index` is the map: every entry by name
and the door to open. `corpus_door` is a door: one line per entry and that entry's rules. `corpus_entry`
is the entry, and it defaults to the rules rather than the transcript. Returning every verdict and every
tag on the first call, as this server did, is the 21,000-token index over the wire before the agent has
asked anything.

No dependency. The corpus is markdown with frontmatter, and reading it needs nothing that is not in the
standard library, so mounting this costs an operator no install beyond the clone.

Only `scope: api` entries are served. A `site` or `project` measurement is true of one installation, and
an agent that cannot tell the difference will state one as general behaviour. `--overlay` opts in to the
local ones, which is the same decision the reading level makes on the site.
"""
import json
import math
import re
import sys
from collections import Counter

from . import corpus as C
from .env import repo_root

# Anchored on the corpus, not on this file: installed, the package sits in site-packages with no
# corpus above it. `_load` reports the miss rather than serving an empty corpus, because an agent
# cannot tell "nothing probed that" from "no corpus found" in an empty answer.
ROOT = repo_root("corpus/INDEX.md")
CORPUS = ROOT / "corpus"
DOORS = CORPUS / "doors"
INDEX = CORPUS / "INDEX.md"
PROTOCOL = "2025-06-18"
SUPPORTED = {"2025-06-18", "2025-03-26", "2024-11-05"}

# Both quote forms the cards use, because three types quote the raw JSON body with the quotes still
# escaped. See the site's filter page for why this pattern is one and not two.
RELATIONS_RE = re.compile(r"Valid relations:\s*\[(.*?)\]", re.S)
TOKEN_RE = re.compile(r'\\?"([a-z_]+)\\?"')
WORD_RE = re.compile(r"[a-z0-9]+")


def _load(overlay):
    """Every entry, with the reading level it came from.

    Later roots do not overwrite earlier ones: a slug that exists at two levels is two entries, and
    the level is part of what an answer has to carry.
    """
    if not INDEX.is_file():
        raise SystemExit(
            f"no corpus at {CORPUS}. This server reads the corpus from a clone of "
            "sg-groundtruth; run it from inside one, or set the working directory to it. "
            "Installing the package does not install the corpus."
        )
    roots = [("api", CORPUS)]
    if overlay:
        local = ROOT / "corpus.local"
        if (local / "site").is_dir():
            roots.append(("site", local / "site"))
        pdir = local / "projects"
        if pdir.is_dir():
            roots += [("project", d) for d in sorted(pdir.iterdir()) if d.is_dir()]

    entries = []
    for level, root in roots:
        for e in C.load(root):
            if level == "api" and e.get("scope") != "api":
                continue  # a site or project measurement never ships as general behaviour
            e["level"] = level
            e["path"] = str((root / e["path"]).relative_to(ROOT))
            e["terms"] = _terms(e)
            entries.append(e)
    return entries


def _row(e):
    """One entry as a door writes it. An overlay entry has no door, so the row names the file."""
    if e["level"] == "api":
        return C.door_row(e)
    where = e.get("project") or e["level"]
    return f"- `{e['slug']}` ({e['group']}) [{where}] — {e['summary']}  \n  rules: `{e['path']}`"


def _stem(word):
    """Strip one suffix, then the silent `e`, to a fixed point.

    `expire`, `expires` and `expiring` are one term or a query for one of them misses the other two.
    Two passes settle the pairs that need them: `statuses` to `status` to `statu`, which is where
    `status` itself lands.
    """
    for _ in range(2):
        for suffix in ("ing", "edly", "ed", "ly", "es", "s"):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3:
                word = word[: -len(suffix)]
                break
        else:
            if len(word) > 3 and word.endswith("e"):
                word = word[:-1]
    return word


def _tokens(text):
    return [_stem(w) for w in WORD_RE.findall(text.lower())]


def _terms(e):
    """What an entry is searched on: its name, its verdict, its tags and its rules.

    Not the body. A search over whole entries ranks the entry that quotes a word in a transcript
    above the entry whose rule is about it, and every response sample mentions every field name.
    Tags count twice: a tag is the one retrieval key written by hand.
    """
    rules = " ".join(C.rules(e))
    return Counter(_tokens(f"{e['slug']} {e['summary']} {rules}") + _tokens(" ".join(e["tags"])) * 2)


def _rank(entries, query, limit=10):
    """BM25 over those terms. k1 and b are the usual defaults; nothing here is tuned per query."""
    q = [t for t in _tokens(query) if t]
    if not q:
        return []
    n = len(entries)
    lengths = [sum(e["terms"].values()) for e in entries]
    avg = sum(lengths) / n if n else 0
    df = Counter()
    for e in entries:
        df.update(set(e["terms"]))
    k1, b = 1.5, 0.75
    scored = []
    for e, length in zip(entries, lengths):
        score = 0.0
        for t in q:
            f = e["terms"].get(t, 0)
            if not f:
                continue
            idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
            score += idf * f * (k1 + 1) / (f + k1 * (1 - b + b * length / (avg or 1)))
        if score:
            scored.append((score, e))
    scored.sort(key=lambda s: (-s[0], s[1]["slug"]))
    return [e for _, e in scored[:limit]]


def _door_names():
    return sorted(f.stem for f in DOORS.glob("*.md"))


def _endpoint_door(endpoint):
    """The door the generator put this call on.

    Read off the doors rather than recomputed: a family splits by method, and then by call, as it
    grows, and only the generator knows where a given call landed.
    """
    head = f"`{endpoint}`"
    for f in sorted(DOORS.glob("endpoints-*.md")):
        for line in f.read_text().splitlines():
            if line.startswith("#") and line.lstrip("#").strip().split(" **[")[0] == head:
                return f"doors/{f.stem}"
    return f"doors/endpoints-{C.family(endpoint).lower()}"


def _canonical(path):
    """A caller holds a real path. The corpus is written against one spelling of it.

    `POST /entity/shots/_search` and `POST /entity/versions/_search` are the same endpoint; so are
    `PUT /entity/versions/53` and `PUT /entity/versions/{id}`. Normalise before matching, or an
    agent asking about its own call finds nothing and concludes the corpus is silent.
    """
    parts = path.strip().split()
    method = parts[0].upper() if parts and parts[0].isalpha() else ""
    p = re.sub(r"^https?://[^/]+", "", parts[-1] if parts else "").split("?")[0]
    p = re.sub(r"^/api/v\d+", "", p)
    if not p.startswith("/"):
        return f"{method} {p}".strip()          # PUT <links.upload> and its kind
    out = []
    for s in p.strip("/").split("/") if p.strip("/") else []:
        prev = out[-1] if out else ""
        if prev == "schema":
            out.append("<Type>")
        elif prev == "fields":
            out.append("<field>")
        elif prev == "entity" and s != "_batch":
            out.append("<type>")
        elif prev == "<type>" and s not in ("_search", "_summarize"):
            out.append("<id>")
        elif prev == "<id>" and s != "_upload":
            out.append("<field>")
        elif prev == "<Type>" and s != "fields":
            out.append("<field>")
        else:
            out.append(s)
    return f"{method} /{'/'.join(out)}".strip()


def _segments(path):
    """A call's method and path segments, the site URL, the API version and the query string gone."""
    parts = path.strip().split()
    method = parts[0].upper() if parts and parts[0].isalpha() else ""
    p = re.sub(r"^https?://[^/]+", "", parts[-1] if parts else "").split("?")[0]
    p = re.sub(r"^/api/v\d+", "", p)
    return method, [s for s in p.strip("/").split("/") if s]


# What a caller fills in: `<type>`, `<Type>`, `<id>`, `<record_uuid>`, and `<format>` inside
# `spec.<format>`. `<links.upload>` is not one of them: it is the literal the API hands back, and the
# dot is what separates the two.
SLOT_RE = re.compile(r"(<[A-Za-z_]+>)")


def _matches(pattern, seg):
    """One card segment against one real segment, a slot standing for anything but a slash."""
    pat = "".join("[^/]+" if SLOT_RE.fullmatch(tok) else re.escape(tok)
                  for tok in SLOT_RE.split(pattern))
    return re.fullmatch(pat, seg) is not None


def _fits(card, method, segs):
    """Whether a card's pattern covers this call."""
    cm, cs = _segments(card["endpoint"])
    if method and cm and cm != method:
        return False
    return len(cs) == len(segs) and all(_matches(c, s) for c, s in zip(cs, segs))


def _literals(card):
    return sum(1 for s in _segments(card["endpoint"])[1] if not SLOT_RE.search(s))


def _resolve(cards, asked):
    """The card for the call the caller holds, and the spelling it normalises to.

    The card patterns segment by segment, most literal segments first, and the canonical form after
    them. Normalising alone sends `/entity/shots/1/activity_stream` to the field card: every segment
    after an id reads as a field name, and eight cards keep a literal there. Matching the pattern is
    what makes the call an agent is about to make resolve to the card written about it.
    """
    want = _canonical(asked)
    method, segs = _segments(asked)
    fits = [c for c in cards if _fits(c, method, segs)]
    if fits:
        best = max(_literals(c) for c in fits)
        fits = [c for c in fits if _literals(c) == best]
        if len(fits) == 1:
            return fits[0], want, []
    hit = next((c for c in cards if c["endpoint"] == want), None)
    return hit, want, [] if hit else fits


TOOLS = [
    {
        "name": "corpus_index",
        "description": (
            "The map: every entry by name, grouped, and the door to open for each way in. Read this "
            "first. With tag, phase or group it returns that slice as door rows instead, each naming "
            "the door its rules are on."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "tag": {"type": "string", "description": "Only entries carrying this tag."},
                "phase": {
                    "type": "string",
                    "description": ("The part of a session a finding bites in: auth, protocol, schema, "
                                    "read, filter, write, upload, observe, render."),
                },
                "group": {
                    "type": "string",
                    "description": ("findings, field_types, entity_types, recipes, endpoints "
                                    "or reports."),
                },
            },
        },
    },
    {
        "name": "corpus_door",
        "description": (
            "One door: a line per entry and that entry's rules, copied whole. Name it as the map "
            "spells it: findings-read, endpoints-post-entity-type-search, endpoints-records-get, field_types, "
            "entity_types, recipes, reports, tags. An unknown name returns the list."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    },
    {
        "name": "corpus_entry",
        "description": (
            "One entry, by slug. view=rules, the default, is the verdict and the rules as the door "
            "carries them. view=full is the entry: the transcript, the sample and the tables that "
            "prove them."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "slug": {"type": "string"},
                "view": {"type": "string", "enum": ["rules", "full"]},
            },
            "required": ["slug"],
        },
    },
    {
        "name": "corpus_search",
        "description": (
            "Ranked search over every entry's name, verdict, tags and rules. Returns the ten best as "
            "one-liners, each naming the door its rules are on."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
    {
        "name": "corpus_endpoint",
        "description": (
            "What the corpus records about one REST call. Pass the endpoint you are about to make, in "
            "any spelling: POST /entity/shots/_search, PUT /entity/versions/53 and the canonical form "
            "all resolve to the same card. Returns the card and the endpoint door's row for the call: "
            "the edge cases, every entry that measured it, and what is silent on it. Omit endpoint for "
            "the whole list, where an endpoint with no entries is one nothing has probed yet."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "endpoint": {
                    "type": "string",
                    "description": "e.g. 'POST /entity/versions/_search' or '/schema/Version/fields'.",
                }
            },
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
        m = RELATIONS_RE.search(card["text"])
        if m:
            out[name] = sorted(set(TOKEN_RE.findall(m.group(1))))
        elif "cannot be used in a filter" in card["text"]:
            out[name] = []
        else:
            out[name] = None
    return out


def _index(entries, args):
    rows = entries
    if args.get("tag"):
        rows = [e for e in rows if args["tag"] in e["tags"]]
    if args.get("group"):
        rows = [e for e in rows if e["group"] == args["group"]]
    if args.get("phase"):
        rows = [e for e in rows if e.get("phase") == args["phase"]]
    if not any(args.get(k) for k in ("tag", "group", "phase")):
        out = INDEX.read_text()
        local = [e for e in entries if e["level"] != "api"]
        if local:
            out += ("\n## Overlay\n\nRead with `--overlay`, and true of this installation alone. No "
                    "door is generated at these levels; the row names the file.\n\n"
                    + "\n".join(_row(e) for e in local) + "\n")
        return out
    if not rows:
        return "No entry matches. Call corpus_index with no arguments for the map and its vocabulary."
    return f"{len(rows)} entries.\n\n" + "\n".join(_row(e) for e in rows)


def _entry(entries, args):
    slug, view = args.get("slug", ""), args.get("view") or "rules"
    hit = next((e for e in entries if e["slug"] == slug), None)
    if hit is None:
        near = [e["slug"] for e in entries if slug and slug in e["slug"]]
        return f"No entry {slug!r}." + (f" Did you mean: {', '.join(near)}" if near else "")
    head = "  ".join([hit["path"]]
                     + [f"{k}: {hit[k]}" for k in ("scope", "measured", "project") if hit.get(k)])
    if view == "full":
        return f"{head}\n\n{hit['text']}"
    rules = C.rules(hit)
    if hit["level"] == "api":                   # an overlay entry has no door; the head names the file
        head += f"  rules: `{C.door_of(hit)}`"
    return (f"{head}\n\n{hit['summary']}{C.mark(hit)}\n\n"
            + ("\n\n".join(rules) if rules else "No rule beyond the entry.")
            + "\n\nThe transcript, the sample and the tables are the entry: "
              f"corpus_entry {slug} with view=\"full\".")


def _endpoint(entries, args):
    cards = sorted((e for e in entries if e["group"] == "endpoints"),
                   key=lambda e: e["endpoint"])
    behind = C.by_endpoint(entries)
    asked = (args.get("endpoint") or "").strip()
    if not asked:
        probed = sum(1 for c in cards if behind.get(c["endpoint"]))
        rows = [f"- {c['endpoint']} — {c['summary']}\n  "
                + (", ".join(e["slug"] for e in C.joined(c, behind))
                   or "NOT PROBED: nothing in the corpus measures this")
                for c in cards]
        return (f"{probed} of {len(cards)} endpoints have an entry behind them.\n\n"
                + "\n".join(rows))

    hit, want, near = _resolve(cards, asked)
    if hit is None and near:
        return (f"{asked!r} normalises to {want!r}, which matches several cards:\n"
                + "\n".join(f"- {c['endpoint']} — {c['summary']}" for c in near))
    if hit is None:
        return (f"{asked!r} normalises to {want!r}, which has no card in corpus/endpoints/. Call "
                f"corpus_endpoint with no argument for the list. An absent endpoint means nothing "
                f"here has probed it, not that the API lacks it.")

    rows = C.joined(hit, behind)
    out = [f"{hit['path']}  door: `{_endpoint_door(hit['endpoint'])}`", "", hit["text"].rstrip(), ""]
    joined = C.measured_by(rows) + C.silent_on(hit, rows)
    out += joined or ["No finding or recipe measures this call beyond the card."]
    return "\n".join(out)


def _call(name, args, entries):
    if name == "corpus_index":
        return _index(entries, args)

    if name == "corpus_door":
        want = (args.get("name") or "").strip().strip("`")
        want = want.removeprefix("corpus/").removeprefix("doors/").removesuffix(".md")
        f = DOORS / f"{want}.md"
        if want and "/" not in want and f.is_file():
            return f.read_text()
        return (f"No door {args.get('name')!r}. The doors are:\n"
                + "\n".join(f"- {n}" for n in _door_names()))

    if name == "corpus_entry":
        return _entry(entries, args)

    if name == "corpus_search":
        hits = _rank(entries, args.get("query", ""))
        if not args.get("query", "").strip():
            return "Give a query."
        if not hits:
            return (f"Nothing matches {args['query']!r}. corpus_index with no arguments is the map, "
                    "and its tag list is the vocabulary that selects.")
        return f"Top {len(hits)}, best first.\n\n" + "\n".join(_row(e) for e in hits)

    if name == "corpus_endpoint":
        return _endpoint(entries, args)

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
