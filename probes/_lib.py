"""Shared probe plumbing: env, client, sanitised finding output."""
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from fpt_llm_api.client import FPT  # noqa: E402

FINDINGS = ROOT / "corpus" / "findings"
RECIPES = ROOT / "corpus" / "recipes"


def load_env():
    env = {}
    f = ROOT / ".env.local"
    if not f.exists():
        raise SystemExit("no .env.local — copy .env.local.example")
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def client():
    return FPT.from_env(load_env())


def writes_allowed():
    return "--write" in sys.argv


# Industry-generic vocabulary. Never redacted: it carries the teaching value of the corpus and
# identifies nobody. Pipeline steps, statuses, entity types, schema words.
SAFE = {
    "comp", "anim", "layout", "light", "lighting", "fx", "model", "modeling", "rig", "rigging", "previz",
    "roto", "paint", "matte", "track", "tracking", "lookdev", "surfacing", "groom", "cloth", "crowd",
    "edit", "editorial", "conform", "grade", "online", "plate", "element", "render", "review", "final",
    "shot", "asset", "sequence", "scene", "task", "version", "note", "playlist", "project", "step",
    "status", "type", "name", "code", "description", "image", "movie", "thumbnail", "attachment",
    "user", "group", "department", "pipeline", "delivery", "vendor", "client", "artist", "supervisor",
    "wtg", "ip", "fin", "apr", "rev", "omt", "hld", "dis", "cmpt", "clsd", "vwd", "cfrm", "part", "pass",
    "and", "the", "for", "not", "all", "any", "date", "time", "list", "text", "float",
    "entity", "field", "value", "true", "false", "null", "none", "custom", "default", "system",
    "pending", "approved", "progress", "complete", "viewed", "confirmed", "closed", "omitted",
    "ready", "waiting", "hold", "disabled", "cbb", "icon", "active",
}
# Standard entity types are safe. Anything else capitalised is a name until proven otherwise —
# an earlier version used [A-Z]\w* here and leaked every single-word display name.
STD_ENTITIES = {
    "Project", "Shot", "Asset", "Sequence", "Scene", "Task", "Version", "Note", "Playlist", "Step",
    "HumanUser", "ApiUser", "Group", "Department", "Attachment", "Delivery", "PublishedFile",
    "PublishedFileType", "Ticket", "Phase", "Cut", "CutItem", "Status", "Icon", "Reply", "Element",
    "TimeLog", "Booking", "EventLogEntry", "Camera", "Release", "Launcher", "Software", "LocalStorage",
}
ENTITY_RE = re.compile(r"^Custom(Entity|NonProject\w*)\d*(_\w+_Connection)?$")

_FIRST = ["Ari", "Bo", "Cy", "Dev", "Eli", "Fen", "Gus", "Hana", "Ivo", "Jules", "Kai", "Lux",
          "Mira", "Nico", "Oona", "Piet", "Quin", "Rune", "Sol", "Tao", "Uma", "Vera", "Wren", "Zia"]
_LAST = ["Alder", "Brenn", "Cove", "Dray", "Ember", "Frost", "Gale", "Hollow", "Iris", "Jarn",
         "Kestrel", "Larkin", "Mourne", "Nesbit", "Orrin", "Pell", "Quarry", "Raske", "Stilt", "Thorne"]
_WORDS = ["cobalt", "dovetail", "ember", "fathom", "girder", "harrow", "indigo", "jetty", "kelp",
          "lantern", "marrow", "nimbus", "orchard", "pylon", "quartz", "rivet", "sable", "tundra",
          "umber", "vellum", "willow", "xenon", "yarrow", "zephyr", "anvil", "basalt", "cinder",
          "drift", "eddy", "flint", "gable", "haven", "inlet", "juniper", "kiln", "loom", "mesa",
          "notch", "obsidian", "prism", "quill", "ridge", "slate", "thicket", "updraft", "vapor",
          "warren", "yonder", "zenith", "alcove", "bramble", "cairn", "delta", "escarp", "fjord"]


def _pick(seq, s, salt):
    h = hashlib.sha256(f"{salt}{s.lower()}".encode()).hexdigest()
    return seq[int(h, 16) % len(seq)]


def pseudonym(real, salt=""):
    """Stable fictional stand-in. Same input always yields the same output, so a name referenced by
    two findings reads the same in both. Shape is preserved: codes stay code-shaped."""
    real = real.strip()
    if (not real or len(real) < 3 or ENTITY_RE.match(real) or real.startswith("sg_")
            or real in STD_ENTITIES):
        return real
    words = real.split()
    if (len(words) == 2 and all(w[:1].isupper() and w.isalpha() for w in words)
            and not any(w.lower() in SAFE for w in words)):
        return f"{_pick(_FIRST, words[0], salt)} {_pick(_LAST, words[1], salt)}"

    def swap(m):
        tok = m.group(0)
        # Acronyms are identifying even at two letters, and split across digits (E2E -> E, E).
        if tok.lower() in SAFE or (len(tok) < 3 and not tok.isupper()):
            return tok
        new = _pick(_WORDS, tok, salt)
        return new.upper() if tok.isupper() else (new.capitalize() if tok[:1].isupper() else new)

    return re.sub(r"[A-Za-z]+", swap, real)


def _redactable(v):
    v = v.strip()
    return not (
        len(v) < 3
        or v.startswith("sg_")
        or v.startswith("<")
        or ENTITY_RE.match(v)
        or v in STD_ENTITIES
        or v.lower() in SAFE
        or not any(c.isalpha() for c in v)
    )


_NAME_KEYS = r"name|code|login|firstname|lastname|content|description|cached_display_name|display|title"
_REGISTERED = set()


def register_names(*names):
    """Values a probe knows are identifying — project names, user names, codes pulled from the site."""
    _REGISTERED.update(n for n in names if n and isinstance(n, str) and len(n) >= 3)


_NAMEISH = {"name", "code", "login", "firstname", "lastname", "content", "description",
            "cached_display_name", "title", "subject", "email", "sg_description"}


def register_from(obj):
    """Walk a decoded response and register every name-ish value. Probes call this on raw payloads so
    that names reformatted into tables or tuples still get redacted — matching on key shape alone missed
    anything the probe pretty-printed itself."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in _NAMEISH and isinstance(v, str):
                register_names(v)
            else:
                register_from(v)
    elif isinstance(obj, list):
        for x in obj:
            register_from(x)


def _redact_names(text, salt):
    for real in sorted(_REGISTERED, key=len, reverse=True):
        if _redactable(real):
            text = text.replace(real, pseudonym(real, salt))

    def json_val(m):
        return m.group(0).replace(m.group(1), pseudonym(m.group(1), salt)) if _redactable(m.group(1)) else m.group(0)

    text = re.sub(rf'"(?:{_NAME_KEYS})"\s*:\s*"([^"]{{1,200}})"', json_val, text)
    text = re.sub(rf"\b(?:{_NAME_KEYS})\s*=\s*'([^']{{1,200}})'", json_val, text)
    return text


def sanitize(text, env):
    for key in ("FPT_API_SITE_URL", "FPT_API_SCRIPT_NAME", "FPT_API_API_KEY"):
        v = env.get(key)
        if v:
            text = text.replace(v, f"<{key}>")
    host = (env.get("FPT_API_SITE_URL") or "").split("//")[-1].split(".")[0]
    if host:
        text = text.replace(host, "<site>")
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "<email>", text)
    text = re.sub(r"(?i)(bearer\s+|access_token\"?\s*[:=]\s*\"?)[\w.\-]{20,}", r"\1<token>", text)
    # Presigned media URLs carry the site host and signatures.
    text = re.sub(r"https://[\w.\-]*(amazonaws|shotgrid|shotgunstudio)[\w.\-]*/\S+", "<media-url>", text)
    return _redact_names(text, env.get("FPT_REDACTION_SALT", ""))


def record(slug, endpoint, doc_claim, actual, verdict, env, tags=(), python_equivalent=None):
    """Write a finding. `verdict` is one actionable sentence — it lands in INDEX.md and is often
    all an agent reads. `tags` drive retrieval; see probes/index.py."""
    extra = f"\n**Python equivalent**\n\n```python\n{python_equivalent.strip()}\n```\n" if python_equivalent else ""
    body = f"""---
tags: [{", ".join(tags)}]
verdict: {verdict}
---

# {slug}

**Endpoint** `{endpoint}`

**Docs claim** {doc_claim}

**Actual**

```
{actual.strip()}
```

**Verdict** {verdict}
{extra}"""
    FINDINGS.mkdir(parents=True, exist_ok=True)
    (FINDINGS / f"{slug}.md").write_text(sanitize(body, env))
    print(f"wrote corpus/findings/{slug}.md")


def dump(obj, limit=2000):
    return json.dumps(obj, indent=2, default=str)[:limit]


def record_recipe(slug, intent, call, response, env, tags=(), notes=(), lang="python"):
    """A verified task -> call -> real response pair. This is the corpus an LLM reads to *do*
    something, as opposed to a finding, which it reads to reason about the API."""
    note_lines = "\n".join(f"- {n}" for n in notes)
    body = f"""---
intent: {intent}
tags: [{", ".join(tags)}]
---

# {slug}

{intent}

## Call

```{lang}
{call.strip()}
```

## Response

```json
{response.strip()}
```

## Notes

{note_lines or "- none"}
"""
    RECIPES.mkdir(parents=True, exist_ok=True)
    (RECIPES / f"{slug}.md").write_text(sanitize(body, env))
    print(f"wrote corpus/recipes/{slug}.md")
