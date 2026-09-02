"""Q: how do you list the projects a human would actually pick from?

The node's project picker showed template and demo projects alongside real ones. The obvious filter is
sg_status is Active — this checks whether that is safe.
"""
import _lib

env = _lib.load_env()
c = _lib.client()
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
rows = []

f = c.get("/schema/Project/fields").json()["data"]
rows.append("candidate fields on Project:")
for name in ("sg_status", "archived", "is_template", "is_demo", "is_template_project"):
    if name not in f:
        rows.append(f"  {name:<22} ABSENT")
        continue
    props = f[name].get("properties", {})
    rows.append(f"  {name:<22} {f[name]['data_type']['value']:<10} "
                f"valid={props.get('valid_values', {}).get('value')} "
                f"display={props.get('display_values', {}).get('value')}")

r = c.get("/entity/projects", params={"fields": "name,sg_status,archived,is_template,is_demo",
                                      "page[size]": 500})
data = r.json()["data"]
_lib.register_from(r.json())
total = len(data)


def tally(key):
    out = {}
    for x in data:
        out[str(x["attributes"].get(key))] = out.get(str(x["attributes"].get(key)), 0) + 1
    return out


rows.append(f"\n{total} projects on the site")
for k in ("sg_status", "archived", "is_template", "is_demo"):
    rows.append(f"  {k:<14} {tally(k)}")

rows.append("\nsg_status is NULL on real, in-use projects — it is not a liveness flag:")
nulls = [x for x in data if x["attributes"].get("sg_status") is None
         and not x["attributes"].get("is_template")]
rows.append(f"  {len(nulls)} of {total} have no status and are not templates")


def count(filt):
    r = c.post("/entity/projects/_search", headers=ARR,
               json={"filters": filt, "fields": ["name"], "page": {"size": 500}})
    return len(r.json()["data"]) if r.ok else f"ERR {r.status_code} {r.text[:80]}"


rows.append("\nfilter results:")
for label, filt in [
    ("no filter", []),
    ('sg_status is Active', [["sg_status", "is", "Active"]]),
    ('is_template is False', [["is_template", "is", False]]),
    ('is_demo is False', [["is_demo", "is", False]]),
    ('archived is False', [["archived", "is", False]]),
    ('not template AND not archived', [["is_template", "is", False], ["archived", "is", False]]),
    ('not template AND not demo AND not archived',
     [["is_template", "is", False], ["is_demo", "is", False], ["archived", "is", False]]),
]:
    rows.append(f"  {label:<44} -> {count(filt)}")

actual = "\n".join(rows)
_lib.record("018_project_listing", "GET /entity/projects ; POST /entity/projects/_search",
            "sg_status marks a project Active.",
            actual,
            "DO NOT filter a project picker on sg_status. Its valid values are Bidding/Active/Lost/Hold "
            "with NO display_values, and it is null on most real projects - on this site 10 of 22, "
            "including freshly created ones, so 'sg_status is Active' hides working projects. The "
            "reliable discriminators are the checkboxes: is_template is True for exactly the stock "
            "templates, is_demo for the shipped demo show, archived for retired ones. Filter "
            "is_template/is_demo/archived is False and leave sg_status alone; a new project has no "
            "status until someone sets one.",
            env, tags=("project", "query", "filter", "inspector", "list-field", "trap"))
print(actual)
