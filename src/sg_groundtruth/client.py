"""Thin Flow PT REST client. Behaviour verified by probes, not by docs."""
import os
import time

import requests

# The site's OpenAPI document advertises /api/v1.1 and never mentions /api/v1. They are the
# same API: same 62 operations, same bodies, and links echo whichever prefix you called.
# /api/v1 stays because every finding in the corpus was measured on it. Probe 051.
API = "/api/v1"


class FPTError(RuntimeError):
    pass


class FPT:
    def __init__(self, site, script_name, script_key, sudo_as_login=""):
        """`sudo_as_login` acts as that HumanUser: reads what they read, and writes as them.

        Impersonation is an OAuth2 scope on the token request, never a body field (probe 027). The
        target needs `can_impersonate_this_user` and an active status, both granted in the web UI.
        """
        self.site = site.rstrip("/")
        self._creds = {
            "grant_type": "client_credentials",
            "client_id": script_name,
            "client_secret": script_key,
        }
        self.sudo_as_login = sudo_as_login or ""
        if self.sudo_as_login:
            self._creds["scope"] = f"sudo_as_login:{self.sudo_as_login}"
        self._token = None
        self._expires_at = 0.0

    @classmethod
    def from_env(cls, env=None, sudo_as_login=""):
        """A client from the environment. Acting as someone is asked for, never inferred.

        No login is read out of the environment here: a client that impersonates because a variable
        happens to be set is worse than one that makes the caller say so.
        """
        e = env or os.environ
        missing = [k for k in ("FPT_API_SITE_URL", "FPT_API_SCRIPT_NAME", "FPT_API_API_KEY") if not e.get(k)]
        if missing:
            raise FPTError(f"missing in .env.local: {', '.join(missing)}")
        return cls(e["FPT_API_SITE_URL"], e["FPT_API_SCRIPT_NAME"], e["FPT_API_API_KEY"],
                   sudo_as_login=sudo_as_login)

    def _authenticate(self):
        r = requests.post(
            f"{self.site}{API}/auth/access_token",
            data=self._creds,
            headers={"Accept": "application/json"},
            timeout=30,
        )
        if not r.ok:
            # Every impersonation refusal lands here rather than on the call the caller meant to
            # make, so the message says which of the two failed.
            who = f" as {self.sudo_as_login!r}" if self.sudo_as_login else ""
            raise FPTError(f"auth{who} {r.status_code}: {r.text[:300]}")
        d = r.json()
        self._token = d["access_token"]
        # expires_in is short (probe 001); refresh a minute early.
        self._expires_at = time.time() + int(d.get("expires_in", 600)) - 60

    def request(self, method, path, **kw):
        if not self._token or time.time() >= self._expires_at:
            self._authenticate()
        headers = {"Authorization": f"Bearer {self._token}", "Accept": "application/json"}
        headers.update(kw.pop("headers", {}))
        # links.next and links.self come back root-relative *including* the /api/v1 prefix (probe 006),
        # so prepending API again would 404.
        if path.startswith("http"):
            url = path
        elif path.startswith(API):
            url = f"{self.site}{path}"
        else:
            url = f"{self.site}{API}{path}"
        return requests.request(method, url, headers=headers, timeout=60, **kw)

    def get(self, path, **kw):
        return self.request("GET", path, **kw)

    def post(self, path, **kw):
        return self.request("POST", path, **kw)

    def put(self, path, **kw):
        return self.request("PUT", path, **kw)

    def delete(self, path, **kw):
        return self.request("DELETE", path, **kw)
