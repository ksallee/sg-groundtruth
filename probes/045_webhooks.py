"""Q: how does a client subscribe to events, and audit what was delivered?

`/webhook/*` is the push half of the change feed probe 025 reads by pulling `EventLogEntry`. Ten
calls, none of them in the corpus: five on the subscription, three on the deliveries it produced,
and two that send real HTTP.

The write half stands up a local listener, publishes it through a tunnel, points one hook at it,
changes one sandbox row, and records the request that came back. Every hook is named
`zzprobe_045_*` and deleted by uuid in the same run; the tunnel and the listener are stopped in a
`finally`, because a hook left registered against a dead tunnel keeps firing. Nothing touches a
hook the probe did not create.

    python probes/045_webhooks.py --write
"""
import hashlib
import hmac
import json
import subprocess
import threading
import time
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import _lib

env = _lib.load_env()
c = _lib.client()
PORT = 8099
TOKEN = "zzprobe_045_token"
GONE = str(uuid.uuid4())
RECEIVED = []
rows = []


def census(b):
    """A hook listing names third-party endpoints, each with a delivery token in its path.

    Never print one. The shape and the tally are the measurement; the rows belong to other people.
    """
    out, tally = [], {}
    for h in b.get("data", []):
        k = (h.get("status"), tuple(sorted(h.get("entity_types") or {})),
             bool(h.get("batch_deliveries")), bool(h.get("is_token_set")),
             bool(h.get("validate_ssl_cert")), h.get("num_deliveries") or 0)
        tally[k] = tally.get(k, 0) + 1
    out.append(f"   {len(b.get('data', []))} hooks, keys "
               f"{sorted(b['data'][0]) if b.get('data') else '(none)'}")
    for k, n in sorted(tally.items(), key=lambda x: -x[1]):
        out.append(f"   x{n}  status={k[0]} types={list(k[1])} batch={k[2]} token_set={k[3]} "
                   f"ssl={k[4]} num_deliveries={k[5]}")
    out.append("   links: " + json.dumps(b.get("links")))
    return out


def call(label, method, path, hide=False, **kw):
    r = c.request(method, path, **kw)
    rows.append(f"\n-- {label}")
    body = json.dumps(kw.get("json")) if kw.get("json") is not None else ""
    q = "?" + "&".join(f"{k}={v}" for k, v in kw["params"].items()) if kw.get("params") else ""
    rows.append(f"   {method} {path}{q}" + (f"  {body[:200]}" if body else ""))
    rows.append(f"   -> {r.status_code} {len(r.content)} bytes")
    try:
        b = r.json()
    except ValueError:
        if r.content:
            rows.append(f"   body (not JSON): {r.text[:200]!r}")
        return r, None
    _lib.note_from(b)
    if hide and isinstance(b.get("data"), list):
        rows.extend(census(b))
    else:
        rows.append("   " + json.dumps(b.get("errors", b))[:500])
    return r, b


rows.append("===== GET /webhook/hooks, before anything is created")
r, b = call("the site's whole list", "GET", "/webhook/hooks", hide=True)
existing = {h["id"] for h in b.get("data", [])} if b else set()

call("status filter", "GET", "/webhook/hooks", hide=True, params={"status": "active"})
call("a status no hook has", "GET", "/webhook/hooks", hide=True, params={"status": "zzprobe_045"})
call("paging", "GET", "/webhook/hooks", hide=True, params={"page[size]": 1, "page[number]": 2})
call("a uuid that is not a hook", "GET", f"/webhook/hooks/{GONE}")
call("not a uuid at all", "GET", "/webhook/hooks/zzprobe_045_not_a_uuid")
call("deliveries of a hook that is not there", "GET", f"/webhook/hooks/{GONE}/deliveries")
call("a uuid that is not a delivery", "GET", f"/webhook/deliveries/{GONE}")

if not _lib.writes_allowed():
    rows.append("\n\n===== the write half needs --write")
    _lib.emit("045_webhooks", "\n".join(rows), env)
    raise SystemExit(0)

SANDBOX = _lib.sandbox_id(c, env)
ARR = {"Content-Type": "application/vnd+shotgun.api3_array+json"}


class Receiver(BaseHTTPRequestHandler):
    """Records what Flow PT sent and answers 200, so the delivery record has a body to keep."""

    protocol_version = "HTTP/1.1"

    def _record(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b""
        RECEIVED.append({"at": time.time(), "method": self.command, "path": self.path,
                         "headers": dict(self.headers), "raw": raw})
        out = b'{"received":true}'
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("X-Zzprobe-045", "receiver")
        self.send_header("Content-Length", str(len(out)))
        self.end_headers()
        self.wfile.write(out)

    do_POST = do_PUT = do_GET = _record

    def log_message(self, *a):
        pass


def start_tunnel():
    """Returns (public https url, the process to kill, a note). Never kills a tunnel it did not start."""
    try:
        urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2)
        return None, None, "a tunnel agent is already running on 4040; not starting a second one"
    except Exception:
        pass
    p = subprocess.Popen(["ngrok", "http", str(PORT), "--log=stdout"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        time.sleep(1)
        try:
            t = json.load(urllib.request.urlopen("http://127.0.0.1:4040/api/tunnels", timeout=2))
            for x in t.get("tunnels", []):
                if x.get("public_url", "").startswith("https") and str(PORT) in x["config"]["addr"]:
                    return x["public_url"], p, "tunnel up"
        except Exception:
            continue
    p.terminate()
    return None, None, "tunnel did not come up within 40s"


def drop(b):
    """Delete a hook the moment it is created. A hook with no `projects` matches the whole site."""
    if isinstance(b, dict) and isinstance(b.get("data"), dict) and b["data"].get("id"):
        i = b["data"]["id"]
        return i, c.delete(f"/webhook/hooks/{i}").status_code
    return None, None


def self_test(pub):
    """Prove the listener is reachable from outside before blaming the API for silence.

    Without this the probe cannot tell "Flow PT did not deliver" from "the tunnel was not up",
    and those two produce the same empty result.
    """
    if not pub:
        return "no public url"
    req = urllib.request.Request(pub + "/zzprobe-045-self-test", data=b'{"self":"test"}',
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        code = urllib.request.urlopen(req, timeout=20).status
    except Exception as e:
        return f"FAILED: {type(e).__name__} {e}"
    time.sleep(2)
    return f"POST through the public url -> {code}, listener received {len(RECEIVED)}"


httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Receiver)
threading.Thread(target=httpd.serve_forever, daemon=True).start()
PUBLIC, NGROK, NOTE = start_tunnel()
SELFTEST = self_test(PUBLIC)
RECEIVED.clear()
HOOK = None


def main():
    global HOOK
    rows.append("\n\n===== POST /webhook/hooks, which url the validator accepts")
    for u in ["https://localhost:9/zzprobe-045", "http://127.0.0.1:9/zzprobe-045",
              "https://10.255.255.1/zzprobe-045", "https://192.0.2.1/zzprobe-045",
              "https://zzprobe-045.invalid/hook", "https://zzprobe-045.example.com/hook",
              "zzprobe_045", "ftp://example.com/zzprobe-045"]:
        r = c.post("/webhook/hooks", json={"url": u, "entity_types": {"Shot": {"create": []}},
                                           "name": "zzprobe_045_url"})
        b = r.json()
        i, gone = drop(b)
        src = b["errors"][0]["source"] if "errors" in b else None
        rows.append(f"   {u:38s} -> {r.status_code} "
                    f"{json.dumps(src) if src else f'created, deleted again -> {gone}'}")
    rows.append(f"   the tunnel url                         -> {NOTE}")
    rows.append(f"   listener reachable from outside        -> {SELFTEST}")

    rows.append("\n\n===== POST /webhook/hooks, what the create body has to hold")
    TARGET = PUBLIC or "https://example.com:9/zzprobe-045"
    for label, body in [
        ("empty body", {}),
        ("url alone", {"url": TARGET}),
        ("entity_types alone", {"entity_types": {"Shot": {"update": ["sg_status_list"]}}}),
        ("an action the API does not have",
         {"url": TARGET, "entity_types": {"Shot": {"zzprobe_045": []}}}),
        ("an entity type the site does not have",
         {"url": TARGET, "entity_types": {"ZzProbe045": {"create": []}}}),
        ("a field the type does not have",
         {"url": TARGET, "entity_types": {"Shot": {"update": ["zzprobe_045_nope"]}},
          "projects": [SANDBOX]}),
        ("two entity types, which the spec says is unsupported",
         {"url": TARGET, "entity_types": {"Shot": {"create": []}, "Asset": {"create": []}},
          "projects": [SANDBOX]}),
        ("a project id that is not there",
         {"url": TARGET, "entity_types": {"Shot": {"create": []}}, "projects": [999999999]}),
    ]:
        r, b = call(label, "POST", "/webhook/hooks", json=body)
        i, gone = drop(b)
        if i:
            rows.append(f"   created, deleted again -> {gone}")

    if not PUBLIC:
        rows.append(f"\n\n===== no reachable url: {NOTE}. The delivery payload is unmeasured.")
        return

    rows.append("\n\n===== the hook this probe keeps, pointed at the tunnel")
    r, b = call("create", "POST", "/webhook/hooks", json={
        "url": PUBLIC + "/zzprobe-045",
        "entity_types": {"Shot": {"create": [], "update": ["sg_status_list", "description"],
                                  "delete": []}},
        "projects": [SANDBOX], "name": "zzprobe_045_hook",
        "description": "probe 045, tunnelled, deleted in-run", "token": TOKEN})
    HOOK = b["data"]["id"] if b and isinstance(b.get("data"), dict) else None
    if not HOOK:
        return

    call("the vendor content type every _search needs", "POST", "/webhook/hooks", headers=ARR,
         json={"url": PUBLIC, "entity_types": {"Shot": {"create": []}}})
    call("read it back", "GET", f"/webhook/hooks/{HOOK}")

    rows.append("\n\n===== PUT /webhook/hooks/<record_uuid>")
    call("empty body", "PUT", f"/webhook/hooks/{HOOK}", json={})
    call("a status that is not active or disabled", "PUT", f"/webhook/hooks/{HOOK}",
         json={"status": "zzprobe_045"})
    call("one key only, is the rest kept", "PUT", f"/webhook/hooks/{HOOK}",
         json={"description": "probe 045, edited"})

    rows.append("\n\n===== a real change in the sandbox, and what came back")
    with _lib.Created(c) as made:
        st = c.get("/schema/Shot/fields/sg_status_list").json()
        vals = st["data"]["properties"]["valid_values"]["value"]
        t0 = time.time()
        shot = c.post("/entity/shots", json={"project": {"type": "Project", "id": SANDBOX},
                                             "code": "zzprobe_045_shot",
                                             "sg_status_list": vals[0]}).json()["data"]
        made.add("shots", shot["id"])
        rows.append(f"   POST /entity/shots -> {shot['id']}, sg_status_list {vals[0]!r}")
        t1 = time.time()
        pr = c.put(f"/entity/shots/{shot['id']}", json={"sg_status_list": vals[1]})
        rows.append(f"   PUT sg_status_list {vals[0]!r} -> {vals[1]!r} -> {pr.status_code}")

        for _ in range(300):
            if len(RECEIVED) >= 2:
                break
            time.sleep(1)
        t2 = time.time()
    for _ in range(120):
        if len(RECEIVED) >= 3:
            break
        time.sleep(1)
    marks = [("create", t0), ("update", t1), ("delete", t2)]
    rows.append(f"   {len(RECEIVED)} request(s) received. "
                + ", ".join(f"{what} -> delivery {RECEIVED[i]['at'] - mark:.1f}s"
                            for i, (what, mark) in enumerate(marks) if i < len(RECEIVED)))
    if not RECEIVED:
        rec = c.get(f"/webhook/hooks/{HOOK}/deliveries")
        rows.append("   nothing reached the listener. The site's own delivery record says: "
                    + json.dumps(rec.json())[:600])

    for i, got in enumerate(RECEIVED[:3]):
        rows.append(f"\n-- request {i + 1}: {got['method']} {got['path']}")
        for k in sorted(got["headers"]):
            rows.append(f"   {k}: {got['headers'][k]}")
        payload = json.loads(got["raw"])
        _lib.note_from(payload)
        rows.append("   body: " + json.dumps(payload))

    if RECEIVED:
        sig = {k.lower(): v for k, v in RECEIVED[0]["headers"].items()}
        raw = RECEIVED[0]["raw"]
        rows.append("\n-- verifying the signature against the token")
        for name, algo in (("sha1", hashlib.sha1), ("sha256", hashlib.sha256)):
            d = hmac.new(TOKEN.encode(), raw, algo).hexdigest()
            rows.append(f"   hmac-{name}(token, raw body) = {name}={d}")
        rows.append("   header sent = "
                    + json.dumps([v for k, v in sig.items() if "sign" in k or "hash" in k]))

    rows.append("\n\n===== POST /webhook/hooks/<record_uuid>/test_connection")
    n = len(RECEIVED)
    call("send a fake delivery", "POST", f"/webhook/hooks/{HOOK}/test_connection")
    for _ in range(30):
        if len(RECEIVED) > n:
            break
        time.sleep(1)
    if len(RECEIVED) > n:
        rows.append("   test payload: " + json.dumps(json.loads(RECEIVED[n]["raw"])))
    call("test a hook that is not there", "POST", f"/webhook/hooks/{GONE}/test_connection")

    rows.append("\n\n===== GET /webhook/hooks/<hook_id>/deliveries")
    ds = []
    for _ in range(30):
        r = c.get(f"/webhook/hooks/{HOOK}/deliveries")
        ds = r.json().get("data", []) if r.ok else []
        if len(ds) >= len(RECEIVED):
            break
        time.sleep(2)
    body = r.json()
    rows.append(f"   {len(ds)} delivery record(s) for {len(RECEIVED)} request(s) received")
    if ds:
        d = ds[0]
        _lib.note_from(d)
        rows.append("   keys: " + ", ".join(sorted(d)))
        rows.append("   " + json.dumps({k: v for k, v in d.items() if k != "request_body"})[:600])
    rows.append("   included: " + json.dumps(body.get("included"))[:300])
    rows.append("   performance_metrics: " + json.dumps(body.get("performance_metrics"))[:300])

    for label, params in [("status=delivered", {"status": "delivered"}),
                          ("status=failed", {"status": "failed"}),
                          ("a status the enum does not have", {"status": "zzprobe_045"}),
                          ("entity_type", {"entity_type": "Shot"}),
                          ("entity_type and entity_id", {"entity_type": "Shot",
                                                         "entity_id": shot["id"]}),
                          ("a from in the future", {"from": int(time.time()) + 86400}),
                          ("acknowledgement contains", {"acknowledgement": "zzprobe_045"})]:
        r2 = c.get(f"/webhook/hooks/{HOOK}/deliveries", params=params)
        rows.append(f"\n-- {label} -> {r2.status_code}, "
                    f"{len(r2.json().get('data', []))} of {len(ds)}")

    if ds:
        D = ds[0]["id"]
        rows.append("\n\n===== one delivery: read, acknowledge, redeliver")
        call("read it", "GET", f"/webhook/deliveries/{D}")
        call("empty body", "PUT", f"/webhook/deliveries/{D}", json={})
        call("acknowledge", "PUT", f"/webhook/deliveries/{D}",
             json={"acknowledgement": "zzprobe_045 ack"})
        r3 = c.get(f"/webhook/deliveries/{D}")
        rows.append(f"   read back: acknowledgement="
                    f"{r3.json()['data'].get('acknowledgement')!r}")
        r4 = c.get(f"/webhook/hooks/{HOOK}/deliveries", params={"acknowledgement": "zzprobe_045"})
        rows.append(f"   filter acknowledgement=zzprobe_045 -> {len(r4.json().get('data', []))}")
        call("4097 bytes, one over the documented cap", "PUT", f"/webhook/deliveries/{D}",
             json={"acknowledgement": "z" * 4097})
        call("a key the request does not take", "PUT", f"/webhook/deliveries/{D}",
             json={"status": "failed"})

        n = len(RECEIVED)
        call("redeliver", "POST", f"/webhook/deliveries/{D}/redeliver")
        for _ in range(30):
            if len(RECEIVED) > n:
                break
            time.sleep(1)
        rows.append(f"   requests received {n} -> {len(RECEIVED)}; "
                    f"same body: {len(RECEIVED) > n and RECEIVED[n]['raw'] == RECEIVED[0]['raw']}")
        r5 = c.get(f"/webhook/hooks/{HOOK}/deliveries")
        rows.append(f"   delivery records {len(ds)} -> {len(r5.json().get('data', []))}")
        call("redeliver a delivery that is not there", "POST",
             f"/webhook/deliveries/{GONE}/redeliver")

    r, b = call("the hook after all of it", "GET", f"/webhook/hooks/{HOOK}")
    rows.append(f"   status={b['data'].get('status')!r} "
                f"num_deliveries={b['data'].get('num_deliveries')!r}")


try:
    main()
finally:
    if HOOK:
        rows.append("\n\n===== teardown")
        rows.append(f"   DELETE /webhook/hooks/<uuid> -> {c.delete(f'/webhook/hooks/{HOOK}').status_code}")
        rows.append(f"   GET the hook          -> {c.get(f'/webhook/hooks/{HOOK}').status_code}")
        rows.append(f"   GET its deliveries    -> {c.get(f'/webhook/hooks/{HOOK}/deliveries').status_code}")
        rows.append(f"   DELETE it again       -> {c.delete(f'/webhook/hooks/{HOOK}').status_code}")
    now = {h["id"] for h in c.get("/webhook/hooks").json().get("data", [])}
    rows.append(f"   hooks on the site {len(existing)} before, {len(now)} after; "
                f"every pre-existing one still there: {existing <= now}")
    if NGROK:
        NGROK.terminate()
        NGROK.wait(timeout=10)
        rows.append("   tunnel stopped")
    httpd.shutdown()
    rows.append("   listener stopped")

_lib.emit("045_webhooks", "\n".join(rows), env)
