---
description: Record a verified call and its real response into the corpus
---

Task: $ARGUMENTS

1. Read `corpus/INDEX.md`. If a recipe already covers this, stop and say so.
2. Write a probe that performs the task for real against the site. Read-only unless the task needs `--write`.
3. Run it, then write `corpus/recipes/NNN_slug.md` by hand — intent, the exact call, the actual response,
   and every gotcha hit on the way. The gotchas are the point; a call that worked first time teaches a
   model nothing it did not know.
4. Carry a `measured:` key, from the line `_lib.emit` prints. A recipe demonstrated on three rows the
   probe made in the sandbox is weaker evidence than one run against a real show, and the reader deciding
   whether to trust it cannot tell the two apart otherwise.
5. Redact by the rules in `.claude/commands/probe.md`. A recipe is executable, so a mangled filename or
   MIME type is worse here than anywhere else in the corpus.
6. `python probes/check_corpus.py` then `python probes/index.py`.
7. Report the intent and one gotcha. Nothing else.
