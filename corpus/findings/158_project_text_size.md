---
tags: [custom-field, project, cost]
endpoints: [PUT /entity/<type>/<id>, GET /entity/<type>/<id>, POST /entity/<type>/_search, GET /entity/<type>, POST /schema/<Type>/fields, POST /schema/<Type>/fields/<field>, DELETE /schema/<Type>/fields/<field>]
phase: write
scope: api
measured: sandbox project written, 2026-11-17; one text field on Project, written on the sandbox Project and cleared; two runs
verdict: A custom text field on Project stored 1,000,000 characters of JSON byte for byte, `\n`, `\r\n` and tabs kept, with no refusal. Leading and trailing whitespace is stripped.
---

# 158_project_text_size

**Q** A custom text field on Project holding a JSON document: is a long string stored byte for byte,
newlines included, and up to what size?

**Endpoint** `PUT /entity/projects/<id> ; GET /entity/projects/<id> ; POST /entity/projects/_search`

**Docs claim** Silent on a length limit for `text`. `field_types/text` found none at 100,000 characters.

**Actual**

```
shapes, about 1.5 KB each, PUT then GET, _search and the PUT echo compared by SHA-256
  compact, \u escapes            PUT 200   1150 chars   all three equal
  compact, raw é 日本 🎬          PUT 200    994 chars, 1042 bytes   equal
  pretty, \n                     PUT 200   1439 chars   equal
  pretty, \r\n                   PUT 200   1518 chars   equal
  pretty, a literal tab per line PUT 200   1361 chars   equal
  pretty + trailing \n           PUT 200   1440 sent, 1439 read   sent '  }\n]\n', read '  }\n]'
  leading space + pretty         PUT 200   1440 sent, 1439 read   sent ' [\n  ', read '[\n  {'

size, pretty JSON with \n and some non-ASCII
  100,000 chars    102,000 bytes   PUT 200 in 0.4 s   GET, _search, echo equal
  500,000 chars    510,000 bytes   PUT 200 in 0.7 s   equal
  1,000,000 chars  1,020,000 bytes PUT 200 in 1.0 s   equal

with 1,000,000 chars stored, no fields named
  GET /entity/projects/<sandbox>             200, 1,175,336 bytes; 33 attributes, 9 relationships
  GET /entity/projects/<sandbox>?fields=name 200, 207 bytes
  GET /entity/projects?page[size]=100        200, 2,557 bytes; 22 rows, 0 attributes each
```

**Round trip**

| sent | read back |
|---|---|
| compact JSON, `\u` escapes or raw non-ASCII | identical |
| pretty JSON with `\n`, `\r\n` or tabs | identical |
| a trailing newline | stripped |
| a leading space | stripped |
| 100,000, 500,000, 1,000,000 characters | identical. No refusal, so no limit was reached |

The PUT's 200 body echoes the stored value, and `GET` and `_search` read the same string.

**Teaches**
- Write `JSON.stringify(value)` and parse what reads back. A serializer that ends in a newline gets
  one character fewer back: compare parsed values, not strings or hashes.
- 1,000,000 characters was a 200 in about a second. Nothing larger was sent, so a limit, if any, is above it.
- `GET /entity/projects/<id>` with no `fields` returns every field, a custom field of 1 MB included,
  while the listing `GET /entity/projects` with no `fields` returns ids only. Name `fields` on every
  read of a Project with a large field, or every client on the site pays for it.
