"""Shared probe plumbing: env, client, and a scrubber for the values a machine can redact safely.

A probe prints. It does not write the corpus. The agent running the probe reads the output, judges
what is identifying, and writes the finding by hand — see `.claude/commands/probe.md`.

That split exists because the two kinds of redaction have opposite failure modes. Substituting the
site URL, the script name, the key, a bearer token, an email or a presigned URL is a string replace
that cannot misfire. Deciding whether a token is a project name, an English word, a file extension or
an API error message needs judgment; an earlier version of this file guessed, and rewrote
`application/vnd+shotgun.api3_array+json` into `eddy/xenon+pylon.thicket3_array+json` inside the one
finding that string exists to teach.
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from sg_groundtruth.client import FPT  # noqa: E402
from sg_groundtruth.env import load as _load  # noqa: E402

FINDINGS = ROOT / "corpus" / "findings"
RECIPES = ROOT / "corpus" / "recipes"


def load_env():
    if not (ROOT / ".env.local").exists():
        raise SystemExit("no .env.local — copy .env.local.example")
    return _load(ROOT)


def client():
    return FPT.from_env(load_env())


def writes_allowed():
    return "--write" in sys.argv


def _need(env, key, what):
    v = (env.get(key) or "").strip()
    if not v:
        raise SystemExit(f"set {key} in .env.local — {what}")
    return v


_PROJECTS = {}


def _projects(c):
    """One listing, cached, so name lookups cost nothing after the first."""
    if not _PROJECTS:
        r = c.get("/entity/projects", params={"fields": "name", "page[size]": 200}).json()
        _PROJECTS.update({p["attributes"]["name"]: p["id"] for p in r["data"]})
    return _PROJECTS


def resolve_project(c, ref):
    """A project id or a project name. Names are readable in a setup doc; ids survive a rename."""
    ref = str(ref).strip()
    if ref.isdigit():
        return int(ref)
    by_name = _projects(c)
    if ref not in by_name:
        raise SystemExit(f"no project named {ref!r} on this site")
    return by_name[ref]


_MEASURED = {"sample": [], "used": set(), "sandbox": None}


class _Sampled(list):
    """The sample projects, remembering which ones the probe reached for.

    A probe that takes `[0]` measured one project, not the three the environment offers, and the
    finding should say so. Recording the subscript is the only way to know that without asking the
    probe to declare it.
    """

    def __getitem__(self, i):
        if isinstance(i, slice):
            _MEASURED["used"].update(range(*i.indices(len(self))))
        else:
            _MEASURED["used"].add(i if i >= 0 else len(self) + i)
        return list.__getitem__(self, i)

    def __iter__(self):
        _MEASURED["used"].update(range(len(self)))
        return list.__iter__(self)


def sample_projects(c, env):
    """Read-only projects a probe may measure, most interesting first. Ids or names, comma separated.

    Site ids and names are site data: hardcoding one in committed source is the same leak either way.
    """
    raw = _need(env, "FPT_PROBE_SAMPLE_PROJECTS", "comma-separated project ids or names probes may READ")
    ids = [resolve_project(c, x) for x in raw.split(",") if x.strip()]
    _MEASURED["sample"] = ids
    return _Sampled(ids)


def sandbox_name(env):
    """The one project a probe may WRITE into. A name, because probe 011 creates it if absent."""
    _MEASURED["sandbox"] = _need(env, "FPT_PROBE_SANDBOX_PROJECT",
                                 "the project name probes may WRITE into")
    return _MEASURED["sandbox"]


def sandbox_id(c, env):
    """Resolve the sandbox name to an id. Fails loudly rather than writing into the wrong project."""
    name = sandbox_name(env)
    if name not in _projects(c):
        raise SystemExit(f"no project named {name!r}; run probe 011 --write to create the sandbox")
    _MEASURED["sandbox"] = _projects(c)[name]
    return _MEASURED["sandbox"]


def measured():
    """Where this run took its evidence, as the finding's `measured:` value.

    Derived from what the probe reached for, not from anything it declares: a declaration goes stale
    the first time someone edits the probe below it.
    """
    parts = []
    used, n = sorted(_MEASURED["used"]), len(_MEASURED["sample"])
    if len(used) == n and n > 1:
        parts.append(f"all {n} sample projects")
    elif used:
        which = ", ".join(str(i + 1) for i in used)
        parts.append(f"sample project{'s' if len(used) > 1 else ''} {which} of {n}")
    if _MEASURED["sandbox"] is not None:
        parts.append("sandbox project written" if writes_allowed() else "sandbox project read")
    return ", ".join(parts) or "site-wide"


def scrub(text, env):
    """Mechanical substitutions only. Never touches ordinary words."""
    for key in ("FPT_API_SITE_URL", "FPT_API_SCRIPT_NAME", "FPT_API_API_KEY"):
        v = env.get(key)
        if v:
            text = text.replace(v, f"<{key}>")
    host = (env.get("FPT_API_SITE_URL") or "").split("//")[-1].split(".")[0]
    if host:
        text = text.replace(host, "<site>")
    home = os.path.expanduser("~")
    if home and home != "/":
        text = text.replace(home, "<home>")
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", text)
    text = re.sub(r"(?i)(bearer\s+|(?:access|refresh|session)_token\"?\s*[:=]\s*\"?)[\w.\-]{20,}",
                  r"\1<token>", text)
    # A JWT is three base64url segments. The token endpoint returns two of them and only one was
    # ever named in a key this pattern could see.
    text = re.sub(r"\beyJ[\w-]{8,}\.[\w-]{8,}\.[\w-]{8,}", "<token>", text)
    # Presigned media URLs carry the site host and a signature.
    text = re.sub(r"https://[\w.\-]*(amazonaws|shotgrid|shotgunstudio)[\w.\-]*/\S+", "<media-url>", text)
    return text


_NAMEISH = {"name", "code", "login", "firstname", "lastname", "content", "description",
            "cached_display_name", "title", "subject", "email", "sg_description"}
_SEEN = set()


def note_names(*values):
    """Flag a value as probably identifying. Printed at the end of a run so the agent writing the
    finding knows what to replace; never rewritten automatically."""
    _SEEN.update(v.strip() for v in values if isinstance(v, str) and len(v.strip()) >= 3)


def note_from(obj):
    """Walk a decoded response and flag every name-ish value. Skips `errors` payloads: JSON:API puts
    the message under `title`/`detail`, and those are teaching content, not names."""
    if isinstance(obj, dict):
        if "errors" in obj:
            obj = {k: v for k, v in obj.items() if k != "errors"}
        for k, v in obj.items():
            if k in _NAMEISH and isinstance(v, str):
                note_names(v)
            else:
                note_from(v)
    elif isinstance(obj, list):
        for x in obj:
            note_from(x)


def note_path(path):
    """Flag every segment of a filesystem path. Paths carry show, asset and user names that never
    appear in a name-ish field."""
    for seg in re.split(r"[/\\]", str(path or "")):
        note_names(seg)


class Created:
    """Rows a probe made, deleted when it finishes.

    A probe leaves no trace. Sandbox rows outlive the run otherwise, and the next probe measures them.

        with _lib.Created(c) as made:
            v = c.post("/entity/versions", json={...}).json()["data"]
            made.add("versions", v["id"])
    """

    def __init__(self, c):
        self.c, self.rows = c, []

    def add(self, slug, entity_id):
        self.rows.append((slug, entity_id))
        return entity_id

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        for slug, i in reversed(self.rows):
            r = self.c.delete(f"/entity/{slug}/{i}")
            print(f"  deleted /entity/{slug}/{i} -> {r.status_code}")
        return False


def emit(slug, actual, env):
    """Print the probe's evidence, scrubbed, where it was measured, and the names the agent judges.

    The provenance goes to the frontmatter, not into the `**Actual**` block: field-type and
    entity-type cards have no `**Actual**` block to hold it, the block is capped at 30 lines of
    evidence, and only a key can be required by `check_corpus.py` and read by the site.
    """
    print(f"===== {slug} =====")
    print(scrub(actual.strip(), env))
    print("\n----- measured on <site>, paste the second line into the finding's frontmatter -----")
    print(f"# sample projects {_MEASURED['sample'] or 'none read'}, "
          f"sandbox {scrub(str(_MEASURED['sandbox'] or 'not resolved'), env)}")
    print(f"measured: {measured()}")
    if _SEEN:
        flagged = sorted(scrub(n, env) for n in _SEEN)
        print("\n----- identifying, replace with a placeholder before writing the finding -----")
        print("\n".join(f"  {n}" for n in flagged))


def dump(obj, limit=2000):
    return json.dumps(obj, indent=2, default=str)[:limit]
