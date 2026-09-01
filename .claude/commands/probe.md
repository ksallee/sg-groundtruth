---
description: Write and run a probe answering one question about the Flow PT REST API
---

Question: $ARGUMENTS

1. Next free number in `probes/`.
2. Write `probes/NNN_slug.py` using `_lib` — one question. Read-only unless the question needs `--write`.
3. Run it.
4. Fill the real verdict: one actionable sentence, because it lands in `INDEX.md` and is often all an agent
   reads. Say where the docs were wrong. Tag for retrieval.
5. Add `python_equivalent=` when the `shotgun_api3` mapping is non-obvious — TDs read Python.
6. `python probes/index.py`.
7. Report the verdict in one line. Do not restate the file.

Schema-writing probes use `sg_zzprobe_<nnn>_*`. See the litter warning in `docs/quirks.md`.
