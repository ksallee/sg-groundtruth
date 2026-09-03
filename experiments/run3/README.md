# Run 3

The grading material and the seed inventory are deliberately **not here** while the run is in progress.

Arm a is given the whole repository, including `probes/`, the schema inspector, the MCP server and the
slash commands, because that is what someone who clones this actually has. An answer key stored inside
the repository would be part of what that arm can read.

During the run they live in `~/dev/run3-grading/`, which no arm can reach: arm a is scoped to this
repository, arms b and c are scoped to their own directories. They come back here with the result.

`experiments/weekly-report/` stays where it is. It records a previous run and names several of the same
traps. Arm a can read it, and a person who cloned this repository could too, so that is a real advantage
rather than a leak. `RESULT.md` has to say whether arm a used it.
