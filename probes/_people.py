"""People probes 147 to 150 may address, assign and act as.

Addressing a Note to someone can mail them. A probe sends no mail to anyone but the operator, so the
only people it names are the operator (`FPT_USER_LOGIN`) and active accounts in the sandbox project
whose `email` is the operator's own: test accounts the operator made. Acting as them needs
`can_impersonate_this_user` (probe 027).
"""
import _lib

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


def operator_and_aliases(c, env, sandbox, need=2):
    """(operator id, operator login, [(id, login, permission group)]) of the aliases, by group name."""
    login = (env.get("FPT_USER_LOGIN") or "").strip()
    if not login:
        raise SystemExit("set FPT_USER_LOGIN in .env.local: the person this probe writes as")
    rows = c.post("/entity/human_users/_search", headers=ARR, json={
        "filters": [["sg_status_list", "is", "act"]],
        "fields": ["login", "email", "projects", "permission_rule_set", "can_impersonate_this_user"],
        "page": {"size": 500}}).json()["data"]
    me = next(r for r in rows if r["attributes"]["login"] == login)
    mail = (me["attributes"]["email"] or "").lower()
    aliases = []
    for r in rows:
        a, rel = r["attributes"], r["relationships"]
        if r["id"] == me["id"] or (a.get("email") or "").lower() != mail or not a.get("can_impersonate_this_user"):
            continue
        if not any(p["id"] == sandbox for p in rel["projects"]["data"] or []):
            continue
        aliases.append((r["id"], a["login"], (rel["permission_rule_set"]["data"] or {}).get("name")))
        _lib.note_names(a["login"])
    if len(aliases) < need:
        raise SystemExit(f"needs {need} active, impersonatable accounts in the sandbox project sharing the "
                         f"operator's email; found {len(aliases)}")
    return me["id"], login, sorted(aliases, key=lambda x: (x[2] != "Artist", x[0]))
