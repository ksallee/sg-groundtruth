"""Shared probe plumbing: env, client, sanitised finding output."""
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
    return text


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
