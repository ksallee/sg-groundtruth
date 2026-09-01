---
description: Record a verified call and its real response into the corpus
---

Task: $ARGUMENTS

1. Read `corpus/INDEX.md`. If a recipe already covers this, stop and say so.
2. Write a probe that performs the task for real against the site. Read-only unless the task needs `--write`.
3. Record it with `_lib.record_recipe` — intent, the exact call, the actual response, and every gotcha hit on
   the way. The gotchas are the point; a call that worked first time teaches a model nothing it did not know.
4. `python probes/index.py`.
5. Report the intent and one gotcha. Nothing else.
