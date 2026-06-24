---
description: Load a task from docs/PLAN.md by ID and start work on it
argument-hint: <task-id>  (e.g. P2-01)
---

You are picking up task `$1` from this repo's plan. Work from a cold start;
do not assume prior conversation context.

1. Read `docs/PLAN.md` and find the entry whose ID is `$1`. If `$1` is empty
   or no entry matches, list the `todo`/`in-progress` task IDs with their
   one-line goals and stop for the user to choose.
2. Read every file the task entry links to (its `Files:`/`Detail:` paths) plus
   anything they reference that you need. Do NOT read the whole repo.
3. If the task is `blocked` or depends on an unfinished task, or needs a
   physical action only the user can do (e.g. handling the robot), say so and
   confirm the user is ready before proceeding.
4. Set the task status to `in-progress` in `docs/PLAN.md`.
5. Do the work, following the repo conventions in CLAUDE.md (branch, run
   `make check`, open a PR per the git workflow).
6. When the task's "Done when" criteria are met, set the status to `done` and
   append a one-line outcome (e.g. the PR number) to the entry.

Report what you did against the task's acceptance criteria. If you discover
follow-up work, add it to the relevant phase or the parking lot in
`docs/PLAN.md` rather than doing it silently.
