"""Entity type `HumanUser`: how a person is identified, what a create costs, and what a delete leaves.

The corpus leans on this type everywhere (`created_by`, `Version.user`, task assignees, followers,
impersonation) and has never measured it. Three questions the other probes left open: whether
`sudo_as_login` takes the login or the email, whether an empty `projects` means site-wide access or
none, and whether a HumanUser can be created over REST at all and what it does to the licence.

Read-only by default. `--write` creates one HumanUser and deletes it again, which the operator asked
for explicitly: a seat count only moves when a row is really made. The login is `zzprobe_054_user`
and the email is under `example.invalid`, a reserved domain, so no invitation can reach anyone.
"""
import json
import sys
from collections import Counter
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import _lib  # noqa: E402

env = _lib.load_env()
c = _lib.client()
site = env["FPT_API_SITE_URL"].rstrip("/")
SCRIPT = env["FPT_API_SCRIPT_NAME"]
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}
SLUG = "human_users"
LOGIN = "zzprobe_054_user"
EMAIL = "zzprobe_054@example.invalid"
# The minimum body the site accepts, found below: a create defaults to `act` and is refused there.
MIN = {"login": LOGIN, "email": EMAIL, "sg_status_list": "dis"}
rows = []


def errs(r):
    """The whole errors[] object, `source` included. The 400 is the documentation (probe 017)."""
    try:
        return json.dumps(r.json().get("errors", r.json()))
    except ValueError:
        return r.text[:400]


def token(**data):
    return requests.post(f"{site}/api/v1/auth/access_token", data=data,
                         headers={"Accept": "application/json"}, timeout=30)


def as_user(subject):
    """A bearer acting as one HumanUser, or the refusal."""
    return token(grant_type="client_credentials", client_id=SCRIPT,
                 client_secret=env["FPT_API_API_KEY"], scope=f"sudo_as_login:{subject}")


def get_as(tok, path, **params):
    return requests.get(f"{site}/api/v1{path}", timeout=60, params=params or None,
                        headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})


def search(entity, filters, fields, size=500):
    return c.post(f"/entity/{entity}/_search", headers=ARR,
                  json={"filters": list(filters), "fields": list(fields), "page": {"size": size}})


def seats():
    """The two calls that report what a user costs. Neither is a row count."""
    lic = c.get("/license_info")
    sub = c.get("/subscription_seat/user_subscriptions")
    lic_d = lic.json().get("data") if lic.ok else errs(lic)
    sub_d = sub.json() if sub.ok else errs(sub)
    n = len(sub_d) if isinstance(sub_d, dict) else "?"
    return lic.status_code, lic_d, sub.status_code, n, (sub_d if isinstance(sub_d, dict) else {})


def report_seats(label, before_keys=None):
    ls, ld, ss, n, hash_ = seats()
    extra = ""
    if before_keys is not None:
        extra = f"  new keys {sorted(set(hash_) - set(before_keys))}"
    rows.append(f"  {label:<26} /license_info {ls} {json.dumps(ld)}   "
                f"/subscription_seat/user_subscriptions {ss}, {n} keys{extra}")
    return hash_


# ---------------------------------------------------------------- path and scope
rows.append("=== path slug and scope")
for path in ("/entity/human_users", "/entity/HumanUser", "/entity/humanusers", "/entity/users"):
    r = c.get(path, params={"fields": "id", "page[size]": 1})
    rows.append(f"  GET {path:<24} -> {r.status_code}"
                + (f"  type={(r.json()['data'] or [{}])[0].get('type')}" if r.ok
                   else "  " + errs(r)))

fields = c.get("/schema/HumanUser/fields").json()["data"]
rows.append(f"  /schema/HumanUser/fields -> {len(fields)} fields, "
            f"{sum(1 for f in fields.values() if f['editable']['value'])} editable")
rows.append(f"  'project' in HumanUser's own fields: {'project' in fields}  "
            f"(site-wide if False)")


def prop(f, key, default=None):
    p = (fields.get(f) or {}).get(key)
    return (p or {}).get("value", default) if isinstance(p, dict) else default


def dtype(f):
    return prop(f, "data_type")


def props(f, name, default=None):
    p = (fields.get(f) or {}).get("properties", {}).get(name)
    return (p or {}).get("value", default) if isinstance(p, dict) else default


# ---------------------------------------------------------------- identity
rows.append("\n=== identity: the name-ish fields, and what each is flagged")
rows.append("  field                        data_type      editable mandatory unique")
for f in ("login", "email", "name", "firstname", "lastname", "code",
          "cached_display_name", "sg_status_list", "password_proxy"):
    if f not in fields:
        rows.append(f"  {f:<28} absent from /schema/HumanUser/fields")
        continue
    rows.append(f"  {f:<28} {str(dtype(f)):<14} {str(prop(f, 'editable')):<8} "
                f"{str(prop(f, 'mandatory')):<9} {prop(f, 'unique')}")

rows.append("\n  which name-ish field a filter accepts:")
for f in ("login", "email", "name", "code", "firstname"):
    r = search(SLUG, [[f, "is", "definitely_not_a_user_zz"]], ["login"], size=1)
    rows.append(f"  filter [{f!r}, 'is', ...] -> {r.status_code} "
                + (f"{len(r.json()['data'])} row(s)" if r.ok else errs(r)))

# `name` is not a stored field on most types. Ask whether it is readable even so.
r = c.get(f"/entity/{SLUG}", params={"fields": "login,email,name,firstname,lastname", "page[size]": 1})
if r.ok and r.json()["data"]:
    a = r.json()["data"][0]["attributes"]
    _lib.note_from(r.json())
    rows.append(f"  one row, fields=login,email,name,firstname,lastname -> keys {sorted(a)}")

# ---------------------------------------------------------------- the visibility fields
rows.append("\n=== the fields that decide what a person sees")
for f in ("permission_rule_set", "groups", "projects", "can_impersonate_this_user",
          "sg_status_list", "locked_until"):
    if f not in fields:
        rows.append(f"  {f:<28} absent")
        continue
    rows.append(f"  {f:<28} {str(dtype(f)):<14} editable={prop(f, 'editable')}  "
                f"valid_types={props(f, 'valid_types')}")

rows.append("  every entity and multi_entity field on the type:")
for f in sorted(fields):
    if dtype(f) in ("entity", "multi_entity"):
        vt = props(f, "valid_types") or []
        # image_source_entity names every type on the site; the count is the content there.
        shown = vt if len(vt) <= 8 else f"{len(vt)} types, every one on the site"
        rows.append(f"  {f:<34} {str(dtype(f)):<13} editable={str(prop(f, 'editable')):<6} {shown}")

sl = c.get("/schema/HumanUser/fields/sg_status_list")
if sl.ok:
    d = sl.json()["data"]
    rows.append(f"  sg_status_list valid_values {d['properties']['valid_values']['value']}  "
                f"default {d['properties']['default_value']['value']!r}  "
                f"display_values {d['properties'].get('display_values', {}).get('value')}")

users = c.get(f"/entity/{SLUG}", params={
    "fields": "login,email,sg_status_list,permission_rule_set,groups,projects,"
              "can_impersonate_this_user", "page[size]": 500}).json()["data"]
_lib.note_from(users)
rows.append(f"  /entity/{SLUG} -> {len(users)} rows")


def relcount(u, f):
    return len((u["relationships"].get(f, {}) or {}).get("data") or [])


rows.append("  sg_status_list: " + json.dumps(dict(Counter(
    u["attributes"]["sg_status_list"] for u in users))))
rows.append("  projects list length: " + json.dumps(dict(Counter(
    relcount(u, "projects") for u in users))))
rows.append("  can_impersonate_this_user: " + json.dumps(dict(Counter(
    u["attributes"]["can_impersonate_this_user"] for u in users))))
rows.append("  login == email on: "
            f"{sum(1 for u in users if u['attributes']['login'] == u['attributes']['email'])} "
            f"of {len(users)} rows")

# ---------------------------------------------------------------- sudo: login or email
rows.append("\n=== sudo_as_login: which of login and email the scope takes")
def live(u):
    return (u["attributes"]["can_impersonate_this_user"]
            and u["attributes"]["sg_status_list"] == "act")


# A subject whose email is a real address and is not the login, so the two are distinguishable.
cands = [u for u in users if live(u) and "@" in (u["attributes"]["email"] or "")
         and u["attributes"]["login"] != u["attributes"]["email"]]
same = [u for u in users if live(u) and u["attributes"]["login"] == u["attributes"]["email"]]
if not cands:
    rows.append("  no active impersonable user whose login differs from its email; not measured here")
for label, u in (("login differs from email", cands[0] if cands else None),
                 ("login is the email", same[0] if same else None)):
    if not u:
        continue
    lg, em = u["attributes"]["login"], u["attributes"]["email"]
    rows.append(f"  subject where the {label}:")
    for what, value in (("login", lg), ("email", em)):
        r = as_user(value)
        body = "200, claim sudo_as_login set to what was sent" if r.ok else errs(r)
        # The API echoes the subject back inside the message. A login is not an email, so the
        # shared scrubber cannot catch it; the probe knows what it sent and replaces it here.
        rows.append(f"    scope=sudo_as_login:<{what}> -> {r.status_code} "
                    f"{body.replace(lg, '<login>')}")

# ---------------------------------------------------------------- empty projects
rows.append("\n=== does an empty `projects` mean site-wide or none?")
total = len(c.get("/entity/projects", params={"fields": "id", "page[size]": 500}).json()["data"])
rows.append(f"  the script user reads {total} projects")
rows.append("  user                 permission_rule_set  HumanUser.projects  Project.users  reads")
seen = set()
for u in users:
    if not live(u):
        continue
    pset = (u["relationships"]["permission_rule_set"]["data"] or {}).get("name")
    n_field = relcount(u, "projects")
    if (pset, n_field > 0) in seen:
        continue
    seen.add((pset, n_field > 0))
    # The other side of the same link: projects whose `users` names this person.
    back = search("projects", [["users", "is", {"type": "HumanUser", "id": u["id"]}]], ["id"])
    n_back = len(back.json()["data"]) if back.ok else back.status_code
    r = as_user(u["attributes"]["login"])
    if not r.ok:
        n_seen = f"sudo refused {r.status_code}"
    else:
        got = get_as(r.json()["access_token"], "/entity/projects",
                     **{"fields": "id", "page[size]": 500})
        n_seen = len(got.json().get("data", [])) if got.ok else got.status_code
    rows.append(f"  <user>               {str(pset):<20} {n_field:>18} {str(n_back):>14}  "
                f"{n_seen} of {total}")
    # Where a person reads fewer projects than the site has, say what the subset is made of.
    if r.ok and isinstance(n_seen, int) and n_seen < total:
        mine = get_as(r.json()["access_token"], "/entity/projects",
                      **{"fields": "is_template,is_demo,archived", "page[size]": 500}).json()["data"]
        allp = c.get("/entity/projects", params={
            "fields": "is_template,is_demo,archived", "page[size]": 500}).json()["data"]

        def flags(rowset):
            return dict(Counter(
                "".join(letter for k, letter in (("is_template", "template"),
                                                 ("is_demo", "demo"), ("archived", "archived"))
                        if p["attributes"].get(k)) or "plain" for p in rowset))

        extra = sorted({p["id"] for p in mine} - {p["id"] for p in allp})
        rows.append(f"    the {n_seen} it reads: {json.dumps(flags(mine))}   "
                    f"all {total}: {json.dumps(flags(allp))}   "
                    f"in its listing and not in the script user's: {len(extra)}")

# ---------------------------------------------------------------- create and delete
rows.append("\n=== create over REST" + ("" if _lib.writes_allowed() else "  (skipped: no --write)"))
if _lib.writes_allowed():
    prs = c.get("/entity/permission_rule_sets",
                params={"fields": "code,entity_type", "page[size]": 100}).json()["data"]
    _lib.note_from(prs)
    PRS = next((p["id"] for p in prs if p["attributes"]["entity_type"] == "HumanUser"), None)
    before = report_seats("before any create")
    with _lib.Created(c) as made:
        new_id = None
        for label, body in (("{}", {}),
                            ("login", {"login": LOGIN}),
                            ("login + email", {"login": LOGIN, "email": EMAIL}),
                            ("login + email + names",
                             {"login": LOGIN, "email": EMAIL,
                              "firstname": "zzprobe", "lastname": "054"}),
                            # The refusal names promotion to *active*, and a create defaults to
                            # sg_status_list 'act'. Ask for a disabled row instead.
                            ("login + email + status dis",
                             {"login": LOGIN, "email": EMAIL, "sg_status_list": "dis"}),
                            ("login + email + names + status dis",
                             {"login": LOGIN, "email": EMAIL, "sg_status_list": "dis",
                              "firstname": "zzprobe", "lastname": "054"}),
                            ("the same, plus a permission_rule_set",
                             {"login": LOGIN, "email": EMAIL, "sg_status_list": "dis",
                              "permission_rule_set": {"type": "PermissionRuleSet", "id": PRS}})):
            if new_id:
                break
            r = c.post(f"/entity/{SLUG}", json=body)
            rows.append(f"  POST body {label:<22} -> {r.status_code} "
                        + ("created" if r.ok else errs(r)))
            if r.ok:
                new_id = made.add(SLUG, r.json()["data"]["id"])

        if new_id:
            r = c.get(f"/entity/{SLUG}/{new_id}", params={
                "fields": "login,email,name,firstname,lastname,sg_status_list,"
                          "permission_rule_set,projects,groups,can_impersonate_this_user"})
            d = r.json()["data"]
            rows.append(f"  GET /entity/{SLUG}/<new id> -> {r.status_code} "
                        f"attributes {json.dumps(d['attributes'])}")
            rows.append("    relationships "
                        + json.dumps({k: (v or {}).get("data")
                                      for k, v in d["relationships"].items()}))
            report_seats("after the create", before)

            r = c.put(f"/entity/{SLUG}/{new_id}", json={"can_impersonate_this_user": True})
            rows.append(f"  PUT can_impersonate_this_user -> {r.status_code} "
                        + ("ok" if r.ok else errs(r)))
            # The create is refused at 'act'. Whether an update can promote the row afterwards is
            # the same question asked at the other end, and it is what a seat would cost.
            r = c.put(f"/entity/{SLUG}/{new_id}", json={"sg_status_list": "act"})
            rows.append(f"  PUT sg_status_list act        -> {r.status_code} "
                        + ("ok" if r.ok else errs(r)))
            if r.ok:
                report_seats("after promoting to act", before)
                back = c.put(f"/entity/{SLUG}/{new_id}", json={"sg_status_list": "dis"})
                rows.append(f"  PUT sg_status_list dis        -> {back.status_code}")
                report_seats("after disabling again", before)

            # A second row with the same login and email, while the first is still live.
            r = c.post(f"/entity/{SLUG}", json=MIN)
            rows.append(f"  POST the same login + email again -> {r.status_code} "
                        + ("created" if r.ok else errs(r)))
            if r.ok:
                made.add(SLUG, r.json()["data"]["id"])

            r = c.delete(f"/entity/{SLUG}/{new_id}")
            rows.append(f"  DELETE /entity/{SLUG}/<new id> -> {r.status_code} {r.text[:80]!r}")
            if r.ok:
                made.rows = [x for x in made.rows if x != (SLUG, new_id)]
            rows.append("\n=== what the delete left behind")
            r = c.get(f"/entity/{SLUG}/{new_id}")
            rows.append(f"  GET /entity/{SLUG}/<id>                     -> {r.status_code} "
                        + ("ok" if r.ok else errs(r)))
            r = c.get(f"/entity/{SLUG}/{new_id}", params={"options[return_only]": "retired"})
            rows.append(f"  GET /entity/{SLUG}/<id> return_only=retired -> {r.status_code} "
                        + (f"login {r.json()['data']['attributes'].get('login')!r}" if r.ok
                           else errs(r)))
            for label, filt in (("login", [["login", "is", LOGIN]]),
                                ("email", [["email", "is", EMAIL]])):
                r = search(SLUG, filt, ["login"], size=10)
                rows.append(f"  _search on {label:<6} -> {r.status_code} "
                            + (f"{len(r.json()['data'])} row(s)" if r.ok else errs(r)))
            report_seats("after the delete", before)

            r = c.post(f"/entity/{SLUG}", json=MIN)
            rows.append(f"  POST the same login + email after the delete -> {r.status_code} "
                        + (f"created id reused: {r.json()['data']['id'] == new_id}" if r.ok
                           else errs(r)))
            if r.ok:
                second = made.add(SLUG, r.json()["data"]["id"])
                report_seats("after the second create", before)
                r = c.delete(f"/entity/{SLUG}/{second}")
                rows.append(f"  DELETE the second row -> {r.status_code}")
                if r.ok:
                    made.rows = [x for x in made.rows if x != (SLUG, second)]
                report_seats("after the second delete", before)
        rows.append(f"  rows still registered for cleanup: {made.rows}")

_lib.emit("entity_types/HumanUser", "\n".join(rows), env)
