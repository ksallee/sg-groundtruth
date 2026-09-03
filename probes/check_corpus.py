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
# corpus.example/ is a reviewed copy of one site's overlay, committed so the public deploy has
# something to show at the site and project reading levels. It is public, so it gets the leak
# checks. It is measured output rather than written prose, so it gets neither the register checks
# nor the shape ones: `AD Approval Required` and `Bid - MOD` are display names read off a site,
# and the ALL-CAPS rule governs an agent reaching for emphasis. See docs/example-overlay.md.
EXAMPLE = ROOT / "corpus.example"
# experiments/ holds committed artifacts of runs made against a real site: scripts, notes and the
# grader's ground truth. Same leak checks, same reason. Their prose is a record of what happened
# rather than corpus writing, so the register and shape checks do not apply.
EXPERIMENTS = ROOT / "experiments"
VERDICT_MAX = 200
# A verdict is the surprise, which is wrong in a list of 24 types. Every card in the two
# matrices also says plainly what the thing is, and the site's list pages render that.
SUMMARY_MAX = 100
# `scope:` says whether a claim transfers; `measured:` says where the evidence came from. A reader
# on their own site cannot weigh recorded output without it, and a `scope: api` finding still rests
# on one run in one place.
MEASURED_MAX = 120
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
           "CRUD", "CSV", "VFX", "PT", "DAY", "HOUR", "WEEK", "MONTH", "YEAR", "YYYY", "MM", "DD",
           "HTML", "XML", "EDL", "MP4", "PNG", "JPG", "TIF", "EXR", "MOV", "OTIO"}

# The site generates its filter matrix from these three columns, so they are a contract, not a habit.
FILTER_COLS = ("operator", "value", "matches")
SEP_RE = re.compile(r"^\|[\s\-:|]*-[\s\-:|]*\|$")

fails = []


def fail(f, msg):
    fails.append(f"{f.relative_to(ROOT)}: {msg}")


def filter_heads(text):
    """Header cells of every table in the **Filter** section, outermost first."""
    m = re.search(r"^\*\*Filter\*\*.*?(?=^\*\*|\Z)", text, re.M | re.S)
    if not m:
        return []
    lines = m.group(0).splitlines()
    return [[c.strip().lower() for c in ln.strip().strip("|").split("|")]
            for ln, nxt in zip(lines, lines[1:])
            if ln.startswith("|") and SEP_RE.match(nxt.strip())]


def check_leaks(f, text):
    """What must not be in any committed file, written or measured."""
    for s in secrets:
        if s in text:
            fail(f, f"leaks a secret or host ({len(s)} chars)")
    for pat, what in PATTERNS:
        m = pat.search(text)
        if m and "<" not in m.group(0)[:1]:
            fail(f, f"leaks a {what}: {m.group(0)[:40]}")


def check_register(f, text):
    """How an agent is allowed to write. Prose only; a measured value is not prose."""
    prose = "" if f.name == "INDEX.md" else FENCE_RE.sub("", text)  # INDEX is generated   # payloads and error strings are evidence, not register
    for m in dict.fromkeys(x.lower() for x in BANNED_RE.findall(prose)):
        fail(f, f"banned register {m!r} — state the fact plainly (CLAUDE.md Style)")
    if "\u2014" in prose:
        fail(f, f"{prose.count(chr(0x2014))} em dash(es) — recast as a full stop, a colon, or commas")
    for w in dict.fromkeys(CAPS_RE.findall(TICK_RE.sub("", prose))):
        if w not in CAPS_OK:
            fail(f, f"ALL-CAPS emphasis {w!r} — capitals are for API literals only (CLAUDE.md Style)")


for root in (EXAMPLE, EXPERIMENTS):
    if not root.is_dir():
        continue
    for f in sorted(root.rglob("*")):
        if f.is_file() and f.suffix in (".md", ".py", ".txt", ".csv"):
            check_leaks(f, f.read_text(errors="replace"))

for f in sorted(CORPUS.rglob("*.md")):
    text = f.read_text()
    check_leaks(f, text)
    check_register(f, text)

    is_type = f.parent.name in ("field_types", "entity_types")
    is_recipe = f.parent.name == "recipes"
    if not is_type and not is_recipe and (f.parent.name != "findings" or not f.stem[:1].isdigit()):
        continue
    head = re.match(r"---\n(.*?)\n---", text, re.S)
    if not head:
        fail(f, "no frontmatter")
        continue
    measured = re.search(r"^measured:\s*(\S.*?)\s*$", head.group(1), re.M)
    if not measured:
        fail(f, "no measured: where the evidence was taken. A sample project, the sandbox project, "
                "site-wide, or unrecorded when the probe does not say")
    elif len(measured.group(1)) > MEASURED_MAX:
        fail(f, f"measured is {len(measured.group(1))} chars, max {MEASURED_MAX} — name the place "
                f"and the sample size, nothing else")
    if is_recipe:
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
    if is_type:
        summary = re.search(r"^summary:\s*(.*)$", head.group(1), re.M)
        if not summary or not summary.group(1).strip():
            fail(f, "no summary: one sentence saying what the thing is and what it is for, "
                    "in the plainest words available")
        elif len(summary.group(1).strip()) > SUMMARY_MAX:
            fail(f, f"summary is {len(summary.group(1).strip())} chars, max {SUMMARY_MAX} — "
                    f"the detail belongs in the verdict")
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
        if f.parent.name == "field_types":
            # A type the API refuses to filter enumerates no operators and so has no matrix;
            # its two-column list of refusals is not one, and nothing is checked there.
            matrix = [h for h in filter_heads(text) if len(h) >= 3]
            if matrix and not any(tuple(h[:3]) == FILTER_COLS for h in matrix):
                found = " | ".join(matrix[0][:3])
                fail(f, f"**Filter** matrix heads with | {found} | — one row per operator, under "
                        f"| operator | value | matches |, then any extra column")
        continue
    block = re.search(r"\*\*Actual\*\*\s*\n+```\n(.*?)\n```", text, re.S)
    if block and len(block.group(1).splitlines()) > ACTUAL_MAX:
        n = len(block.group(1).splitlines())
        fail(f, f"**Actual** is {n} lines, max {ACTUAL_MAX} — trim to representative rows")
    if text.count("**Verdict**"):
        fail(f, "verdict repeated in the body; it belongs in the frontmatter only")

print("\n".join(fails) if fails else "corpus clean")
sys.exit(1 if fails else 0)
