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

## The tiers

Three, and they are the ones a reader of the clone gets. An agent that stops at a door has the rule; it
opens the entry when it needs the evidence.

| tier | tool | holds | chars |
|---|---|---|---|
| map | `corpus_index` | every entry by name, grouped, and the door to open for each way in | 7,700 |
| door | `corpus_door` | one line per entry and that entry's rules, copied whole | 2,300 to 35,600 |
| entry | `corpus_entry` | the verdict and the rules, or the whole entry with `view="full"` | 500 to 4,500 |

The map says which door to open.

| you know | open |
|---|---|
| the call | `corpus_endpoint`, which answers with the call's own row off its family door |
| the entity type | `corpus_door` `entity_types` |
| the `data_type` | `corpus_door` `field_types` |
| the task | `corpus_door` `recipes` |
| the phase of a session | `corpus_door` `findings-<phase>` |

An endpoint door holds the edge cases that live on the call and the verdict of every entry that measured
it, each naming the group door its rules are on. Read the verdicts, open that door for the rules, the
entry for a transcript, a sample or a table. A 2xx that did nothing is under **Silent on this call**.

## The tools

| tool | answers | chars |
|---|---|---|
| `corpus_index` | the map. With `tag`, `phase` or `group`, that slice as door rows | 7,700, a slice 2,300 |
| `corpus_door` | one door, by the name the map spells. An unknown name returns the list | 2,300 to 35,600 |
| `corpus_entry` | one entry, `view="rules"` by default and `view="full"` for the transcript | 1,900 against 4,300 |
| `corpus_search` | the ten best entries, ranked, each naming the door its rules are on | 2,500 |
| `corpus_endpoint` | the card for one call, and its row off the family door | 11,500 |
| `filter_operators` | the relations the API accepts per data type. Omit `data_type` for all 24 | 1,600 |

Sizes are measured against the 178 `scope: api` entries on 2026-09-14, for `phase: read`,
`doors/findings-read`, `026_result_order` and `POST /entity/<type>/_search`.

A door name is the one on the map: `findings-read`, `endpoints-post-entity-type-search`, `endpoints-records-get`,
`field_types`, `entity_types`, `recipes`, `reports`, `tags`. A family splits by method as it grows, then
by call: `endpoints-records-get` is a method door, `endpoints-post-entity-type-search` a call door. The map
names every one.

`corpus_endpoint` resolves the call the agent is about to make. `POST /entity/shots/_search`,
`PUT /entity/versions/53`, `GET /entity/shots/1/activity_stream` and a full site URL each reach their
own card, matched segment by segment against the card's pattern rather than by string. It returns the
card in full, then the call's row off the family door: every entry that measured it with the door its
rules are on, and what is silent on it. Omit `endpoint` for the list, where a row reading `NOT PROBED`
is a card no finding stands behind, which is the queue rather than a gap in the tool.

`corpus_search` is BM25 over each entry's name, verdict, tags and rules, with a suffix stemmer, so
`expire`, `expires` and `expiring` are one term. Tags count twice: a tag is the one retrieval key
written by hand. The body is not searched. An entry that quotes a word in a transcript is not about it,
and every recorded response mentions every field name, which is how the substring search this replaced
answered `sort` with 38 entries in file order and `movie link` with 19, the one that mattered outside
the first five.

| query | ranks |
|---|---|
| `movie link` | `022_sequence_on_version`, `url`, `006_media_round_trip` |
| `presigned expires` | `url`, `006_media_round_trip`, `002_complete_upload_without_bytes` |
| `sort` | `026_result_order`, `Playlist`, `003_sort_fails_silently` |

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

`bin/check-mcp` is the gate. It drives one server process over stdio through `initialize`, `tools/list`
and a `tools/call` per tool, and checks the answers rather than the transport.

| | |
|---|---|
| `initialize`, `tools/list` and one `tools/call` per tool | tested, 6 of 6 tools |
| The map is `corpus/INDEX.md`, and a door is the door file, byte for byte | tested, 27 of 27 doors |
| Every card's endpoint resolving to its own card | tested, 69 of 69 |
| A real path resolving to the card written about it, site URL and all | tested, 7 of 7 |
| The three rankings above | tested |
| Scope filtering, that no `site` or `project` entry is served without `--overlay` | tested |
| `filter_operators`, every field-type card answered and each type's own call agreeing with the listing | tested, 24 of 24 |
| Running it beside a third-party Flow PT MCP server in one agent session | **not tested** |
| Whether an agent given both reaches for the right one | **not tested** |

`site/RESEARCH-mcp.md` records what three third-party servers' own sources say, read at pinned commits.
That is source verification and not a test: nothing was installed, and no agent was measured using one.
Anything on the site about those servers should be read that way.
