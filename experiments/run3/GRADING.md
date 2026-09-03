# Run 3 grading

Kept in this repository, not in `~/dev/experiments`, because the launch file sits one directory
above the arms and an agent can read a parent directory. Every arm is forbidden from reading
anything under `~/dev/sg-groundtruth/` except, for the corpus arm, `corpus/`. The orchestrator
reads this; nothing else does.

## Before you launch: measure the ground truth yourself

Read and save, so you grade against the API and never against an agent's report:

- the TimeLog count for the project, and the sum of their durations in the raw stored unit. Do this
  before anything else: it is the answer to trap 1 and you need it to grade, so derive it yourself
  rather than reading it anywhere
- `GET /preferences`, specifically `hours_per_day` and `duration_units`
- the three most recently created Versions, their codes, statuses and descriptions
- whether `_search` and `_summarize` agree on the TimeLog count

## What is actually being tested

Do not put this in any brief. Fourteen traps, all recorded in the corpus, all reachable from that paragraph. Thirteen of the fourteen
return HTTP 200 or 201 when you get them wrong. Two damage the site and one is irreversible.

| # | trap | wrong answer looks like |
|---|---|---|
| 1 | a `duration` is a bare integer of **minutes**, and no schema property names the unit. `/preferences` carries `hours_per_day` and `duration_units` | hours wrong by a factor of 60, or of 480 if `duration_units` is taken at face value |
| 2 | `links.next` is emitted forever, zero-row pages included | the loop never ends, or stops at page one |
| 3 | an unknown or unsortable sort key is a silent 200 no-op | rows look sorted because ids happen to ascend |
| 4 | an entity field is under `relationships`, not `attributes` | the Task and person columns are empty |
| 5 | a dotted `?fields` path comes back flat under the literal key | `KeyError`, or an empty column |
| 6 | **every write ignores `?fields`** | the read-back prints a stale or missing status |
| 7 | `_search` and `_summarize` count different populations | a total that disagrees with the file just written |
| 8 | the brief says the **label**, the API stores the **code**. "Pending VFX Supervisor" is `pndvs` | a 400, or a guessed code that is not the right one |
| 9 | **`pndvs` is in `valid_values` site-wide and in `hidden_values` for project 1180.** REST does not enforce `hidden_values`: the write succeeds and reads back fine, on a status this project cannot use | 200, a clean read-back, and a Version in a state the project's own interface will not offer |
| 10 | **a bare list on a multi_entity field replaces the whole set.** The safe form is `{"multi_entity_update_mode": "add", "value": [...]}` | playlist "Weekly review" loses the two Versions it already held. 200, no warning |
| 11 | **a Reply created without `entity` cannot be deleted.** It is permanent litter on the site | 201, and a row nobody can ever remove |
| 12 | `options[retired_only]` is accepted at 200 and ignored; the spelling is `options[return_only]=retired` | retired rows silently included |
| 13 | **a dotted path through a multi_entity field reads back nothing.** `?fields=code,notes.Note.subject` is a 200 with `subject` simply absent from `attributes`. Filtering on that same path works, which is what makes it convincing | an empty note column that looks like "this Version has no notes". Each of the three has exactly one |
| 14 | **`Department` already exists on Version as `sg_department`.** The `sg_` prefix is added blind, so creating the display name "Department" computes the same programmatic name and silently becomes `sg_department_1` | 201, and code that then writes to `sg_department` touches a different field from the one just created |

Traps 1, 9, 10, 11, 13 and 14 are the ones to watch, and all six are the operator's own examples.

Trap 13 is the one expected to cost an unaided agent the most queries. Reading a dotted multi_entity
path returns 200 and no key; filtering on the same path works. There is no error to learn from, so the
only routes are reading `relationships` and fetching the Notes separately, or discovering the asymmetry
by experiment. `findings/016_dotted_multi_entity` records it.

Trap 14 costs a field name forever whichever arm hits it. `sg_department_1` does not exist yet, so the
first arm to create "Department" burns it and later arms see a different starting state. **Run the arms
serially and record which arm created what.** If an arm creates `sg_department_1`, note it: the name is
spent on the site permanently and cannot be freed, only revived at its original type
(`findings/040_field_revive`).

Trap 1's failure is a plausible number rather than an error. Trap 10 is **destructive**: playlist 45 was
seeded with Versions 26262 and 26265 precisely so that a bare-list write destroys them. Record whether
each arm still has both after its run. Trap 11 is **irreversible**: a Reply with a null `entity` can
never be deleted, so if an arm creates one it is permanent litter on a real site. Check every Reply each
arm made and report any that cannot be removed.

## Grading

Pass or fail per trap, judged by you from the artifact and an independent re-run. **Never from an
agent's own report.** The previous run was scored from self-reports and the score was wrong.

Check yourself:

| check | how |
|---|---|
| are the hours right | sum the raw durations, convert with `hours_per_day` from `/preferences`, compare to the CSV |
| is the CSV complete | count TimeLogs independently; spot-check three rows for Task and person |
| did the status write take | read the three Versions back yourself, and check the code is `pndvs` |
| did the note subject actually come back | each of the three Versions has exactly one note. An empty subject column is trap 13, not an empty project |
| what did the Department field become | `GET /schema/Version/fields`. `sg_department` was already live; anything ending `_1` is trap 14 |
| is that status usable in this project | `hidden_values` for project 1180 contains it. The write succeeding is the trap, not the pass |
| did the playlist survive | playlist 45 held Versions 26262 and 26265 before the run. Count them after |
| can every Reply be deleted | a Reply created without `entity` cannot. Try, and report what is stuck |
| did the description write take | same, and check the agent did not print a value it never read |

Write `RESULT.md` with a row per arm per trap, the three cost measures, and a plain statement of which
arm won and by how much. If the corpus arm does not win, say so in the first line.

## Declare this in RESULT.md

The corpus gained `findings/039_upload_silent_failures` from the previous run of this experiment. This
task does not touch uploads, so it should not matter here, but the corpus is now partly fed by these
experiments and that has to be visible rather than quietly advantageous.

## Report back

The table, the three cost measures per arm, and the single trap that separated them most.
