"""`.env.local` loading, for the CLIs and the node alike.

Nothing here writes os.environ: credentials travel as an explicit mapping, so a stray dump of the
process environment cannot leak a key that was only ever passed by hand.
"""
import os
from pathlib import Path

NAME = ".env.local"

# The checkout this file lives in, right whenever the package is used from a clone and wrong the
# moment it is installed: from site-packages, parents[2] is not a repository.
_PKG_ROOT = Path(__file__).resolve().parents[2]


def repo_root(marker=NAME, start=None):
    """Walk up from `start` (default: the working directory) for `marker`, then fall back.

    An installed consumer runs from its own tree, not from this one, so the walk is what lets it
    find its own `.env.local`. A caller that knows better passes `root=` and never reaches here.
    """
    d = Path(start or Path.cwd()).resolve()
    for _ in range(6):
        if (d / marker).exists():
            return d
        if d.parent == d:
            break
        d = d.parent
    return _PKG_ROOT


ROOT = repo_root()


def load(root=None):
    """<root>/.env.local layered over a copy of os.environ.

    A missing file is not an error here — the caller that needs a key learns which one from
    FPT.from_env, which names it without printing it.
    """
    env = dict(os.environ)
    f = Path(root or ROOT) / NAME
    if f.is_file():
        for line in f.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip("'\"")
    return env
