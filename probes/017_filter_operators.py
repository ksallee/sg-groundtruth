"""Q: which filter operators does _search accept, and does an unsupported one fail or silently pass?

An entity picker with type-ahead over Shot codes wants a substring operator. The
danger is not a 400 — it is an operator that is ignored, which returns every row and looks like it works.
"""
import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
PROJ = ["project", "is", {"type": "Project", "id": PROJECT}]
rows = []


def search(entity, filt, size=500):
    r = c.post(f"/entity/{entity}/_search", headers=ARR,
               json={"filters": [PROJ] + filt, "fields": ["code"], "page": {"size": size}})
    if not r.ok:
        return f"ERR {r.status_code}", r.text[:120]
    return len(r.json()["data"]), None


shots = c.get("/entity/shots", params={"filter[project.Project.id]": PROJECT, "fields": "code",
                                       "page[size]": 5}).json()["data"]
_lib.note_from(shots)
codes = [s["attributes"]["code"] for s in shots]
shot_ids = [s["id"] for s in shots]
base_shots, _ = search("shots", [])
rows.append(f"baseline: {base_shots} shots in project; sample codes {codes[:3]}")

# Substrings of a real code. If an operator is ignored, the negative control returns the baseline.
code = codes[0]
mid, pre, suf = code[2:-2], code[:4], code[-4:]
rows.append(f"probe code {code!r} -> mid {mid!r} pre {pre!r} suf {suf!r}")

rows.append("\n=== operators on Shot.code  (positive / negative-control)")
rows.append(f"{'operator':<16}{'positive':<28}{'negative (must be 0)':<28}")
for op, pos, neg in [
    ("is",          code,   "ZZZNOPE"),
    ("is_not",      code,   None),
    ("contains",    mid,    "ZZZNOPE"),
    ("not_contains", mid,   None),
    ("starts_with", pre,    "ZZZNOPE"),
    ("ends_with",   suf,    "ZZZNOPE"),
]:
    p, pe = search("shots", [["code", op, pos]])
    n, ne = (search("shots", [["code", op, neg]]) if neg else ("-", None))
    verdict = ""
    if isinstance(n, int) and n == base_shots:
        verdict = "  <- IGNORED, returns baseline"
    rows.append(f"{op:<16}{str(p) + (' ' + (pe or '')):<28}{str(n) + (' ' + (ne or '')):<28}{verdict}")

rows.append("\n=== in / not_in with a scalar list")
for op in ("in", "not_in"):
    p, pe = search("shots", [["code", op, codes[:2]]])
    rows.append(f"  code {op} {codes[:2]} -> {p} {pe or ''}")
n, ne = search("shots", [["code", "in", ["ZZZNOPE1", "ZZZNOPE2"]]])
rows.append(f"  negative control code in [ZZZNOPE...] -> {n} {ne or ''}")

rows.append("\n=== in with entity hashes, on Version.entity")
base_v, _ = search("versions", [])
rows.append(f"  baseline versions: {base_v}")
for label, val in [("[{type,id} x2]", [{"type": "Shot", "id": i} for i in shot_ids[:2]]),
                   ("[{id} only x2]", [{"id": i} for i in shot_ids[:2]]),
                   ("[bare ids x2]",  shot_ids[:2])]:
    p, pe = search("versions", [["entity", "in", val]])
    rows.append(f"  entity in {label:<16} -> {p} {pe or ''}")
n, ne = search("versions", [["entity", "in", [{"type": "Shot", "id": 99999999}]]])
rows.append(f"  negative control entity in [{{Shot,99999999}}] -> {n} {ne or ''}")

rows.append("\n=== in on a dotted path through an entity field")
for label, filt in [("entity.Shot.code in [real x2]", [["entity.Shot.code", "in", codes[:2]]]),
                    ("entity.Shot.code in [ZZZNOPE]", [["entity.Shot.code", "in", ["ZZZNOPE"]]]),
                    ("entity.Shot.code contains mid", [["entity.Shot.code", "contains", mid]])]:
    p, pe = search("versions", filt)
    rows.append(f"  {label:<32} -> {p} {pe or ''}")

rows.append("\n=== an operator that does not exist (does it 400, or pass silently?)")
p, pe = search("shots", [["code", "definitely_not_an_operator", "x"]])
rows.append(f"  code definitely_not_an_operator x -> {p} {pe or ''}")

actual = "\n".join(rows)
_lib.emit("017_filter_operators", actual, env)
