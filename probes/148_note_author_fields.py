"""Q: on a Note create, are `user` and `created_by` accepted, and what does a person's write record in
`created_by`, `updated_by` and `user`? The same for a Version.

sg-onset writes Notes and Versions with a person's own session (App Session Launcher, probe 052), never
a script key. The Note card records `user` and `created_by` as the script's `ApiUser` on a script
create; probe 052 asserted a person's bearer makes them the person without writing a row. The schema
says `user` is editable and `created_by` is not, and probe 070 found `created_at` honoured on create
against the same flag.

Callers:

    script   the ApiUser, `client_credentials`
    sudo     the script with `scope=sudo_as_login:<FPT_USER_LOGIN>` (probe 027)
    session  the bearer minted from `session_token.local.json` (probe 052 --login); only with --session

Per caller: a Note and a Version with no author fields, one with `user` = another person, one with
`created_by` = another person, read back. "Another person" is a test account sharing the operator's
email (`_people`).

Writes in the sandbox, behind `--write`: the Notes and Versions, deleted on exit.

    python probes/148_note_author_fields.py --write [--session]
"""
import base64
import json
import sys

import _lib
import _people
from sg_groundtruth.client import FPT

ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 148 writes; run with --write")
SB = _lib.sandbox_id(c, env)
P = {"type": "Project", "id": SB}
LOGIN = (env.get("FPT_USER_LOGIN") or "").strip()
SAVED = _lib.ROOT / "session_token.local.json"
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


def said(r):
    if r.ok:
        return str(r.status_code)
    try:
        e = r.json()["errors"][0]
        return f"{r.status_code} code {e.get('code')} {e.get('title')!r}"
    except (ValueError, KeyError, IndexError):
        return f"{r.status_code} {r.text}"


def claims(cl):
    """Who the bearer says it is (probe 027), decoded and never verified."""
    cl.request("GET", "/")
    p = cl._token.split(".")[1]
    j = json.loads(base64.urlsafe_b64decode(p + "=" * (-len(p) % 4)))
    return {k: j.get(k) for k in ("user", "auth_type", "sudo_as_login")}


me, LOGIN, aliases = _people.operator_and_aliases(c, env, SB, need=1)
other = aliases[0][0]
callers = [("script", c, None)]
if LOGIN:
    callers.append(("sudo", FPT.from_env(env, sudo_as_login=LOGIN), me))
if "--session" in sys.argv:
    if not SAVED.exists():
        out("session: no session_token.local.json; run probes/052_app_session_launcher.py --login first")
    else:
        tok = json.loads(SAVED.read_text())
        tok = tok.get("session_token") or tok.get("sessionToken") or tok
        callers.append(("session", FPT.from_session(env["FPT_API_SITE_URL"], tok), None))
else:
    out("session: not run; needs a person's launcher token, `052 --login` then `148 --write --session`")


def who(rel):
    d = (rel or {}).get("data") if isinstance(rel, dict) and "data" in rel else rel
    if not d:
        return "null"
    tag = "the caller" if d.get("id") == caller_id and d.get("type") == caller_type else (
        "the other person" if d.get("id") == other else "the script" if d.get("type") == "ApiUser" else "someone else")
    return f"{d.get('type')} ({tag})"


with _lib.Created(c) as made:
    for label, cl, cid in callers:
        cc = claims(cl)
        caller_type, caller_id = cc["user"]["type"], cc["user"]["id"]
        if label == "sudo":
            caller_type, caller_id = "HumanUser", cid
        out(f"\n===== {label}: bearer user {cc['user']['type']}, auth_type {cc['auth_type']}, "
            f"sudo_as_login {'set' if cc['sudo_as_login'] else None}")
        for slug, base in (("notes", {"subject": f"zzprobe_148 {label}"}),
                           ("versions", {"code": f"zzprobe_148 {label}"})):
            for case, extra in (("no author fields", {}),
                                ("user = another person", {"user": {"type": "HumanUser", "id": other}}),
                                ("created_by = another person", {"created_by": {"type": "HumanUser", "id": other}})):
                r = cl.post(f"/entity/{slug}", json={"project": P, **base, **extra})
                if r.status_code != 201:
                    out(f"  {slug[:-1]} {case}: {said(r)}")
                    continue
                rid = made.add(slug, r.json()["data"]["id"])
                rel = c.get(f"/entity/{slug}/{rid}", params={"fields": "user,created_by,updated_by"}).json()["data"]["relationships"]
                out(f"  {slug[:-1]} {case}: 201; created_by {who(rel.get('created_by'))}, "
                    f"updated_by {who(rel.get('updated_by'))}, user {who(rel.get('user'))}")
        r = cl.put(f"/entity/{slug}/{rid}", json={"description": "zzprobe_148 edit"})
        rel = c.get(f"/entity/{slug}/{rid}", params={"fields": "created_by,updated_by"}).json()["data"]["relationships"]
        out(f"  PUT description on that version: {said(r)}; updated_by {who(rel.get('updated_by'))}")
        r = cl.put(f"/entity/{slug}/{rid}", json={"created_by": {"type": "HumanUser", "id": me}})
        rel = c.get(f"/entity/{slug}/{rid}", params={"fields": "created_by"}).json()["data"]["relationships"]
        out(f"  PUT created_by on that version: {said(r)}; created_by {who(rel.get('created_by'))}")
    _lib.emit("148_note_author_fields", "\n".join(rows), env)
