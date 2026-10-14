# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A Claude Code workspace, not an application. It has no build system, tests, or package manifest, and it is not a git repository. It holds project-level Claude configuration only:

- `.claude/skills/ste-writing/`: the main project skill (see below).
- `.claude/skills/bump-semver/`: manual-only skill (`disable-model-invocation`). Bumps major, minor, or patch in the version file of the current stack. It takes an optional `[major|minor|patch]` argument.
- `.claude/skills/verify-implementation/`: backs the hooks in `.claude/settings.json` (see below).
- `.claude/settings.json`: project hooks.
- `.mcp.json`: project MCP config. It is currently empty.

## Verification hooks

`.claude/settings.json` runs `verify-implementation/scripts/verify.py` on two events. `UserPromptSubmit` runs `snapshot` and `Stop` runs `check`. The check fires only when the turn changed files. It runs formatters, linters and tests, and it blocks the stop with the failure output so you must fix the failures. Read `verify-implementation/SKILL.md` before you change the hook behavior.

Other work happens in sibling directories (for example `~/Desktop/work/qcp`, added as a working directory).

## ste-writing skill

Rewrites prose (docs, READMEs, PR text, error messages, never code) into ASD-STE100 Simplified Technical English. Entry point is `.claude/skills/ste-writing/SKILL.md`, which holds the rules, the two modes (strict and STE-flavored), and the guards.

- `references/ste-recurring-errors.md`: the standard's list of the 39 most frequent writer errors, used in strict mode.
- `references/always-on.md`: a paste-ready block that applies the mechanical rules to every reply. It is meant for profile preferences, a custom style, or a CLAUDE.md, not for this file by default.
- `scripts/ste-lint.py`: the linter. The skill requires a lint run before text is called clean.

Lint commands (run from `.claude/skills/ste-writing/`):

```
python3 scripts/ste-lint.py draft.md            # flavored target: under 2.5 violations per 100 words
python3 scripts/ste-lint.py --strict draft.md   # strict target: under 1.5 per 100 words
```

Other options: `--json` gives full output, `--fail-over N` exits 1 when the worst file scores above N, a glob pattern lints several files, and with no file argument the linter reads stdin.

Editing the skill:

- Word lists in `ste-lint.py` (`BANNED`, `STRICT_BANNED`, `PHRASAL`, `MARKETING`, `MODAL_HEDGE`) must stay consistent with the rules in `SKILL.md`. A rule change usually needs both files updated.
- The linter matches strings. It cannot tell a banned word that text uses from one that text quotes. `noun_train` and `em_dash` are markers and stay out of the total score.
- Bump `SCORE_VERSION` in `ste-lint.py` when the scoring changes, because totals from different versions are not comparable.
- The house rule against em dashes is not part of the ASD standard. Keep it in both the rules and the linter.
