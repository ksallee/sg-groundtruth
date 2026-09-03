---
description: Turn the operator's own Flow PT calling code into probes and recipes
---

Path: $ARGUMENTS

The operator has code that already calls this API. It encodes things somebody learned the hard way and
wrote down nowhere. This turns each of those into a finding or a recipe, or discovers it was never true.

## Clean room, and it binds here too

Read only the path the operator named. `~/dev/fpt-ai`, `~/dev/fpt-api`, `~/dev/flow-data-api-docs`,
`~/dev/flow-data-sdk-python` and `~/dev/tk-*` stay unread, whatever the named path imports or vendors. If
the path *is* one of those, stop and say why.

Their own code is theirs to read. Nothing derived from it may be copied into the corpus verbatim: what
lands is a probe you wrote and the response your probe got.

## 1. Inventory the calls, do not read the prose

Find every distinct request. Group by endpoint and method, not by call site: twenty places posting a
Version are one entry.

| record per call | example |
|---|---|
| endpoint and method | `POST /api/v1/entity/versions` |
| the fields it sends | `sg_status_list`, `entity`, `sg_uploaded_movie` |
| the shape it expects back | `data.attributes`, `data.relationships.entity` |
| what it does on failure | retries, swallows, or falls over |
| the comment beside it | this is where the lore is |

Report the inventory before writing anything. The operator will recognise which entries are load-bearing
and which are dead, and they will know things about their own code you cannot see.

## 2. Sort each entry into one of four

| the code | do |
|---|---|
| matches a corpus entry | cite it, `# probe NNN`, and move on. Nothing to write |
| contradicts a corpus entry | probe it. One of the two is wrong and finding out which is the whole value |
| does something the corpus does not cover | `/probe` it, one question at a time |
| works and is worth repeating | `/recipe` it |

The second row is the reason to run this at all. A comment reading "the API needs this or it 400s" is a
claim, and this repository does not ship claims.

## 3. A workaround is a finding, and usually the best one

Look for the shapes that mean somebody hit a wall:

| shape | probe |
|---|---|
| a retry loop around one call | what does that call return, and when |
| a sleep before a read | is the write eventually consistent, and for how long |
| a field written twice | did the first write not take |
| a hardcoded id or status code | does the vocabulary transfer, or was it read off one project |
| a try/except with a bare pass | what error is being swallowed, and is it real |
| a comment saying "do not remove" | this is the highest-value entry in the inventory |

## 4. Write nothing by hand from their source

Every corpus entry comes from a probe this repository ran against the API, never from reading code. A
finding written from a source comment is an unverified operator claim, which is what `docs/quirks.md` is
for. Put it there instead and say it needs probing.

## 5. Report

The inventory, how many entries fell into each of the four, and the single contradiction most worth
probing first. Do not summarise their codebase back to them.
