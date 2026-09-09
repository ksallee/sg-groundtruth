"""Q: does anything in /schema/<Type>/fields separate a field the site added from a stock one?

A client deciding "can I depend on this field existing on someone else's site" has been reading the
`sg_` prefix, and the prefix is wrong in both directions: `sg_status_list` and `sg_uploaded_movie` are
stock on every site, and probe 019 shows a created field is named `sg_<display name>` whatever the
caller passes. Read-only: seven types, every field, every schema key that could carry the answer.
"""
import json
from collections import Counter

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

TYPES = ["PublishedFile", "Version", "Shot", "Task", "Asset", "Project", "HumanUser"]
# Stock fields whose name carries the prefix. Named here so the tally can point at them.
KNOWN_STOCK_SG = ("sg_status_list", "sg_uploaded_movie")

# 1. every key the schema puts on a field, and which of them vary with a boolean shape.
f = c.get("/schema/PublishedFile/fields").json()["data"]
rows.append(f"=== /schema/PublishedFile/fields -> {len(f)} fields")
sample = f["code"]
rows.append("  keys on one field: " + json.dumps(sorted(sample)))
rows.append("  code:        " + json.dumps({k: v for k, v in sample.items()
                                            if k not in ("properties",)}))
rows.append("  visible on a stock field:  " + json.dumps(f["sg_status_list"]["visible"]))
rows.append("  editable on a stock field: " + json.dumps(f["sg_status_list"]["editable"]))

totals = Counter()
for t in TYPES:
    fields = c.get(f"/schema/{t}/fields").json()["data"]
    ed = {n: d for n, d in fields.items() if (d.get("visible") or {}).get("editable") is True}
    sg = {n for n in fields if n.startswith("sg_")}
    rows.append(f"\n=== {t}: {len(fields)} fields, {len(ed)} with visible.editable true, "
                f"{len(sg)} named sg_*")
    rows.append(f"  visible.editable true: {sorted(ed)}")
    rows.append(f"  sg_* and NOT visible.editable: {sorted(sg - set(ed))}")
    rows.append(f"  visible.editable true and NOT sg_*: {sorted(set(ed) - sg)}")
    # visible.value and editable.editable, in case either separates the same way
    vis_ed = {n for n, d in fields.items() if (d.get("visible") or {}).get("value") is False}
    ed_ed = {n for n, d in fields.items() if (d.get("editable") or {}).get("editable") is True}
    rows.append(f"  visible.value false: {len(vis_ed)}   editable.editable true: {len(ed_ed)}"
                + (" (same set as visible.editable)" if ed_ed == set(ed) else ""))
    totals["fields"] += len(fields)
    totals["editable"] += len(ed)
    totals["sg"] += len(sg)
    totals["sg_not_editable"] += len(sg - set(ed))
    totals["editable_not_sg"] += len(set(ed) - sg)

rows.append("\n=== across the seven types")
rows.append(f"  {dict(totals)}")
for n in KNOWN_STOCK_SG:
    d = c.get(f"/schema/Version/fields/{n}").json()["data"]
    rows.append(f"  Version.{n}: visible={json.dumps(d['visible'])} "
                f"editable={json.dumps(d['editable'])} data_type={d['data_type']['value']}")

# The four that break the sg_ correlation, in full, so the finding can name rather than count them.
rows.append("\n=== the fields with visible.editable true and no sg_ prefix")
for t, n in (("Version", "platform_status"), ("Shot", "platform_status"),
             ("Version", "version_sg_ai_generated_from_versions"), ("Project", "code")):
    d = c.get(f"/schema/{t}/fields/{n}").json()["data"]
    rows.append(f"  {t}.{n}: data_type={d['data_type']['value']!r} "
                f"name={d['name']['value']!r} mandatory={d['mandatory']['value']} "
                f"description={d['description']['value']!r}")

_lib.emit("056_stock_vs_custom_field", "\n".join(rows), env)
