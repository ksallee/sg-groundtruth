"""Version naming conventions: infer one, match it, produce the next.

Where the version number lives is site-specific. A Toolkit-driven site usually carries a real numeric
field (`sg_version_number` or similar) and that is authoritative when present. Many sites do not — this
one has none — and then the version lives inside `code` as a freeform convention that differs per show.

So: use the field if the profile names one, otherwise infer the convention, show it to the operator
with its coverage, and store it as data. Nothing here is hardcoded either way.

This lives here, with the client, because it is knowledge about how a Flow PT site names things —
the same reason `schema.usable_values` does. The node consumes it; it does not own it.

Validated against the reference show, where one pattern covers 99 of 100 codes:

    bunny_030_0090_comp_v002   ->  link=bunny_030_0090  task=comp  version=2

and the code contains its own link entity name in 99 of 100 rows, which is what makes per-link
numbering possible without a structured field.
"""
import re
from collections import Counter

# Ordered: the first pattern that covers the sample wins. Each must name `version`; `link` and `task`
# are optional captures, present when the convention encodes them.
PATTERNS = [
    # {output} is what a stream IS — depth, normals, mask. A graph with several image outputs needs it,
    # or every pass collapses onto one name. {task} is the show's pipeline step, a different thing.
    ("{link}_{task}_{output}_v{version}",
     r"^(?P<link>.+)_(?P<task>[A-Za-z]+)_(?P<output>[A-Za-z0-9]+)_v(?P<version>\d+)$"),
    ("{link}_{output}_v{version}", r"^(?P<link>.+)_(?P<output>[A-Za-z0-9]+)_v(?P<version>\d+)$"),
    ("{link}_{task}_v{version}", r"^(?P<link>.+)_(?P<task>[A-Za-z]+)_v(?P<version>\d+)$"),
    ("{link}_v{version}",        r"^(?P<link>.+)_v(?P<version>\d+)$"),
    ("{link}.v{version}",        r"^(?P<link>.+)\.v(?P<version>\d+)$"),
    ("{link}_{task}.{version}",  r"^(?P<link>.+)_(?P<task>[A-Za-z]+)\.(?P<version>\d+)$"),
    ("{link}-v{version}",        r"^(?P<link>.+)-v(?P<version>\d+)$"),
]


# The same shape, named two ways. Which one it is cannot be read off the string: `comp` in
# bunny_030_0090_comp_v001 is a pipeline step, `depth` in sbx_0020_depth_v001 is a render pass.
# Only the site's Task names can tell them apart, so `infer` takes them when the caller has them.
AS_TASK = {"{link}_{output}_v{version}": "{link}_{task}_v{version}"}


def infer(codes, task_names=()):
    """(template, regex, matched, total) for the pattern that best fits real codes.

    Specificity beats raw coverage. `{link}_v{version}` matches almost everything because a greedy
    {link} swallows whatever precedes the version — it is the least informative pattern and would win
    on count alone, so a pattern that captures more tokens wins any near-tie.

    Returns the best even when coverage is poor: the caller shows the number and lets the operator
    judge, the same way every other inference here works. Coverage is the evidence.
    """
    codes = [c for c in codes if isinstance(c, str) and c.strip()]
    if not codes:
        return None, None, 0, 0
    scored = [(t, rx, sum(1 for c in codes if re.match(rx, c))) for t, rx in PATTERNS]
    best = max(x[2] for x in scored)
    if not best:
        return scored[0][0], scored[0][1], 0, len(codes)
    near = [x for x in scored if x[2] >= best - max(1, best // 10)]
    template, regex, matched = max(near, key=lambda x: (len(re.findall(r"\{(\w+)\}", x[0])), x[2]))

    # Middle token: a Task name the site actually uses, or a render pass?
    lowered = {str(t).lower() for t in task_names}
    if lowered and template in AS_TASK:
        seen = [m.group("output").lower() for m in
                (re.match(regex, c) for c in codes) if m]
        if seen and sum(1 for t in seen if t in lowered) * 2 >= len(seen):
            template = AS_TASK[template]
            regex = dict(PATTERNS)[template]
    return template, regex, matched, len(codes)


def version_field_candidates(schema):
    """Numeric Version fields that could be the version number, for the operator to choose from.

    Proposed, never auto-adopted: `sg_first_frame` is numeric too, and picking wrong would silently
    misnumber every publish.
    """
    return sorted(k for k, v in (schema or {}).items()
                  if v.get("data_type", {}).get("value") in ("number", "float")
                  and "version" in k.lower() and "transcoding" not in k.lower())


def next_number(existing_numbers):
    """Next value for a real version-number field. Authoritative when the site has one."""
    ns = [int(n) for n in existing_numbers if isinstance(n, (int, float))]
    return max(ns, default=0) + 1


# What each token may contain when a template is turned into a concrete regex.
TOKEN_RX = {"link": r".+?", "task": r"[A-Za-z][A-Za-z0-9]*", "output": r".+?", "version": r"\d+"}


def regex_from_template(template, link=""):
    """A concrete regex for one template, anchoring {link} literally when the link is known.

    Without that anchor a non-greedy {link} swallows part of {output}: `sbx_0020_depth_v001` parsed as
    link='sbx', output='0020_depth', so numbering for 'depth' never found its own history and every
    publish produced v001 again — two Versions, one code.
    """
    out, i = "", 0
    for m in re.finditer(r"\{(\w+)\}", template):
        out += re.escape(template[i:m.start()])
        name = m.group(1)
        out += re.escape(link) if (name == "link" and link) else f"(?P<{name}>{TOKEN_RX.get(name, '.+?')})"
        i = m.end()
    return "^" + out + re.escape(template[i:]) + "$"


def parse(code, regex):
    m = re.match(regex, code or "")
    if not m:
        return None
    d = m.groupdict()
    d["version"] = int(d["version"])
    return d


def width(regex, codes):
    """Zero-padding actually in use, so v001 does not become v1 on the next publish."""
    ns = [re.match(regex, c).group("version") for c in codes if re.match(regex, c)]
    return Counter(len(n) for n in ns).most_common(1)[0][0] if ns else 3


def next_code(template, regex, existing, link="", task="", output=""):
    """The next code for one link, following the convention the site already uses.

    `existing` is every code already on that link. Numbering is per link AND per output: two shots
    each have their own v001, and a depth pass does not count a normals pass as history.
    """
    # Anchored on this link, so `depth` finds its own history and not another output's.
    rx = regex_from_template(template, link) if template else regex
    kept = [c for c in existing
            if (p := parse(c, rx)) and (not output or p.get("output") == output)]
    n = max((parse(c, rx)["version"] for c in kept), default=0) + 1
    w = width(rx, kept) if kept else width(regex, existing)
    out = template.replace("{version}", str(n).zfill(w))
    return (out.replace("{link}", link or "").replace("{task}", task or "")
               .replace("{output}", output or ""))


def describe(template, regex, matched, total):
    pct = (100 * matched // total) if total else 0
    return f"{template}  ({matched}/{total} of recent codes, {pct}%)"
