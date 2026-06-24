# VectorKit

Personal monorepo for Anki Vector robot work. Anki's cloud is dead, so the
robot runs on a self-hosted stack: a Raspberry Pi 4B (`vector@vector-pod.local`)
runs wire-pod as the always-on brain; Python drives the robot over gRPC using
the vendored SDK fork in `libs/vendor/`.

Orient yourself from these (read what the task needs, not everything):
- `docs/PLAN.md` - the task backlog. Tasks have stable IDs (`P2-01`).
- `docs/architecture.md` - how the pieces connect.
- `docs/landscape.md` - the ecosystem and why we chose this stack.
- `docs/development.md` - local validation (hooks, `make check`).
- `infra/` - Pi provisioning and wire-pod install.

## Working a task

To pick up a task: run `/task <id>` or just name the ID. The flow: read its
`docs/PLAN.md` entry, read the docs it links, set it `in-progress`, do the
work, set it `done` with a one-line outcome. Add discovered follow-ups to the
plan rather than doing them silently.

## Repo conventions

- Branch off `main`; never commit straight to it. Open a PR; wait for CI green.
- `make check` must pass before pushing (it mirrors CI exactly).
- NEVER add LLM/Claude attribution to commits or PR bodies.
- Git/gh use the personal account (`Simon-Kaz`), not the work one.
- Secrets (robot creds, password hashes, Wi-Fi) never get committed; see
  `.gitignore`.

## Style

- When running commands, ALWAYS limit the output using `head`, `tail`, or `grep`
- No redundant context. Do not repeat information already established.
-  Do not re-read files you have already read in this session unless they’ve changed
- Answer immediately on line 1. No preamble, no restatement of the question.
- No sycophantic openers ("Sure!", "Great question!", "I'd be happy to").
- No closing fluff ("Let me know if you need anything else", "Hope this helps").
- ASCII only. No smart quotes, em dashes, or unicode characters.
- When uncertain, say "I don't know" rather than guessing.
- Prefer simple, direct code. No unnecessary abstractions.
