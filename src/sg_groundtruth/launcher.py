"""Sign a person in through the App Session Launcher. Behaviour verified by probe 052, not by docs.

Two unauthenticated calls and a browser. `request()` asks the site for a login and returns the page a
person opens; `poll()` asks whether they have approved it yet. What comes back is a session token, which
`FPT.from_session` spends at the token endpoint as that person, and which `alive()` and `renew()` keep
alive for as long as it is used.
"""
import requests

PATH = "/internal_api/app_session_request"
SESSION = "/internal_api/session"

# A request nobody approves is forgotten after about five minutes (probe 052).
REQUEST_LIFETIME = 300


class Pending(Exception):
    """The person has not approved yet."""


class Gone(Exception):
    """The request is unknown, forgotten, denied, or already handed out. One 404 for all four."""


def request(site, app_name, machine_id):
    """Ask for a login. Returns (session_request_id, url): open `url` in the person's browser."""
    r = requests.post(f"{site.rstrip('/')}{PATH}",
                      data={"appName": app_name, "machineId": machine_id}, timeout=30)
    r.raise_for_status()
    d = r.json()
    return d["sessionRequestId"], d["url"]


def poll(site, session_request_id):
    """Returns (session_token, login) once approved. Raises Pending until then, Gone after 404.

    The token is handed out once: the call after the approved one is 404. Keep what this returns.
    """
    r = requests.put(f"{site.rstrip('/')}{PATH}/{session_request_id}", timeout=30)
    if r.status_code == 404:
        raise Gone(r.text[:200])
    r.raise_for_status()
    d = r.json()
    if not d.get("approved"):
        raise Pending()
    return d["sessionToken"], d.get("userLogin", "")


def alive(site, session_token):
    """The site's own account of the session, or None once it is gone.

    Keys: `expiresAt` and `notifyAt` in epoch seconds, `expired`, and the `app` and `license` clocks.
    Reading it renews nothing.
    """
    r = requests.get(f"{site.rstrip('/')}{SESSION}", cookies={"_session_id": session_token}, timeout=30)
    return r.json() if r.ok else None


def renew(site, session_token):
    """Move the session's expiry to now plus the site's window. Minting a bearer does the same."""
    r = requests.post(f"{site.rstrip('/')}{SESSION}", cookies={"_session_id": session_token}, timeout=30)
    return r.ok
