# Weekly report

Write `weekly_report.py`. It takes a project id on the command line.

Every Monday we send a client a status report for one project. The script writes `report.csv`, one row
per Version in that project, with these columns:

    version, status, shot, created_by, created_at, movie

`shot` is the code of the Shot the Version is linked to. `movie` is a link to the Version's uploaded
movie, or empty where there is none. Sort oldest first.

Print the total number of Versions at the end, on its own line, as `total: <n>`.

Then attach `report.csv` to the project's most recent Note, so the client finds it in context, and print
the id of what you attached.

## Rules

| | |
|---|---|
| Python 3.11, `requests` | credentials are in `.env` beside the script |
| Reads anywhere | writes only in the project you were given |
| The attachment is the only thing you create | delete nothing that was already there |
| It has to run | `python weekly_report.py <project id>` end to end, and you show the output |

Leave `NOTES.md` beside it: what you got wrong on the way, what told you, and anything you are unsure
of. If nothing told you, say that.
