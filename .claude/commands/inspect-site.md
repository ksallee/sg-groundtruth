---
description: Inspect one project and agree a site profile with the operator
---

Project (id, name, or nothing): $ARGUMENTS

`inspect_site.py` measures; you explain; the operator decides. Never write a profile they have not seen
the evidence for.

1. No project given: `python inspect_site.py`, then ask which one. Do not guess from the names.
2. `python inspect_site.py --project N --out <consumer>/profile.local.json`. For the ComfyUI node that
   is `../comfyui-flow-production-tracking/profile.local.json`.
3. Read the report back in plain language, in this order, and say what each number means:
   - **link**: what a Version hangs off here, and how often. A field filled 1% is not a convention.
   - **status**: how many the project hides, and which one new Versions will get.
   - **code**: the proposed default beside the real names it was drawn from.
   - **fields**: `identifier` means one value per row, so exposing it as a choice is useless;
     `no information` means one value, so it is not worth an input either. What is left is the shortlist.
4. Say plainly where it had no evidence: an empty `link` section is a guess, not a finding.
5. Existing profile values are kept and reported as `(yours, kept)`. Only re-run with `--overwrite`
   when the operator says to discard them.
6. Anything the operator wants that no field can hold is a field-creation job, not a profile edit:
   `comfyui-flow-production-tracking/src/comfyui_fpt/fields.py`, and read probe 019 first: a spent field name never frees.

The numbers come from probes 005, 007, 009, 018 and 020. Cite them when the operator asks why.
