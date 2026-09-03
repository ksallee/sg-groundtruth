---
description: Set up this repository against the operator's own Flow PT site, first run
---

Point: $ARGUMENTS

First run. The operator has cloned this and has a Flow Production Tracking site. At the end they have
their own corpus on localhost and know which command to reach for next. Ask before you measure, and never
print the key.

## 1. Say what this is, in three lines

The shipped corpus is the API. The local overlay is their site and their projects, gitignored, and it
never leaves the machine. Every entry names the probe that made it, so any claim re-runs.

Then ask whether they want the whole run or one part. Do not proceed silently.

## 2. Check the toolchain before asking for a credential

| check | fix if missing |
|---|---|
| `python3.11 --version` | any 3.11; the probes are stdlib plus `requests` |
| `.venv` present | `python3.11 -m venv .venv && source .venv/bin/activate && pip install requests` |
| `node --version` | only needed for the site, not for the probes |
| `.env.local` present | `cp .env.local.example .env.local` |

A credential asked for before the venv exists is a credential the operator typed twice.

## 3. Ask for the five values, and say what each is for

Never guess one, and never read `.env.local` back to them.

| key | ask |
|---|---|
| `FPT_API_SITE_URL` | the site, `https://<yours>.shotgrid.autodesk.com` |
| `FPT_API_SCRIPT_NAME` | a script user. Web interface, Admin, Scripts |
| `FPT_API_API_KEY` | its key. Gitignored, never printed, never echoed into a report |
| `FPT_PROBE_SAMPLE_PROJECTS` | projects a probe may **read**. Names or ids, most interesting first |
| `FPT_PROBE_SANDBOX_PROJECT` | the one project a probe may **write** into |

The last two are the ones an operator does not expect and the two that decide whether the run is safe.
Say plainly that everything defaults to read-only and that `--write` touches the sandbox alone.

## 4. Prove the credential before measuring anything

    python probes/001_auth.py
    python probes/002_schema.py

`001` failing is a credential problem and nothing else. `002` is the expensive call and what every later
probe reads. Stop on either and fix it before going on.

## 5. Ask the schema what their site calls things

    PYTHONPATH=src python -m sg_groundtruth.schema entities --custom
    PYTHONPATH=src python -m sg_groundtruth.schema --project N statuses Version

Read the custom entity list back to them by display name. This is the moment they find out their
`CustomEntity07` is called something, and it is the fact that makes the rest of the run concrete.

## 6. Build their overlay

    python probes/build_overlay.py

Read-only, re-runnable, about a minute cold. It replaces each tier it builds and **leaves alone any it
does not**, so a project dropped from `FPT_PROBE_SAMPLE_PROJECTS` stays on disk stale. Say so, and list
`corpus.local/projects/` against what they configured.

## 7. Show them their own documentation

    cd site && npm install && npm run dev

Open `http://localhost:5173`. Point at the reading level switch in the header: it is the whole payoff of
the previous step, and it is not rendered at all when the overlay is empty.

## 8. Hand them the list, and stop

Four commands, what each is for, one line each. Do not run any of them.

| command | when |
|---|---|
| `/probe <question>` | the docs are silent or wrong about something and you need to know. One question per probe |
| `/recipe <task>` | you made a call work and want the call plus its real response recorded |
| `/inspect-site [project]` | you are wiring a consumer to this site and need a profile with the evidence beside it |
| `/sg-groundtruth-adopt <path>` | you have code that already calls this API and want what it knows in the corpus |

Then ask one question and let them answer it: **what did this API do last week that surprised you?** That
is a probe, and it is the fastest way to show them what the repository is for.

## Never

| never | why |
|---|---|
| print, echo or paste the key | it is gitignored for a reason and a transcript is not |
| pass `--write` during setup | nothing on a first run needs it |
| hardcode a project id into a probe | `_lib.sample_projects` and `_lib.sandbox_id` resolve them |
| commit `corpus.local/` | it is the enforcement, see `docs/example-overlay.md` |
| write a corpus entry from this command | a probe prints and an agent judges. Setup measures nothing new |
