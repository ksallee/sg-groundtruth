"""Q: what does the server make of audio, `.m4a` (AAC) and `.webm` (Opus), as an Attachment and as
`Version.sg_uploaded_movie`: a transcode, which stored `content_type`, a thumbnail?

sg-onset records sound notes on set: Safari's MediaRecorder writes AAC in `.m4a`/`.mp4`, Chrome's
writes Opus in `.webm`. Probe 151 measures video the same way; this is the audio half.

Builds four seconds of a 440 Hz tone, twice: AAC in `.m4a` and Opus in `.webm`. Each goes up as an
Attachment on the take's field and on its own Version whose `entity` is the take, then every media
field is polled until it settles (`_media.watch`) and the stored bytes and transcodes are read back
through ffprobe.

Writes in the sandbox, behind `--write`: one take row, three Versions, their Attachments and the
server's transcodes, all deleted on exit. Needs `ffmpeg` and `ffprobe`. `--hold` keeps them that
long before cleanup, for a person to open them in the web interface.

    python probes/152_audio_on_take.py --write [--hold <seconds>]
"""
import sys

import _lib
import _media

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 152 writes; run with --write")
HOLD = int(sys.argv[sys.argv.index("--hold") + 1]) if "--hold" in sys.argv else 0
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


_media.run(c, env, "zzprobe_152", ["aac.m4a", "opus.webm"], out, hold=HOLD)
_lib.emit("152_audio_on_take", "\n".join(rows), env)
