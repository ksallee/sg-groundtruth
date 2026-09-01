"""Q: which Version fields are actually populated on a real project?"""
import _lib

env = _lib.load_env()
c = _lib.client()
BBB, N = 70, 100

names = sorted(c.get("/schema/Version/fields", params={"project_id": BBB}).json()["data"])
r = c.get("/entity/versions", params={"filter[project.Project.id]": BBB,
                                      "fields": ",".join(names), "sort": "-id", "page[size]": N})
rows = r.json()["data"]
n = len(rows)

filled = {f: 0 for f in names}
for row in rows:
    for f in names:
        v = row.get("attributes", {}).get(f)
        if v in (None, "", [], {}):
            v = (row.get("relationships", {}).get(f) or {}).get("data")
        if v not in (None, "", [], {}):
            filled[f] += 1

ranked = sorted(filled.items(), key=lambda kv: -kv[1])
used = [f"  {f:<38} {ct:>3}/{n}" for f, ct in ranked if ct]
dead = [f for f, ct in ranked if not ct]

actual = (f"sample: {n} most recent Versions on project {BBB}; {len(names)} fields in schema\n\n"
          f"populated ({len(used)}):\n" + "\n".join(used) +
          f"\n\nnever populated ({len(dead)}):\n  " + ", ".join(dead))

_lib.record("007_fill_rates", "GET /schema/Version/fields + GET /entity/versions",
            "Schema lists what is possible; only a subset is ever filled.",
            actual,
            f"Of {len(names)} Version fields in the schema, {len(used)} carry data on BBB and {len(dead)} are "
            f"never populated - rank by fill rate, never expose the schema wholesale. CAVEAT: booleans read as "
            f"100% filled because False is not null, so the inspector must exclude checkbox fields from fill "
            f"ranking or use the schema data_type to weight them.",
            env, tags=("version", "inspector", "schema", "fill-rate"))
print(actual[:1600])
