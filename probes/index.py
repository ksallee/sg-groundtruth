"""Regenerate corpus/INDEX.md — the cheap layer an agent reads before opening anything."""
import re
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINDINGS = ROOT / "corpus" / "findings"
RECIPES = ROOT / "corpus" / "recipes"


def parse(f, summary_key):
    m = re.match(r"---\n(.*?)\n---", f.read_text(), re.S)
    if not m:
        return None
    head = m.group(1)
    tags = re.search(r"tags:\s*\[(.*?)\]", head)
    summary = re.search(rf"{summary_key}:\s*(.+)", head)
    return {
        "slug": f.stem,
        "tags": [t.strip() for t in (tags.group(1) if tags else "").split(",") if t.strip()],
        "summary": summary.group(1).strip() if summary else "—",
    }


def collect(d, key):
    return sorted(filter(None, (parse(f, key) for f in d.glob("[0-9]*.md"))), key=lambda e: e["slug"])


def main():
    findings = collect(FINDINGS, "verdict")
    recipes = collect(RECIPES, "intent")

    by_tag = defaultdict(list)
    for kind, items in (("finding", findings), ("recipe", recipes)):
        for e in items:
            for t in e["tags"]:
                by_tag[t].append(f"{e['slug']} ({kind})")

    out = [
        "# Corpus index", "",
        "Read this first. Open an entry only when its one-liner does not already answer the question.", "",
        "**Findings** — how the API behaves. **Recipes** — a verified call and its real response.", "",
        "## Findings", "",
    ]
    out += [f"- **{e['slug']}** — {e['summary']}  \n  `{' '.join(e['tags'])}`" for e in findings] or ["- none yet"]
    out += ["", "## Recipes", ""]
    out += [f"- **{e['slug']}** — {e['summary']}  \n  `{' '.join(e['tags'])}`" for e in recipes] or ["- none yet"]
    out += ["", "## By tag", ""]
    out += [f"- **{t}** — {', '.join(by_tag[t])}" for t in sorted(by_tag)]

    (ROOT / "corpus" / "INDEX.md").write_text("\n".join(out) + "\n")
    print(f"indexed {len(findings)} findings, {len(recipes)} recipes, {len(by_tag)} tags")


if __name__ == "__main__":
    main()
