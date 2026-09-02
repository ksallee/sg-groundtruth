"""Lint the committed corpus: no secrets, and a finding that stays cheap to read.

Runs over the artifact rather than the pipeline, so it also covers prose an agent wrote by hand —
which is everything now that probes only print.
"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from sg_groundtruth.env import load as _load  # noqa: E402

CORPUS = ROOT / "corpus"
VERDICT_MAX = 200
ACTUAL_MAX = 30
SECTIONS = ("**Q**", "**Endpoint**", "**Docs claim**", "**Actual**", "**Teaches**")
# The field-type matrix answers a different shape of question, so it has its own required sections.
TYPE_SECTIONS = ("**Data type**", "**Read**", "**Write**", "**Clear**", "**Filter**", "**Traps**")
# The entity-type matrix answers a different shape of question again.
ENTITY_SECTIONS = ("**Type**", "**Identity**", "**Create**", "**Links**", "**Status**", "**Traps**")
# Cap the prose, not the file. A card with forty rows of table is doing its job; forty
# lines of paragraph is not. Counting both the same penalised measured cases exactly as
# much as waffle, and nine of the first twenty-four cards ended up pinned to the ceiling.
TYPE_MAX_PROSE = 45

env = _load(ROOT) if (ROOT / ".env.local").exists() else {}
secrets = [v for k, v in env.items()
           if k.startswith("FPT_API_") and isinstance(v, str) and len(v) >= 6]
host = (env.get("FPT_API_SITE_URL") or "").split("//")[-1].split(".")[0]
if host:
    secrets.append(host)
home = os.path.expanduser("~")
if home and home != "/":
    secrets.append(home)

PATTERNS = [
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "email address"),
    (re.compile(r"(?i)bearer\s+[\w.\-]{20,}"), "bearer token"),
    (re.compile(r"https://[\w.\-]*(amazonaws|shotgunstudio)[\w.\-]*/\S+"), "presigned URL"),
    (re.compile(r"\.shotgrid\.autodesk\.com"), "site host"),
]

# Public documentation register — see the Style section of CLAUDE.md.
BANNED = [
    r"carr(?:y|ies|ying|ied)", r"travel(?:s|led|ling|ing)?", r"arriv(?:e|es|ing|ed)",
    r"note that", r"worth noting", r"the whole point", r"of course",
    r"simply", r"essentially", r"basically", r"obviously", r"really",
    # Rhetorical scaffolding: the evidence is already on the page, so do not announce it.
    r"is the proof", r"the point is", r"this is the key", r"which is why", r"in other words",
    r"what this means", r"the takeaway", r"the upshot", r"crucially", r"importantly", r"notably",
    r"the whole case", r"that is what makes", r"it is worth", r"the tell",
]
BANNED_RE = re.compile(r"(?i)(?<!\w)(" + "|".join(BANNED) + r")(?!\w)")
FENCE_RE = re.compile(r"```.*?```", re.S)
TICK_RE = re.compile(r"`[^`]*`")
# Capitals are for API literals, never for emphasis (CLAUDE.md Style).
CAPS_RE = re.compile(r"(?<![\w`])[A-Z]{2,}(?![\w`])")
CAPS_OK = {"REST", "API", "URL", "URI", "JSON", "HTTP", "GET", "PUT", "POST", "DELETE", "PATCH",
           "UTC", "ID", "IDS", "S3", "PNG", "MP4", "RGB", "CSS", "PDF", "USD", "RV", "SDK", "CLI",
           "MIT", "AGPL", "UI", "OK", "NULL", "TRUE", "FALSE", "AND", "OR", "NOT", "PG", "MIME",
           "CRUD", "CSV", "VFX", "PT", "DAY", "HOUR", "WEEK", "MONTH", "YEAR", "YYYY", "MM", "DD"}

fails = []


def fail(f, msg):
    fails.append(f"{f.relative_to(ROOT)}: {msg}")


for f in sorted(CORPUS.rglob("*.md")):
    text = f.read_text()
    for s in secrets:
        if s in text:
            fail(f, f"leaks a secret or host ({len(s)} chars)")
    for pat, what in PATTERNS:
        m = pat.search(text)
        if m and "<" not in m.group(0)[:1]:
            fail(f, f"leaks a {what}: {m.group(0)[:40]}")

    prose = "" if f.name == "INDEX.md" else FENCE_RE.sub("", text)  # INDEX is generated   # payloads and error strings are evidence, not register
    for m in dict.fromkeys(x.lower() for x in BANNED_RE.findall(prose)):
        fail(f, f"banned register {m!r} — state the fact plainly (CLAUDE.md Style)")
    if "\u2014" in prose:
        fail(f, f"{prose.count(chr(0x2014))} em dash(es) — recast as a full stop, a colon, or commas")
    for w in dict.fromkeys(CAPS_RE.findall(TICK_RE.sub("", prose))):
        if w not in CAPS_OK:
            fail(f, f"ALL-CAPS emphasis {w!r} — capitals are for API literals only (CLAUDE.md Style)")

    is_type = f.parent.name in ("field_types", "entity_types")
    if not is_type and (f.parent.name != "findings" or not f.stem[:1].isdigit()):
        continue
    head = re.match(r"---\n(.*?)\n---", text, re.S)
    if not head:
        fail(f, "no frontmatter")
        continue
    scope = re.search(r"^scope:\s*(api|site|project)\s*$", head.group(1), re.M)
    if not scope:
        fail(f, "no scope: api|site|project. api transfers anywhere; site is one Flow PT site; "
                "project is one project inside it")
    elif scope.group(1) == "project" and not re.search(r"^project:\s*\S", head.group(1), re.M):
        fail(f, "scope: project needs a project: key naming which project it was measured on")
    verdict = re.search(r"verdict:\s*(.+)", head.group(1))
    if not verdict:
        fail(f, "no verdict")
    else:
        v = verdict.group(1).strip()
        if v in ("see below", "—", ""):
            fail(f, f"placeholder verdict: {v!r}")
        elif len(v) > VERDICT_MAX:
            fail(f, f"verdict is {len(v)} chars, max {VERDICT_MAX} — move the detail to **Teaches**")
    if not re.search(r"tags:\s*\[[^\]]+\]", head.group(1)):
        fail(f, "no tags")
    wanted = SECTIONS
    if f.parent.name == "field_types":
        wanted = TYPE_SECTIONS
    elif f.parent.name == "entity_types":
        wanted = ENTITY_SECTIONS
    for s in wanted:
        if s not in text:
            fail(f, f"missing section {s}")
    if is_type:
        if "|---" not in text.replace(" ", ""):
            fail(f, "no table — a field type enumerates cases, one row each (CLAUDE.md Style)")
        body = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)
        body = FENCE_RE.sub("", body)
        n = len([ln for ln in body.splitlines()
                 if ln.strip() and not ln.lstrip().startswith(("|", "---"))])
        if n > TYPE_MAX_PROSE:
            fail(f, f"{n} lines of prose, max {TYPE_MAX_PROSE}. Tables and evidence do not count; "
                    f"paragraphs do")
        if text.count("**Verdict**"):
            fail(f, "verdict repeated in the body; it belongs in the frontmatter only")
        continue
    block = re.search(r"\*\*Actual\*\*\s*\n+```\n(.*?)\n```", text, re.S)
    if block and len(block.group(1).splitlines()) > ACTUAL_MAX:
        n = len(block.group(1).splitlines())
        fail(f, f"**Actual** is {n} lines, max {ACTUAL_MAX} — trim to representative rows")
    if text.count("**Verdict**"):
        fail(f, "verdict repeated in the body; it belongs in the frontmatter only")

print("\n".join(fails) if fails else "corpus clean")
sys.exit(1 if fails else 0)
