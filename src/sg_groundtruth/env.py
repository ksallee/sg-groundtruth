"""`.env.local` loading, for the CLIs and the node alike.

Nothing here writes os.environ: credentials travel as an explicit mapping, so a stray dump of the
process environment cannot leak a key that was only ever passed by hand.
"""
import os
from pathlib import Path

NAME = ".env.local"
ROOT = Path(__file__).resolve().parents[2]


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
