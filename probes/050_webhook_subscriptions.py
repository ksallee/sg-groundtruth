"""Q: what can a webhook subscribe to?

Probe 045 measured the create contract's mechanics and used one subscription shape throughout:
`entity_types` with create, update and delete. The 400 for an empty body names a second mode that
045 never tried, `entity_types either entity types or event type is required`, and the public guide
lists a fourth lifecycle action, `revive`, and three entity families it says are excluded.

This probe asks only what a hook may name. Delivery is probe 045's open question and is not touched
here: every hook is created and deleted in the same statement, so nothing is left to fire.

    python probes/050_webhook_subscriptions.py --write

Hooks are site-level, not project rows, so `_lib.Created` does not apply. The run counts the site's
hooks before and after and asserts the set is unchanged.
"""
import json

import _lib

env = _lib.load_env()
c = _lib.client()
rows = []

# Any host that resolves passes the url validator (probe 045). Nothing is ever delivered here.
URL = "https://example.com/zzprobe-050"

# The guide lists 39 custom events. A representative spread: logins, client review, permissions,
# preferences, the webhook events themselves, and one import event.
CUSTOM = ["Shotgun_User_Login", "Shotgun_User_Logout", "Shotgun_User_FailedLogin",
          "ClientUser_Login", "CRS_Version_Media_Download", "Shotgun_Preferences_Change",
          "Shotgun_PermissionRuleSet_ChangeRule", "Shotgun_ActionMenuItem_Triggered",
          "Shotgun_Webhook_Created", "Shotgun_ImportApp_Complete", "Shotgun_Reading_Change",
          "Shotgun_PageSetting_Change"]


def try_hook(label, body):
    """Create, report, and delete in the same breath. Returns the parsed body."""
    r = c.post("/webhook/hooks", json=body)
    try:
        b = r.json()
    except ValueError:
        b = {}
    made = isinstance(b.get("data"), dict) and b["data"].get("id")
    gone = c.delete(f"/webhook/hooks/{made}").status_code if made else None
    if r.status_code >= 400:
        src = b.get("errors", [{}])[0].get("source")
        detail = b.get("errors", [{}])[0].get("title")
        rows.append(f"   {label:52s} -> {r.status_code} {json.dumps(src) if src else detail}")
    else:
        rows.append(f"   {label:52s} -> {r.status_code}, deleted again {gone}")
    return b


before = {h["id"] for h in c.get("/webhook/hooks").json().get("data", [])}
rows.append(f"===== {len(before)} hooks on the site before this probe")

if not _lib.writes_allowed():
    rows.append("\nEvery question here needs a create. Re-run with --write.")
    _lib.emit("050_webhook_subscriptions", "\n".join(rows), env)
    raise SystemExit(0)

rows.append("\n\n===== the second subscription mode: event_type")
try_hook("event_type alone", {"url": URL, "event_type": "Shotgun_User_Login"})
try_hook("event_type the API does not have",
         {"url": URL, "event_type": "zzprobe_050_not_an_event"})
try_hook("event_type as a list", {"url": URL, "event_type": ["Shotgun_User_Login"]})
try_hook("both modes at once", {"url": URL, "event_type": "Shotgun_User_Login",
                                "entity_types": {"Shot": {"create": []}}})
try_hook("event_type with projects", {"url": URL, "event_type": "Shotgun_User_Login",
                                      "projects": [_lib.sandbox_id(c, env)]})
try_hook("event_type empty string", {"url": URL, "event_type": ""})

rows.append("\n-- each documented custom event, does the site accept it")
for ev in CUSTOM:
    try_hook(ev, {"url": URL, "event_type": ev})

rows.append("\n\n===== the fourth lifecycle action the guide names")
for action in ["create", "update", "delete", "revive", "retire", "zzprobe_050"]:
    try_hook(f"{{Shot: {{{action}: []}}}}", {"url": URL, "entity_types": {"Shot": {action: []}}})
try_hook("all four at once",
         {"url": URL, "entity_types": {"Shot": {"create": [], "update": [], "delete": [],
                                                "revive": []}}})

rows.append("\n\n===== the entities the guide says are excluded")
for t in ["ApiUser", "EventLogEntry", "HumanUser", "Project", "Attachment", "Note",
          "AssetShotConnection", "PermissionRuleSet"]:
    try_hook(t, {"url": URL, "entity_types": {t: {"create": []}}})

rows.append("\n\n===== the delivery-shaping flags, accepted and read back")
r = c.post("/webhook/hooks", json={"url": URL, "entity_types": {"Shot": {"create": []}},
                                   "batch_deliveries": True, "validate_ssl_cert": False,
                                   "name": "zzprobe_050_flags"})
if r.status_code == 201:
    h = r.json()["data"]
    back = c.get(f"/webhook/hooks/{h['id']}").json()["data"]
    rows.append(f"   sent batch_deliveries=True validate_ssl_cert=False -> {r.status_code}")
    rows.append(f"   read back: batch_deliveries={back.get('batch_deliveries')!r} "
                f"validate_ssl_cert={back.get('validate_ssl_cert')!r} status={back.get('status')!r}")
    rows.append(f"   deleted -> {c.delete('/webhook/hooks/' + h['id']).status_code}")
else:
    rows.append(f"   -> {r.status_code} {json.dumps(r.json().get('errors'))[:300]}")

after = {h["id"] for h in c.get("/webhook/hooks").json().get("data", [])}
rows.append(f"\n\n===== {len(after)} hooks after; unchanged: {before == after}")

_lib.emit("050_webhook_subscriptions", "\n".join(rows), env)
