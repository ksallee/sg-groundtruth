# Result

Measured on 2026-09-14 against `dev` at `3567671`, 180 entries. Tokens are chars/4, the counting
issue #56 uses. No agent ran and no call was made against Flow Production Tracking: a strategy here
is a rule for deciding what to read, and the score is whether the rule a required entry teaches was
inside what the strategy read.

Reproduce with `python experiments/retrieval/score.py` from the repository root. The task set is
`tasks.json`: 13 briefs in a consumer's words, the plan an agent holds before it reads anything, and
the entries whose rules the brief needs.

## The three strategies

| strategy | reads | given |
|---|---|---|
| `index` | `corpus/INDEX.md` whole, then every required entry in full | the required set |
| `doors` | the map, then the doors the plan names | the plan |
| `grep` | the rule section of every entry whose `endpoints:` or `tags:` match the plan | the plan |

`index` is what an agent does today, and the issue defines it as reading the required entries. It is
handed the answer, so its recall is 1/1 at both tiers by construction and what it contributes is a
cost. The other two decide what to read from the plan alone, and neither opens an entry, so the
entry-tier column is 0 for both and the door tier is the headline.

## Decisions

The issue leaves four choices to the scorer. All four are in `score.py`.

| decision | |
|---|---|
| which entries `doors` opens in full | none. An entry is opened when a rule needs its transcript, and no rule in this set does: every required rule is a bullet. Opening on a heuristic would score the heuristic |
| the recipes door | opened on every task. The map's protocol says the task is a door, and every brief here is a task. It costs 11,776 tokens on all 13, priced separately below |
| how much of a door is read | the whole file. A model reads a file, not a byte range. `--per-call` prices the alternative |
| what `grep` matches | `endpoints:` against the plan's calls verbatim, and `tags:` against the lowercased entity types and data types, hyphenated at each capital (`PublishedFile` reaches `published-file`), plus the phase |

The doors do not exist yet, so `score.py` builds the same tiers from each entry's own rule section:
`**Teaches**` on a finding, `**Traps**` on a matrix card, `## Notes` on a recipe, `**Edge cases**` on
an endpoint card, joined onto the endpoint doors by the `endpoints:` frontmatter key. It reads
`corpus/doors/` instead the moment that directory exists.

The built map is 5,964 bytes, 1,491 tokens, against the 2,000 #56 budgets and the 8,000-byte cap it
proposes. `corpus/INDEX.md` today is 82,287 bytes, 20,572 tokens.

The doors, built. The last column is what the family would cost if an entry joined onto four calls
were written out four times; the builder writes it once and names the calls.

| door | entries | tokens | bytes | tokens if every join were written out |
|---|---|---|---|---|
| `endpoints-Attention` | 7 | 2,667 | 10,668 | 2,800 |
| `endpoints-Exports` | 3 | 1,741 | 6,963 | 2,238 |
| `endpoints-Media` | 23 | 7,344 | 29,378 | 12,775 |
| `endpoints-Other` | 4 | 1,104 | 4,416 | 1,232 |
| `endpoints-Records` | 43 | 22,770 | 91,081 | 36,873 |
| `endpoints-Schema` | 26 | 13,311 | 53,244 | 15,027 |
| `endpoints-Search` | 29 | 16,268 | 65,073 | 18,360 |
| `endpoints-Session` | 9 | 2,402 | 9,608 | 3,558 |
| `endpoints-Site` | 12 | 4,344 | 17,377 | 4,749 |
| `endpoints-Webhooks` | 13 | 4,235 | 16,941 | 11,046 |
| `entity_types` | 19 | 5,668 | 22,670 |  |
| `field_types` | 24 | 7,220 | 28,882 |  |
| `findings-auth` | 3 | 994 | 3,975 |  |
| `findings-filter` | 5 | 2,434 | 9,734 |  |
| `findings-observe` | 3 | 2,297 | 9,187 |  |
| `findings-protocol` | 3 | 658 | 2,630 |  |
| `findings-read` | 11 | 5,200 | 20,801 |  |
| `findings-render` | 1 | 540 | 2,158 |  |
| `findings-schema` | 8 | 3,508 | 14,033 |  |
| `findings-upload` | 5 | 1,626 | 6,503 |  |
| `findings-write` | 6 | 3,512 | 14,047 |  |
| `recipes` | 13 | 11,776 | 47,104 |  |

## Per task

### weekly-report

From experiments/weekly-report/BRIEF.md, graded against SCORECARD.md traps 1-5, 7, 8.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 6/6 (100%) | 6/6 (100%) | 26,555 | corpus/INDEX.md, then 6 entries in full |
| `doors` | 6/6 (100%) | 0/6 (0%) | 72,020 | map, endpoints-Records, endpoints-Search, entity_types, field_types, findings-read, findings-upload, recipes |
| `grep` | 6/6 (100%) | 0/6 (0%) | 26,672 | 64 entries, rules only |

### movie-link

From experiments/weekly-report/SCORECARD.md trap 5, the one trap that separated the arms.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 23,216 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 1/2 (50%) | 0/2 (0%) | 70,394 | map, endpoints-Records, endpoints-Search, entity_types, field_types, findings-read, recipes |
| `grep` | 2/2 (100%) | 0/2 (0%) | 23,217 | 53 entries, rules only |

`doors` missed: corpus/findings/013_upload_media.md

### attach-to-note

From experiments/weekly-report/SCORECARD.md traps 7 and 8.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 22,212 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 2/2 (100%) | 0/2 (0%) | 36,828 | map, endpoints-Search, entity_types, findings-upload, recipes |
| `grep` | 2/2 (100%) | 0/2 (0%) | 21,507 | 50 entries, rules only |

### entity-dict-name

From issue #7.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 24,410 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 2/2 (100%) | 0/2 (0%) | 70,394 | map, endpoints-Records, endpoints-Search, entity_types, field_types, findings-read, recipes |
| `grep` | 1/2 (50%) | 0/2 (0%) | 22,007 | 44 entries, rules only |

`grep` missed: corpus/findings/field_types/entity.md

### status-icon

From issue #9, items 1 and 2.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 25,380 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 2/2 (100%) | 0/2 (0%) | 56,274 | map, endpoints-Schema, endpoints-Search, entity_types, field_types, findings-render, recipes |
| `grep` | 2/2 (100%) | 0/2 (0%) | 15,616 | 29 entries, rules only |

### dotted-path-type

From issue #9, item 3.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 22,088 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 2/2 (100%) | 0/2 (0%) | 70,394 | map, endpoints-Records, endpoints-Search, entity_types, field_types, findings-read, recipes |
| `grep` | 2/2 (100%) | 0/2 (0%) | 20,343 | 41 entries, rules only |

### publish-across-platforms

From issue #10.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 5/5 (100%) | 5/5 (100%) | 29,344 | corpus/INDEX.md, then 5 entries in full |
| `doors` | 5/5 (100%) | 0/5 (0%) | 68,705 | map, endpoints-Records, endpoints-Search, entity_types, field_types, findings-write, recipes |
| `grep` | 5/5 (100%) | 0/5 (0%) | 23,487 | 50 entries, rules only |

### publish-bytes-no-root

From issue #17, item 1.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 3/3 (100%) | 3/3 (100%) | 26,142 | corpus/INDEX.md, then 3 entries in full |
| `doors` | 3/3 (100%) | 0/3 (0%) | 50,551 | map, endpoints-Records, entity_types, field_types, findings-upload, recipes |
| `grep` | 3/3 (100%) | 0/3 (0%) | 17,870 | 41 entries, rules only |

### stock-vs-custom

From issue #17, item 2.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 22,637 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 2/2 (100%) | 0/2 (0%) | 35,754 | map, endpoints-Schema, entity_types, findings-schema, recipes |
| `grep` | 2/2 (100%) | 0/2 (0%) | 21,928 | 48 entries, rules only |

### impersonate

From issues #36 and #42.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 3/3 (100%) | 3/3 (100%) | 26,123 | corpus/INDEX.md, then 3 entries in full |
| `doors` | 3/3 (100%) | 0/3 (0%) | 22,330 | map, endpoints-Session, entity_types, findings-auth, recipes |
| `grep` | 2/3 (67%) | 0/3 (0%) | 2,640 | 12 entries, rules only |

`grep` missed: corpus/findings/entity_types/HumanUser.md

### create-a-person

From issue #37.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 1/1 (100%) | 1/1 (100%) | 22,546 | corpus/INDEX.md, then 1 entries in full |
| `doors` | 1/1 (100%) | 0/1 (0%) | 45,216 | map, endpoints-Records, entity_types, findings-write, recipes |
| `grep` | 0/1 (0%) | 0/1 (0%) | 19,245 | 46 entries, rules only |

`grep` missed: corpus/findings/entity_types/HumanUser.md

### sign-in-as-a-person

From issue #45.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 4/4 (100%) | 4/4 (100%) | 24,054 | corpus/INDEX.md, then 4 entries in full |
| `doors` | 4/4 (100%) | 0/4 (0%) | 22,330 | map, endpoints-Session, entity_types, findings-auth, recipes |
| `grep` | 4/4 (100%) | 0/4 (0%) | 2,640 | 12 entries, rules only |

### text-search

From issue #48.

| strategy | door-tier recall | entry-tier recall | tokens | read |
|---|---|---|---|---|
| `index` | 2/2 (100%) | 2/2 (100%) | 22,854 | corpus/INDEX.md, then 2 entries in full |
| `doors` | 2/2 (100%) | 0/2 (0%) | 37,636 | map, endpoints-Search, entity_types, findings-filter, recipes |
| `grep` | 2/2 (100%) | 0/2 (0%) | 21,765 | 47 entries, rules only |

## Summary

| task | required | `index` tokens | `doors` recall | `doors` tokens | `grep` recall | `grep` tokens |
|---|---|---|---|---|---|---|
| weekly-report | 6 | 26,555 | 6/6 (100%) | 72,020 | 6/6 (100%) | 26,672 |
| movie-link | 2 | 23,216 | 1/2 (50%) | 70,394 | 2/2 (100%) | 23,217 |
| attach-to-note | 2 | 22,212 | 2/2 (100%) | 36,828 | 2/2 (100%) | 21,507 |
| entity-dict-name | 2 | 24,410 | 2/2 (100%) | 70,394 | 1/2 (50%) | 22,007 |
| status-icon | 2 | 25,380 | 2/2 (100%) | 56,274 | 2/2 (100%) | 15,616 |
| dotted-path-type | 2 | 22,088 | 2/2 (100%) | 70,394 | 2/2 (100%) | 20,343 |
| publish-across-platforms | 5 | 29,344 | 5/5 (100%) | 68,705 | 5/5 (100%) | 23,487 |
| publish-bytes-no-root | 3 | 26,142 | 3/3 (100%) | 50,551 | 3/3 (100%) | 17,870 |
| stock-vs-custom | 2 | 22,637 | 2/2 (100%) | 35,754 | 2/2 (100%) | 21,928 |
| impersonate | 3 | 26,123 | 3/3 (100%) | 22,330 | 2/3 (67%) | 2,640 |
| create-a-person | 1 | 22,546 | 1/1 (100%) | 45,216 | 0/1 (0%) | 19,245 |
| sign-in-as-a-person | 4 | 24,054 | 4/4 (100%) | 22,330 | 4/4 (100%) | 2,640 |
| text-search | 2 | 22,854 | 2/2 (100%) | 37,636 | 2/2 (100%) | 21,765 |
| **all 13** | 36 | 317,561 | 35/36 (97%) | 658,826 | 33/36 (92%) | 238,937 |

mean tokens per task: index 24,428, doors 50,679, grep 18,380
doors: built

## What separates them

**The index is a floor.** `corpus/INDEX.md` is 20,572 tokens, so every `index` row is that number
plus 1,516 to 8,772 for the entries themselves. The entries a task needs are 6% to 30% of what the
strategy reads. Anything that replaces the index has that 20,572 to beat before it has saved
anything.

**The endpoints doors are larger than the index they replace.** `endpoints-Records` is 91,081 bytes
and `endpoints-Search` 65,073, so #56's own rule, split a door over 32 KB, already fires on Records,
Search and Schema. A plan that names `GET /entity/<type>` and `POST /entity/<type>/_search` opens
39,038 tokens of door before the map, the matrices and the phase are counted. Ten of the 13 plans
name a call in Records or Search.

**A plan naming a small family wins outright.** `impersonate` and `sign-in-as-a-person` name one
call in Session, which has 9 cards: 22,330 tokens at full door-tier recall against 26,123 and 24,054
for `index`, and 10,554 with the recipes door dropped. The layout does what it promises where the
family is small and inverts where it is not.

The misses:

| strategy | task | missed | why |
|---|---|---|---|
| `doors` | movie-link | `findings/013_upload_media` | the plan's phase is `read` and its calls are Records and Search. The rule is in an `upload` finding joined onto upload calls no plan holding "put the movie link in a CSV" would name |
| `grep` | entity-dict-name | `field_types/entity.md` | the card's tags are `dotted-field` and `entity-field`. The plan's `entity` matches neither |
| `grep` | impersonate, create-a-person | `entity_types/HumanUser.md` | tags `user`, `permission`, `sudo`. The plan holds the type name, which is the file name and not a tag |

Both `grep` misses are the same mechanism. The two matrices are addressed by file name, and the tag
rules in CLAUDE.md drop a tag restating the entry's own name, so a card named for a type or a
`data_type` carries no tag a caller holding that name can match. A frontmatter grep cannot reach
them at all; one over file names is a different strategy and nobody has measured it.

The `doors` miss is not the one #56 was written for. The join fixes a rule sitting in a sibling
entry that names the same call, which is #9 item 2. It does nothing for a rule behind a door the
plan never names, and that is what `movie-link` hits.

## Sensitivity

| `doors` variant | mean tokens per task | door-tier recall |
|---|---|---|
| as #56 specifies it | 50,679 | 35/36 (97%) |
| one call's block instead of the family (`--per-call`) | 40,946 | 33/36 (92%) |
| no recipes door (`--no-recipes`) | 38,903 | 35/36 (97%) |
| both | 29,170 | 33/36 (92%) |

Reading one call's block instead of the family costs `sign-in-as-a-person` two of its four entries:
the plan names `POST /auth/access_token`, and the two launcher cards are other calls in the same
family. Reading the family whole is what reaches a call the plan did not know to name, which is the
one thing the family door buys over a per-call file.

## Conclusion

The map holds: 1,491 tokens, and the door tier reaches 35 of 36 required rules without opening a
single entry. What the layout does not do on this corpus is read less. It beats `index` on 2 of 13
tasks as specified, and on 3 of 13 with both reductions applied, because the endpoint doors carry a
whole family and two families cover most of the API. #56 is a win on tokens only if the endpoint
doors are split, by method or by call, and the map names the split. The measurement to repeat after
that split is this one.

## Method faults, all mine

**`index` is scored with the answer key.** It reads exactly the entries a person said the task
needs, so it cannot miss, and the recall columns compare `doors` against `grep` rather than either
against `index`. An `index` arm that had to pick entries from 180 one-liners is a different
experiment and needs an agent to run it.

**The required sets are written after the fact.** Four of the nine issues were gaps when they were
filed, and the entry that answers each was written in response. This measures retrieval over a
corpus already shaped by these questions. It says nothing about a question nobody has asked yet,
which is the case a consumer meets first.

**The plan is the softest input here.** It is written by hand, it is what both blind strategies are
scored on, and a plan can be written to flatter one. `movie-link` misses under `doors` because its
plan names no upload call; a plan that named one would score 2 of 2. The only defence is that every
plan was written before the scorer ran, and that the plans are in `tasks.json` for anyone to argue
with.

**The doors do not exist.** They are built here from the sections #56 names, so the sizes are the
layout's rather than a generator's, and #57's 400-character bullet cap makes every number above an
upper bound.

**chars/4 is not a tokenizer.** Tables, code fences and JSON tokenize worse than prose, and the
entries hold more of all three than the doors do, so the entry tier is undercounted against the door
tier by an unmeasured amount.

**Recall is per entry, not per rule.** An entry counts as reached when its rule section was read,
not when the one rule the task needed was. A door carrying twelve bullets where the task needs the
third scores the same as one carrying the third alone, so nothing here measures whether a rule
survives being read inside 22,000 tokens of other rules. The weekly-report run is the standing
evidence that holding a fact is not using it.

**A door is charged whole.** A reader who greps inside a 91 KB file pays less than this says, and
`--per-call` is the only version of that priced.

**One author, one scorer, no second opinion** on any required set.

## After #56

Re-run on `dev` at `9569fc0`, the merge of #56, reading the generated `corpus/doors/`. Two things
changed between the built form above and this run, and both are in `score.py`.

**The scorer read no endpoint door on its first run against the real files.** It looked for
`endpoints-Search` while `probes/index.py` writes `endpoints-search`, and Records is split by method
because the family passed 32 KB. Every miss on that run was an entry sitting on an endpoint door, so
recall read as falling from 35 of 36 to 30. `door_name` now spells the file as the generator does.

**`follow` is a fourth strategy, and it is the map's own protocol.** `doors` reads every door the
plan names, whole. The map does not say that. It says: the endpoint door for the call, which is
verdicts; the group door row those verdicts name, which is one entry's rule block; the entry for a
transcript. Choosing rows from verdicts is judgment, so `follow` is given the required set for that
step the way `index` is, and its recall is scored one tier earlier: was the required entry's verdict
in front of the agent before it chose. `follow` also reads the rule block of every entity type and
data type the plan holds, since the map sends the agent there by name.

| strategy | reads | given |
|---|---|---|
| `index` | the map, then every required entry in full | the required set |
| `doors` | the map, then the doors the plan names, whole | the plan |
| `follow` | the map, the calls' endpoint doors, the plan's cards, then the rows the verdicts name | the plan, then the required set for the rows |
| `grep` | the rule section of every entry whose `endpoints:` or `tags:` match the plan | the plan |

`index` is no longer what an agent does: the map carries names and no verdicts, so nothing in it
picks an entry. Its number is the floor, what the corpus costs when the agent already knows the
entry. The comparison that matters is the built form's `index`, 24,428 mean, which was INDEX.md
whole and the required entries, against `follow` here.

| task | required | `index` tokens | `doors` recall | `doors` tokens | `follow` recall | `follow` tokens | `grep` recall | `grep` tokens |
|---|---|---|---|---|---|---|---|---|
| weekly-report | 6 | 8,042 | 6/6 (100%) | 39,458 | 5/6 (83%) | 13,051 | 6/6 (100%) | 26,685 |
| movie-link | 2 | 4,702 | 1/2 (50%) | 37,777 | 1/2 (50%) | 10,646 | 2/2 (100%) | 23,229 |
| attach-to-note | 2 | 3,698 | 2/2 (100%) | 22,503 | 1/2 (50%) | 6,966 | 2/2 (100%) | 21,518 |
| entity-dict-name | 2 | 5,895 | 2/2 (100%) | 37,777 | 2/2 (100%) | 11,361 | 1/2 (50%) | 22,018 |
| status-icon | 2 | 6,865 | 2/2 (100%) | 32,994 | 1/2 (50%) | 12,305 | 2/2 (100%) | 15,624 |
| dotted-path-type | 2 | 3,572 | 2/2 (100%) | 37,777 | 2/2 (100%) | 11,112 | 2/2 (100%) | 20,354 |
| publish-across-platforms | 5 | 10,831 | 5/5 (100%) | 40,066 | 5/5 (100%) | 16,066 | 5/5 (100%) | 23,499 |
| publish-bytes-no-root | 3 | 7,628 | 3/3 (100%) | 31,720 | 3/3 (100%) | 8,972 | 3/3 (100%) | 17,878 |
| stock-vs-custom | 2 | 4,122 | 2/2 (100%) | 24,466 | 2/2 (100%) | 7,532 | 2/2 (100%) | 21,938 |
| impersonate | 3 | 7,608 | 3/3 (100%) | 21,543 | 3/3 (100%) | 4,226 | 2/3 (67%) | 2,640 |
| create-a-person | 1 | 4,031 | 1/1 (100%) | 26,694 | 1/1 (100%) | 7,962 | 0/1 (0%) | 19,256 |
| sign-in-as-a-person | 4 | 5,539 | 4/4 (100%) | 21,543 | 4/4 (100%) | 4,730 | 4/4 (100%) | 2,640 |
| text-search | 2 | 4,339 | 2/2 (100%) | 24,891 | 2/2 (100%) | 7,756 | 2/2 (100%) | 21,775 |
| **all 13** | 36 | 76,872 | 35/36 (97%) | 399,209 | 32/36 (89%) | 122,685 | 33/36 (92%) | 239,054 |

| mean tokens per task | built form | generated doors |
|---|---|---|
| `index` | 24,428 | 5,913 |
| `doors` | 50,679 | 30,708 |
| `follow` | | 9,437 |
| `grep` | 18,380 | 18,389 |

The map is 7,721 bytes. `doors` reaches 35 of 36 with no judgment and costs more than the old index
did, because two calls are hubs: `POST /entity/<type>/_search` is named by 27 entries and
`GET /entity/<type>` by 22, ten of the thirteen plans name one of them, and a door row per entry is
the whole rule block. Following the map instead reads the 24 verdicts on the hub's door, about
1,200 tokens, and pays for rule blocks only where it chooses, which is where the cost went: 9,437
against 24,428 before, with the verdict of 32 of 36 required entries in front of the agent when it
chose.

The four `follow` misses are one shape. `013_upload_media` twice, `039_upload_silent_failures` and
`010_status_icons` are each on a door the plan did not name: the upload calls, and the render phase.
`weekly-report` and `movie-link` ask for a movie link and an attachment and their plans name no
`_upload` call. Whether an agent would name one before reading is the plan question already stated
under method faults, and the plans were not changed for this run.

`--per-call` prices nothing against generated doors. A door on disk is one file, and `assemble`
selects blocks only in the built form.
