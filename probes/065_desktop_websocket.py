"""Q: does Shotgun Desktop's local websocket on :9000 answer a page that is not the site?"""
import asyncio
import json
import ssl

import websockets

import _lib

env = _lib.load_env()
SITE = env["FPT_API_SITE_URL"].rstrip("/")
HOST = "shotgunlocalhost.com"
URL = f"wss://{HOST}:9000"
rows = []


def out(s=""):
    rows.append(s)


def head(s):
    out("")
    out(s)


ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

head("1. the certificate the port presents")
try:
    pem = ssl.get_server_certificate((HOST, 9000))
    from cryptography import x509  # noqa: E402

    cert = x509.load_pem_x509_certificate(pem.encode())
    out(f"  subject {cert.subject.rfc4514_string()}  issuer {cert.issuer.rfc4514_string()}")
    out(f"  not after {cert.not_valid_after_utc.date()}")
except ImportError:
    out("  (cryptography not installed; subject unread)")
except Exception as e:  # noqa: BLE001
    out(f"  {type(e).__name__}: {e}")
try:
    ssl.create_default_context().wrap_socket(__import__("socket").create_connection((HOST, 9000)),
                                             server_hostname=HOST).close()
    out("  the default trust store accepts it")
except Exception as e:  # noqa: BLE001
    out(f"  the default trust store refuses it: {type(e).__name__}: {str(e)[:80]}")

FIRST = [
    ("empty object", "{}"),
    ("plain text", "hello"),
    ("protocol query", json.dumps({"protocol_version": 2,
                                   "command": {"name": "get_protocol_version", "data": {}}})),
]


async def talk(origin, label):
    """Handshake with one Origin, then say three things and record every answer and the close."""
    head(f"Origin: {label}")
    hdr = {"Origin": origin} if origin else {}
    try:
        ws = await websockets.connect(URL, ssl=ctx, additional_headers=hdr, open_timeout=5)
    except websockets.exceptions.InvalidStatus as e:
        r = e.response
        body = r.body.decode(errors="replace").strip()[:160] if r.body else ""
        out(f"  handshake refused -> {r.status_code} {r.reason_phrase}  {body}")
        return
    except Exception as e:  # noqa: BLE001
        out(f"  handshake failed: {type(e).__name__}: {str(e)[:120]}")
        return
    out("  handshake -> 101, connection open")
    try:
        try:
            first = await asyncio.wait_for(ws.recv(), timeout=1.5)
            out(f"  unsolicited: {str(first)[:200]}")
        except asyncio.TimeoutError:
            out("  nothing unsolicited in 1.5s")
        for name, msg in FIRST:
            await ws.send(msg)
            try:
                reply = await asyncio.wait_for(ws.recv(), timeout=3)
                out(f"  {name:<15} -> {str(reply)[:220]}")
            except asyncio.TimeoutError:
                out(f"  {name:<15} -> no reply in 3s")
    except websockets.exceptions.ConnectionClosed as e:
        out(f"  closed by server: code {e.rcvd.code if e.rcvd else '?'} "
            f"reason {e.rcvd.reason if e.rcvd else ''!r}")
        return
    await ws.close()
    out("  closed by us")


async def main():
    for origin, label in (
        (None, "none"),
        (SITE, "the site"),
        ("https://other.shotgrid.autodesk.com", "another site"),
        ("http://localhost:5173", "a dev server"),
        ("https://sg-comfyui.vercel.app", "an unrelated https page"),
    ):
        await talk(origin, label)


asyncio.run(main())
_lib.emit("065_desktop_websocket", "\n".join(rows), env)
