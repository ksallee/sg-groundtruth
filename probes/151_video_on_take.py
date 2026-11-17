"""Q: can a Version's `entity` be a custom entity row, and is a video Attachment (`.mp4` H.264, `.mov`
HEVC) transcoded or thumbnailed? What do the same files become on `Version.sg_uploaded_movie`?

sg-onset holds a take's photos as Attachments in a multi_entity field on a custom entity (probes 123,
134) and wants video there too, uploaded from a browser. Probe 022 measured a `.mov` on
`sg_uploaded_movie`; nothing measured video as a plain Attachment, nor HEVC, which is what an iPhone
or iPad records by default.

`Version.entity` is also set to a new row on every enabled custom slot, in `valid_types` or not, and
the slot's multi_entity fields to Version are read for the link.

Builds four seconds of 1280x720 24 fps bars with a 440 Hz AAC tone, twice: H.264 in `.mp4` and HEVC
(`hvc1`) in `.mov`. Each goes up as an Attachment on the take's field and on its own Version whose
`entity` is the take, then every media field is polled until it settles (`_media.watch`) and the
stored bytes and the transcodes are read back through ffprobe.

Writes in the sandbox, behind `--write`: one take row, one row per custom slot, a Version on each,
the Attachments and the server's transcodes, all deleted on exit. Needs `ffmpeg` and `ffprobe`.
`--hold` keeps them that long before cleanup, for a person to open them in the web interface.

    python probes/151_video_on_take.py --write [--hold <seconds>]
"""
import sys

import _lib
import _media

env = _lib.load_env()
c = _lib.client()
if not _lib.writes_allowed():
    raise SystemExit("probe 151 writes; run with --write")
HOLD = int(sys.argv[sys.argv.index("--hold") + 1]) if "--hold" in sys.argv else 0
rows = []


def out(s=""):
    rows.append(str(s))
    print(s, flush=True)


_media.run(c, env, "zzprobe_151", ["h264.mp4", "hevc.mov"], out, every_slot=True, hold=HOLD)
_lib.emit("151_video_on_take", "\n".join(rows), env)
