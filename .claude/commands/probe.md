---
description: Write and run a probe answering one question about the Flow PT REST API
---

Question: $ARGUMENTS

1. Next free number in `probes/`.
2. Write `probes/NNN_slug.py` using `_lib`: one question. Read-only unless the question needs `--write`.
3. Run it. A probe **prints**; it never writes the corpus. Call `_lib.emit(slug, report, env)` last.
4. Read the output. Judge what is identifying and write `corpus/findings/NNN_slug.md` yourself, to the
   template below.
5. `python probes/check_corpus.py` then `python probes/index.py`.
6. Report the verdict in one line. Do not restate the file.

## Redaction

`_lib.scrub` already replaced the site URL, script name, key, home directory, emails, bearer tokens and
presigned URLs. Those are string replacements that cannot misfire. **Everything else is your judgment**,
and the probe lists its candidates under `identifying, replace with a placeholder`.

Replace names with a generic stand-in that keeps the shape: projects `demo_show`, shots `sh010`, assets
`charA`, sequences `seq01`, users `<user>`, storage roots `/mnt/projects`. Never invent a plausible-looking
real name. A placeholder must read as a placeholder.

**Never rewrite an API error message, a MIME type, a field name or a file extension.** Those are the
teaching content. An earlier auto-redactor turned `application/vnd+shotgun.api3_array+json` into
`eddy/xenon+pylon.thicket3_array+json` inside the finding that exists to teach that string, and told a
recipe to upload `render.quill`.

## Never truncate an error body

Slicing an error to `title[:70]` cuts exactly the part worth having. Probe 017 recorded a bogus operator as
a 120-char stub for months; read in full, the same 400 enumerates every legal relation for that data type:

    Valid relations: ["contains","not_contains","is","is_not","starts_with","ends_with","in","not_in"]

The API documents itself in its rejections. Print the whole `errors[]` object, `source` included, and trim in
the finding, where a reader can see what was cut, not at the point of capture.

## Finding template

```markdown
---
tags: [reuse an existing tag from corpus/INDEX.md; singular, lowercase]
verdict: One sentence, 200 chars max. The actionable rule, not the story.
---

# NNN_slug

**Q** The single question, as a question.

**Endpoint** `GET /entity/versions ; POST /entity/versions/_search`

**Docs claim** What the public REST docs say, in one line. Say if they are silent.

**Actual**

```
Real output. 30 lines max: representative rows, not exhaustive ones. Cut a repeating
block to three lines and a count. Keep every error message verbatim.
```

**Teaches**
- The trap, the rule, or the cost. One line each, 2-4 of them.
- Where a long verdict goes. Cite another probe as `probe 004` when it corrects one.
```

`check_corpus.py` enforces the sections, the verdict cap and the output cap. Green is the bar.

Add `**Python equivalent**` with a `shotgun_api3` snippet when the mapping is non-obvious. TDs read Python.

Schema-writing probes use `sg_zzprobe_<nnn>_*`. See the litter warning in `docs/quirks.md`.

## Field-type findings

Every `data_type` behaves differently across read, write, clear and filter, and there is no generic path.
That knowledge is a matrix, not a sequence, so it is addressed by type rather than by probe number:
`probes/field_types/<type>.py` -> `corpus/findings/field_types/<type>.md`. Numbered probes stay the
chronological log, where a later finding corrects an earlier one; the matrix is revised cell by cell.

Delete what you create. Wrap writes in `_lib.Created(c)` and `add(slug, id)` every row; it deletes them in
reverse on exit. A probe that leaves rows behind changes what the next probe measures.

Test on **stock fields** the site already has. Creating a field burns its name permanently (probe 019), so
create one only when the site has no editable field of that type, and then use `sg_zzprobe_<type>_*`.

Writes go only into the sandbox project, behind `--write`. The read-only half, schema inspection and the
operator list, must run ungated, so the probe is useful without touching anything.

**The API enumerates its own operators.** Send a deliberately bogus operator and the 400 names every legal
one for that data type (probe 017). Do that first; it is cheaper and more complete than guessing:

    [["<field>", "definitely_not_an_operator", null]]
    -> 400  ... Valid relations: ["contains","not_contains","is","is_not","starts_with","ends_with","in","not_in"]

```markdown
---
tags: [field-type, …; reuse tags from corpus/INDEX.md]
verdict: One sentence, 200 chars max. The thing that surprises someone assuming this type behaves like text.
---

# <type>

**Data type** `date`, probed on `Shot.sg_turnover_date` (stock, editable)

**Read** The exact shape, and whether it is returned under `attributes` or `relationships`.

**Write**

| sent | result |
|---|---|
| `"2026-09-02"` | 200, stored as sent |
| `"2026-09-02T00:00:00Z"` | 400 `Invalid date format: ... Correct format is: 2011-01-21` |
| `20260902` | 400 `expected [String, NilClass] data type(s) but got Integer` |

**Clear**

| sent | result |
|---|---|
| `null` | cleared |
| `""` | 200, stored as `null` |
| key omitted from the PUT | unchanged |

**Filter** The `Valid relations` list verbatim, then one row per operator: the value shape it takes and
what it matches. Include the negative control that returns 0.

| operator | value shape | matches |
|---|---|---|
| `is` | `"2026-09-02"` | exact date |
| `between` | `["2026-01-01", "2026-12-31"]` | inclusive both ends |
| `in_last` | `[7, "DAY"]` | unit must be uppercase |

**Traps** 2-4 bullets. Anything that fails silently, or differs from what a text field would do.
```

120 lines max: a reference card, not a transcript. `check_corpus.py` enforces it.

## Register

The corpus is public documentation and competes with the official docs. Read the **Style** section of
`CLAUDE.md` before writing prose. `check_corpus.py` rejects the banned register and ALL-CAPS emphasis
mechanically; the rest is judgment. State the fact, once, with the number and the error string verbatim.

## Entity-type findings

One card per standard entity type: `probes/entity_types/<Type>.py` ->
`corpus/findings/entity_types/<Type>.md`, named for the schema name (`Version`, `PublishedFile`).

**Standard types only.** A custom entity is site configuration: its slot number, its display name and its
fields belong in the reader's own `corpus.local/` overlay, never in the shipped corpus. `008_custom_entities`
covers how to resolve them generically, which is the portable part.

Field censuses, row counts and which custom fields exist are site measurements. Attribute them inline,
beginning "On the probed site, ...". What a stock field is called and how the type is addressed are portable.

```markdown
---
tags: [entity-type, …; reuse tags from corpus/INDEX.md]
scope: api
verdict: One sentence, 200 chars max. The thing a client gets wrong about this type.
---

# Version

**Type** Schema name, REST path slug, and whether it is project-scoped or site-wide.

**Identity** The field a human reads as its name, and what is unique. `code`, `content` and `name` are all
used by different types, and guessing wrong is the first thing that breaks.

**Create** What the server actually requires, which is not the same as what the schema flags mandatory
(probe 012). One row per attempt: body sent, result.

**Links** Its entity and multi_entity fields, their `valid_types`, and which one a client actually uses.
Cite `field_types/entity` and `field_types/multi_entity` rather than restating them.

**Status** The status field if it has one, and its vocabulary. Say "none" if it has none.

**Traps** 2-4 bullets. What is read only, what is server managed, what a caller assumes and gets wrong.
```

45 lines of prose maximum; tables and evidence do not count.
