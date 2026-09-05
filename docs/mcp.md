# The corpus over MCP

An MCP server for Flow Production Tracking lets an agent call the API. This one answers what the API
does when you call it, which is a different question, and the reason to mount both.

    PYTHONPATH=src python -m sg_groundtruth.mcp

Standard library only, stdio, JSON-RPC 2.0. No dependency, so mounting it costs nothing beyond the clone.

## Register it

Claude Code:

    claude mcp add sg-groundtruth --scope user \
      -e PYTHONPATH=/path/to/sg-groundtruth/src \
      -- python -m sg_groundtruth.mcp

`PYTHONPATH` is not optional. The package is not installed, so without it `python -m sg_groundtruth.mcp`
raises `ModuleNotFoundError: No module named 'sg_groundtruth'` from any directory except `src/` itself.
Any client that speaks stdio MCP works the same way. In a `mcp.json`:

    {
      "mcpServers": {
        "sg-groundtruth": {
          "command": "python",
          "args": ["-m", "sg_groundtruth.mcp"],
          "env": { "PYTHONPATH": "/path/to/sg-groundtruth/src" }
        }
      }
    }

Servers load when a session starts, so the tools appear in the next session, not the one that registered
it. `claude mcp list` should show `sg-groundtruth ... ✔ Connected`.

## The tools

| tool | answers |
|---|---|
| `corpus_index` | every entry's slug, verdict and tags. Filter by `tag` or `group`. Call this first |
| `corpus_entry` | one entry in full, by slug, with its `scope` and `measured` line |
| `corpus_search` | entries mentioning every word given, returned as one-liners |
| `corpus_endpoint` | the whole card for one call. Pass the endpoint in any spelling |
| `filter_operators` | the relations the API accepts per data type, as the API printed them. Omit `data_type` for all 24 |

`corpus_endpoint` normalises before matching, so an agent asks with the call it is actually about to
make. `POST /entity/shots/_search`, `PUT /entity/versions/53` and a full site URL all resolve to the
same card. It returns the card in full: the request contract, every status code with its error string,
a recorded response, the edge cases, a runnable sample, and the verdict of every finding that measured
the call. Omit `endpoint` for the list, where a row reading `NOT PROBED` is a card no finding stands
behind, which is the queue rather than a gap in the tool.

`corpus_index` also takes `phase`, one of `auth`, `protocol`, `schema`, `read`, `filter`, `write`,
`upload`, `observe`, `render`. That is the part of a session a finding bites in.

`group` is one of `findings`, `field_types`, `entity_types`, `recipes`, `endpoints` or `reports`. Every
group's one-liner reaches the server under a different frontmatter key, `verdict` on a finding, an
endpoint card and a matrix card, `intent` on a recipe and `summary` on a report, and the loader reads
all three. Requiring `verdict` there once dropped all ten recipes with nothing said.

`filter_operators` with no argument is the call to make before building anything that filters. It is 24
lines and it is the difference between offering an operator that works and one that returns 400, or
worse, omitting a type that filters fine because you never met a field of it.

## What it will not serve

Only `scope: api` entries, the ones true of any Flow PT site. A `site` or `project` measurement is true
of one installation, and an agent that cannot tell the two apart will state a local vocabulary as general
behaviour.

    PYTHONPATH=src python -m sg_groundtruth.mcp --overlay

opts into the local ones, which is the same decision the reading level makes on the site. On the probed
site that takes 67 entries to 108. Use it when the agent is working against that site and nowhere else.

## Alongside a Flow PT MCP server

The two answer different questions and neither replaces the other.

| ask | server |
|---|---|
| "list Shots where status is ip" | the Flow PT server. It holds the credential and makes the call |
| "which operators does a `date` field accept" | this one. It holds what the API answered when asked |
| "what does `POST /entity/shots/_search` do" | this one. `corpus_endpoint` |
| "why did my filter return every row" | this one |

Tell the agent which is which, or it will use whichever it happens to reach first:

    Two servers. sg-groundtruth answers how the Flow Production Tracking API behaves, from recorded
    probe output. The other one calls the API. Before writing any call, ask sg-groundtruth what the
    API does; before filtering, call filter_operators. A 200 from this API does not mean your request
    was understood.

## What has and has not been tested

| | |
|---|---|
| This server, driven over stdio through initialize, tools/list and tools/call | tested |
| `corpus_endpoint` path normalisation, every canonical endpoint resolving to itself | tested, 23 of 23 |
| Its `filter_operators` output against the corpus's own field-type cards | tested, 24 of 24 agree |
| Scope filtering, that no `site` or `project` entry is served without `--overlay` | tested |
| Running it beside a third-party Flow PT MCP server in one agent session | **not tested** |
| Whether an agent given both reaches for the right one | **not tested** |

`site/RESEARCH-mcp.md` records what three third-party servers' own sources say, read at pinned commits.
That is source verification and not a test: nothing was installed, and no agent was measured using one.
Anything on the site about those servers should be read that way.
