# The public example overlay

The site has three reading levels and a public build could only ever show one of them. `corpus.local/`
is gitignored, and `site/README.md` names that as the entire enforcement against a local measurement
reaching production. So the deployed site had nothing at the site or project level, and the two features
the corpus exists to argue for, the overlay and the reading level, were invisible to everyone who had not
cloned the repository and pointed it at their own Flow Production Tracking site.

`corpus.example/` is a committed copy of one site's overlay, reviewed by hand, that the public deploy
reads instead.

## The three directories

| directory | committed | holds | read when |
|---|---|---|---|
| `corpus/` | yes | `scope: api`, true of any Flow PT site | always |
| `corpus.example/` | yes | one site and one project, reviewed before commit | `PUBLIC_OVERLAY_SOURCE=corpus.example` |
| `corpus.local/` | no | whatever `build_overlay.py` last wrote | the default, and every local build |

`corpus.local/` did not change. It is still gitignored, unscrubbed, overwritten by every
`build_overlay.py` run, and incapable of reaching a deployment. The example is a separate directory so
that stays true: what is public is what somebody read and committed, never what a probe last wrote.

## What the site reads

`site/src/lib/site.js` carries two names, because one constant was answering two questions.

| constant | answers | value |
|---|---|---|
| `OVERLAY_DIR` | where should *you* put your own overlay | `corpus.local`, always |
| `OVERLAY_SOURCE_DIR` | which directory did *this build* read | `PUBLIC_OVERLAY_SOURCE`, defaulting to `corpus.local` |

`/how-it-works` quotes the first, because it is instructing a reader who has cloned the repository.
`ScopeSection` quotes the second under every local section, because that is a provenance claim and the
example build would otherwise name a directory its content did not come from.

`PUBLIC_OVERLAY_SOURCE` is read by `site/vite.config.js`, which substitutes it into the bundle as
`__OVERLAY_SOURCE__`. The default lives in that file, so a fresh clone builds with no `.env` of any kind
and an absent variable cannot break the build. `site/vercel.json` sets `corpus.example` under `build.env`,
so the switch lives in the repository rather than in the Vercel dashboard.

`ignoreCommand` is what decides whether a push builds at all, and its exit codes read backwards: **1
builds, 0 skips**. It builds on `main` and skips every other ref, so a branch and a pull request produce
a skipped deployment and no site. The repository is public, so a fork can open a pull request; the skip
is what stops that publishing anything. `git.deploymentEnabled` names `main` as well, which is
redundant and is there to be read.

## Rebuilding the example

    python probes/build_overlay.py --refresh    # rewrites corpus.local/
    # review, then:
    rm -rf corpus.example
    mkdir -p corpus.example/projects
    cp -R corpus.local/site corpus.example/site
    cp -R corpus.local/projects/<id> corpus.example/projects/big-buck-bunny
    python probes/check_corpus.py

The project directory is renamed on the way in. `<id>` is a real project id on a real site; the example
directory is named for the project instead, and the `project:` key inside the files already carries the
display name. `site/README.md` states the directory name is the author's choice.

## The review, before any copy is committed

`probes/check_corpus.py` runs `check_leaks` over `corpus.example/` and nothing else. Secrets, the site
host, emails, tokens and presigned URLs are caught mechanically. The register and shape checks are not
applied: `AD Approval Required` and `Bid - MOD` are display names read off a site, and the ALL-CAPS rule
governs an agent reaching for emphasis.

Everything else is judgment, and the linter cannot make it. Read the copy before committing it and answer
these:

| check | why |
|---|---|
| every enabled `CustomEntityNN` display name | a slot is named by an operator, and an operator names it after the work. `Lenses` and `Location` describe the craft; `Security Scan Report` and `E2E Test Run` describe the studio's own engineering |
| every `sg_` display name in `019_create_fields` | same reason, one level down. A field name can carry a client, a vendor or a tool |
| every vocabulary in `009_status_lists` | a status list enumerates the tools and stages in use |
| the LocalStorage roots in `021_media_resolution` | a mount point is infrastructure |
| the row counts | a count says how much work of that kind the studio does |
| which projects are present | `build_overlay.py` replaces only the tiers it builds. A project dropped from `FPT_PROBE_SAMPLE_PROJECTS` is left on disk, stale, and the site keeps rendering it |

The last row is the one that already bit. Custom entity slots 01 to 07 were disabled on the site and a
rebuild dropped them from the site tier and from the project that was rebuilt. A second project directory
that no longer appeared in `FPT_PROBE_SAMPLE_PROJECTS` was never rewritten and still named four of them.
Check the directory listing against the configured projects, and not only the freshly written files.

## Verifying a build

    PUBLIC_OVERLAY_SOURCE=corpus.example npm run build

Then grep `site/build/` for whatever the review decided to exclude. A miss is silent otherwise: the
overlay renders as ordinary marked sections and nothing about the page says the content should not have
been there.
