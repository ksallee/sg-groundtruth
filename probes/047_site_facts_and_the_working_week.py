"""Q: what does the site tell you about itself beyond /preferences, and which of it is writable?

Three endpoints answer questions no entity or schema call can: how many seats the site has,
which subscription each user holds, and which calendar days count as work. Each has a write
side, and each write side changes configuration for every user of the site.

Read-only by default. The `--write` half sends only bodies that must be rejected: an empty
object, a missing required key, an unparseable date, a user id that does not exist. Nothing
here may name a real date, a real user or a real entity type on the write side.
"""
import json
from datetime import date, timedelta

import _lib

env = _lib.load_env()
c = _lib.client()
PROJECT = _lib.sample_projects(c, env)[0]
rows = []

# Fixed window so two runs measure the same fortnight. Monday to the second Sunday.
START = date(2026, 3, 2)
END = START + timedelta(days=13)
FMT = "%Y-%m-%d"


def call(label, method, path, **kw):
    r = c.request(method, path, **kw)
    rows.append(f"\n-- {label}")
    rows.append(f"   {method} {path}" + (f"  {json.dumps(kw.get('json'))[:200]}" if "json" in kw else "")
                + (f"  {kw.get('params')}" if kw.get("params") else ""))
    rows.append(f"   -> {r.status_code} {len(r.content)} bytes")
    try:
        b = r.json()
    except ValueError:
        rows.append(f"   body (not JSON): {r.text[:200]!r}")
        return r, None
    _lib.note_from(b)
    rows.append("   " + json.dumps(b.get("errors", b))[:500])
    return r, b


rows.append("===== GET /license_info")
r, b = call("no parameters", "GET", "/license_info")
if b and "data" in b:
    rows.append("   value types: " + json.dumps({k: type(v).__name__ for k, v in b["data"].items()}))
call("an unknown query parameter", "GET", "/license_info", params={"prefs": "hours_per_day"})

rows.append("\n\n===== GET /subscription_seat/user_subscriptions")
r, b = call("no parameters", "GET", "/subscription_seat/user_subscriptions")
if isinstance(b, dict):
    tally = {}
    for v in b.values():
        tally[str(v)] = tally.get(str(v), 0) + 1
    rows.append(f"   top level is a bare hash: {len(b)} keys, no data/links envelope")
    rows.append(f"   key types {sorted({type(k).__name__ for k in b})}, "
                f"value tally {json.dumps(tally)}")
    rows.append(f"   first three entries {json.dumps(dict(list(b.items())[:3]))}")

# Cross-check the seat hash against the user list: does it hold every user, or only some?
users = c.get("/entity/human_users",
              params={"fields": "login,sg_status_list", "page[size]": 500}).json()["data"]
if isinstance(b, dict):
    ids = {str(u["id"]) for u in users}
    rows.append(f"   HumanUser rows {len(ids)}, seat-hash keys {len(b)}")
    rows.append(f"   keys not in HumanUser: {len(set(b) - ids)}; "
                f"HumanUser not in keys: {len(ids - set(b))}")
    by_status = {}
    for u in users:
        st = str(u["attributes"].get("sg_status_list"))
        seat = "in hash" if str(u["id"]) in b else "absent"
        by_status.setdefault(st, {}).setdefault(seat, 0)
        by_status[st][seat] += 1
    rows.append("   HumanUser.sg_status_list x seat hash: " + json.dumps(by_status))
USER = users[0]["id"]
_lib.note_names(users[0]["attributes"].get("login") or "")

rows.append("\n\n===== GET /schedule/work_day_rules")
r, b = call("a fortnight, no user and no project", "GET", "/schedule/work_day_rules",
            params={"start_date": START.strftime(FMT), "end_date": END.strftime(FMT)})
if b and "data" in b:
    rows.append(f"   rows {len(b['data'])} for a 14-day window (inclusive of both ends)")
    rows.append("   " + " ".join(f"{d['date'][-2:]}{'W' if d['working'] else '.'}" for d in b["data"]))
    rows.append("   weekdays " + " ".join(
        f"{date.fromisoformat(d['date']).strftime('%a')}={d['working']}" for d in b["data"][:7]))
    rows.append("   reasons " + json.dumps(sorted({d["reason"] for d in b["data"]})))
    rows.append("   row keys " + json.dumps(sorted(b["data"][0])))
    rows.append("   links " + json.dumps(b.get("links")))

call("scoped to a project", "GET", "/schedule/work_day_rules",
     params={"start_date": START.strftime(FMT), "end_date": END.strftime(FMT),
             "project_id": PROJECT})
call("scoped to a user", "GET", "/schedule/work_day_rules",
     params={"start_date": START.strftime(FMT), "end_date": END.strftime(FMT), "user_id": USER})
call("a project that is not there", "GET", "/schedule/work_day_rules",
     params={"start_date": START.strftime(FMT), "end_date": END.strftime(FMT),
             "project_id": 999999999})
call("a user that is not there", "GET", "/schedule/work_day_rules",
     params={"start_date": START.strftime(FMT), "end_date": END.strftime(FMT),
             "user_id": 999999999})
call("no end_date", "GET", "/schedule/work_day_rules",
     params={"start_date": START.strftime(FMT)})
call("no parameters at all", "GET", "/schedule/work_day_rules")
call("end_date before start_date", "GET", "/schedule/work_day_rules",
     params={"start_date": END.strftime(FMT), "end_date": START.strftime(FMT)})
call("a date that will not parse", "GET", "/schedule/work_day_rules",
     params={"start_date": "not-a-date", "end_date": END.strftime(FMT)})
call("a slashed date", "GET", "/schedule/work_day_rules",
     params={"start_date": "03/02/2026", "end_date": "03/15/2026"})
r, b = call("two years in one call", "GET", "/schedule/work_day_rules",
            params={"start_date": "2026-01-01", "end_date": "2027-12-31"})
if b and "data" in b:
    rows.append(f"   rows {len(b['data'])} for a 730-day window; no page envelope, no links.next")
    reasons = {}
    for d in b["data"]:
        reasons[d["reason"]] = reasons.get(d["reason"], 0) + 1
    rows.append("   reason tally over two years " + json.dumps(reasons))
    rows.append(f"   non-working days {sum(1 for d in b['data'] if not d['working'])}, "
                f"described {sum(1 for d in b['data'] if d['description'])}")
    # Does a project override anything the studio default says?
    p = c.get("/schedule/work_day_rules",
              params={"start_date": "2026-01-01", "end_date": "2027-12-31",
                      "project_id": PROJECT}).json()["data"]
    diff = [(x["date"], x["working"], y["working"]) for x, y in zip(b["data"], p)
            if x["working"] != y["working"] or x["reason"] != y["reason"]]
    rows.append(f"   days where project {PROJECT} differs from the studio default: {len(diff)}")
r, b = call("the same day twice", "GET", "/schedule/work_day_rules",
            params={"start_date": START.strftime(FMT), "end_date": START.strftime(FMT)})

# ---------------------------------------------------------------------------
# The write half. Every body below is chosen so that it CANNOT succeed: no real
# date, no real user id, no real entity type. The point is the rejection, which
# names the parameters. A body that could apply is not sent from here.
# ---------------------------------------------------------------------------
if not _lib.writes_allowed():
    rows.append("\n\n===== write paths not exercised (pass --write)")
else:
    rows.append("\n\n===== PUT /schedule/work_day_rules  (rejections only)")
    call("empty body", "PUT", "/schedule/work_day_rules", json={})
    call("working, but no date", "PUT", "/schedule/work_day_rules", json={"working": True})
    call("a date that will not parse", "PUT", "/schedule/work_day_rules",
         json={"date": "not-a-date", "working": True})
    call("bogus recalculate_field, on an unparseable date", "PUT", "/schedule/work_day_rules",
         json={"date": "not-a-date", "working": True,
               "recalculate_field": "definitely_not_a_field"})
    call("working is a string, on an unparseable date", "PUT", "/schedule/work_day_rules",
         json={"date": "not-a-date", "working": "yes"})
    call("a user that is not there, on an unparseable date", "PUT", "/schedule/work_day_rules",
         json={"date": "not-a-date", "working": True, "user_id": 999999999})

    rows.append("\n\n===== POST /subscription_seat/user_subscriptions  (rejections only)")
    call("empty body: names no user", "POST", "/subscription_seat/user_subscriptions", json={})
    call("a user that is not there, and a subscription that is not a subscription", "POST",
         "/subscription_seat/user_subscriptions",
         json={"999999999": "definitely_not_a_subscription"})
    call("a list where a hash is wanted", "POST", "/subscription_seat/user_subscriptions",
         json=[{"999999999": "definitely_not_a_subscription"}])
    call("a key that is not a number", "POST", "/subscription_seat/user_subscriptions",
         json={"definitely_not_a_user": "definitely_not_a_subscription"})

    rows.append("\n\n===== PUT /preferences/update  (rejections only)")
    call("empty body", "PUT", "/preferences/update", json={})
    call("preference alone", "PUT", "/preferences/update", json={"preference": "enable_entity"})
    call("entity_type alone", "PUT", "/preferences/update",
         json={"entity_type": "NotAnEntityType"})
    call("an operation the endpoint does not have", "PUT", "/preferences/update",
         json={"preference": "definitely_not_a_preference", "entity_type": "NotAnEntityType"})
    call("enable_entity on a type that does not exist", "PUT", "/preferences/update",
         json={"preference": "enable_entity", "entity_type": "NotAnEntityType"})
    call("an empty array, which enables nothing", "PUT", "/preferences/update", json=[])

_lib.emit("047_site_facts_and_the_working_week", "\n".join(rows), env)
