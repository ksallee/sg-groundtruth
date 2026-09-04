# SG Ground Truth

Recorded behaviour of the Flow Production Tracking REST API.

The REST documentation is incomplete and in places wrong. Every entry here is what a live Flow PT site
answered when a probe asked it one question: the status code, the error string, the response shape, in
the words the API used. The 51 probes that produced it are in this repository and run against any site.

## Read it

    git clone https://github.com/ksallee/sg-groundtruth

Then give an agent one line:

    Read sg-groundtruth/corpus/INDEX.md first.
    Open an entry only when its one-liner falls short.

`corpus/INDEX.md` is generated: 67 KB, one line per entry with its verdict and its tags. The corpus
behind it is much larger, and an agent that loads all of it spends its context on the first call.

## What is in `corpus/`

| directory | holds |
|---|---|
| `endpoints/` | 64 cards, one per REST call: what it takes, every status code it answers with, a recorded response |
| `findings/entity_types/` | 17 cards, one per schema name: identity, the create contract, every link field, the status field |
| `findings/field_types/` | 24 cards, one per `data_type`: what it reads, writes and clears as, and what filters it |
| `findings/` | 40 questions, each answered by one probe, grouped by the phase of a session they bite in |
| `recipes/` | 11 tasks, each with the calls that perform it, the real response, and the errors hit on the way |
| `INDEX.md` | generated. Read this first |

Four ways in, one per thing a caller already knows before making a call: the call itself, the entity
type, the field's `data_type`, or the task.

## Why it exists

A 400 names the legal set and an agent recovers from it. A 200 that ignored what you sent teaches it
nothing. Each row is a published finding.

| you do this | this happens |
|---|---|
| Sort on a misspelled field | `200`. The sort is ignored, rows come back id ascending, and nothing says so |
| Page until `links.next` is absent | It is never absent. It is emitted on zero-row pages too. Stop when `data` is empty |
| Create rows in a batch | You get an id per row. A batch can return an id for a row it never made |
| Create a field whose display name is taken | `201`. You got `<name>_1` |

## Mount it over MCP

    PYTHONPATH=src python -m sg_groundtruth.mcp

Five tools, stdio, standard library only, so mounting it costs nothing beyond the clone. `PYTHONPATH`
is not optional: the package is not installed. Registration for Claude Code and any other stdio client
is in [docs/mcp.md](docs/mcp.md).

It answers what the API does. A Flow PT MCP server calls the API. An agent given both has to be told
which is which.

## Put your own site in it

The corpus covers any Flow PT site. One command measures yours: your custom entities, your field
names, your status vocabularies, your projects.

    cd sg-groundtruth
    claude

Then ask for `/sg-groundtruth-setup`. Start the agent inside the clone: the command is one of this
repository's own and is registered when the session starts.

| | |
|---|---|
| Writes to your site | Nothing, unless a probe is run with `--write` |
| Project it may write into | The sandbox you name, and no other |
| Where your data goes | `corpus.local/`, gitignored, never leaves your machine |

## Scopes

Every entry declares one, because a measurement that is true of one site is not a fact about the API.

| scope | true of | committed |
|---|---|---|
| `api` | Any Flow PT site: status codes, error strings, value shapes, operator vocabularies | Yes |
| `site` | One site: which custom entities are enabled, which fields exist, `valid_values` | Only when scrubbed |
| `project` | One project inside it: `hidden_values`, page columns, fill rates | No |

`valid_values` is byte-identical at every scope and only `hidden_values` varies by project, so "which
statuses can I use" has no site-level answer. That is why the last two are not one scope (probe 009).

## Probes

    python probes/017_filter_operators.py

One question per probe. A probe prints what the API answered and deletes anything it created before it
exits; it never writes the corpus. An agent reads the output and writes the entry. Every entry names
the probe that produced it, so a claim you doubt, you re-run.

Read-only by default. A write needs `--write`, and the only project a probe may write into is the
sandbox named in `.env.local`.

## Layout

| path | |
|---|---|
| `corpus/` | the corpus. `scope: api`, committed, the product |
| `probes/` | the scripts that produced it, plus `check_corpus.py` and `index.py` |
| `src/sg_groundtruth/` | the MCP server, the schema inspector, the client |
| `site/` | SvelteKit, prerendered static, renders the corpus and any local overlay |
| `docs/` | MCP registration, the example overlay, unverified operator claims |
| `corpus.local/` | your own site, written by the setup command. Gitignored |

## Licence

[MIT](LICENSE). Nothing AGPL enters this repository, at any depth. It is derived only from the public
Flow PT REST documentation and this repository's own probes, so that studio legal can say yes without
reading anything.
