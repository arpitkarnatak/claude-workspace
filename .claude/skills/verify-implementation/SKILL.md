---
name: verify-implementation
description: Hook-driven check that runs formatters, linters and tests after Claude changes files. It fires only when the current turn changed files, and it blocks the stop with the failure output so Claude fixes it. Use when setting up, tuning or debugging this verification hook.
---

# verify-implementation

Runs as two hooks. It is not called by hand.

| Hook | Command | Job |
|---|---|---|
| `UserPromptSubmit` | `verify.py snapshot` | Hash every file before Claude starts work. |
| `Stop` | `verify.py check` | Compare with the snapshot. If nothing changed, exit 0 and do nothing. |

When files changed, `check` finds the project root of each changed file (nearest `package.json`, `pyproject.toml`, `go.mod`, `Cargo.toml` or `.verify.json`). For each root it runs, in order:

1. Format (writes fixes).
2. Lint (and typecheck for JS).
3. All tests in that project.

On failure it exits 2. The Stop hook then blocks, and Claude sees the output and must fix it. After 3 failed attempts it stops blocking and tells Claude to report the failures to the user. On success the snapshot is refreshed, so the next turn starts clean.

Changes to only `.md`, `.txt` or `.rst` files do not fire the hook.

## Detected commands

- Node: scripts `format`/`fmt`, `lint`, `typecheck`, `test` (runner from the lockfile).
- Python: `ruff format`, `ruff check --fix` (if ruff is configured), `pytest -q`.
- Go: `go fmt`, `go vet`, `go test ./...`.
- Rust: `cargo fmt`, `cargo clippy`, `cargo test`.

Override per project with `<root>/.verify.json`:

```json
{ "format": ["pnpm prettier --write ."], "lint": ["pnpm eslint ."], "test": ["pnpm vitest run"] }
```

## Watched directories

The hook watches the session `cwd`. Work in other directories (for example `~/Desktop/work/qcp`) is invisible unless you set `VERIFY_IMPL_DIRS=/path/a:/path/b` in the environment. For a global setup, copy the `hooks` block from `.claude/settings.json` to `~/.claude/settings.json` and use the absolute script path.

## Debugging

- Snapshots: `~/.claude/verify-implementation/<session_id>.json`.
- Test the check by hand: `echo '{"session_id":"x","cwd":"."}' | python3 scripts/verify.py snapshot`, edit a file, then run the same with `check`.
