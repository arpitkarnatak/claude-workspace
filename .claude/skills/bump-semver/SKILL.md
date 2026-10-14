---
name: bump-semver
description: Bump the project version by major, minor, or patch in the version file of the current stack (package.json, Cargo.toml, pyproject.toml, and so on). Asks the user which kind of change it is when no argument is given.
argument-hint: "[major|minor|patch]"
disable-model-invocation: true
allowed-tools: Read, Edit, Glob, Grep, Bash(ls:*), Bash(git status:*), Bash(git describe:*), Bash(cargo update:*), Bash(npm install:*)
---

# /bump-semver

Bump the semantic version of the project in the current working directory.

## 1. Choose the bump type

Argument given: `$ARGUMENTS`

- If the argument is exactly `major`, `minor`, or `patch`, use it. Go to step 2.
- Otherwise (empty or unknown), ask the user with AskUserQuestion. Question: "What kind of change is this?" Use these three options:
  - **patch**: backward-compatible bug fixes (1.2.3 -> 1.2.4)
  - **minor**: new backward-compatible functionality (1.2.3 -> 1.3.0)
  - **major**: breaking changes (1.2.3 -> 2.0.0)

## 2. Find the version file

Look in the current working directory (not parent directories) for these files, in this order. Use the first one that holds a version field.

| Stack | File | Version field |
|---|---|---|
| Node | `package.json` | top-level `"version"` |
| Rust | `Cargo.toml` | `version` under `[package]`, or under `[workspace.package]` for a workspace |
| Python | `pyproject.toml` | `version` under `[project]` or `[tool.poetry]` |
| Python | `setup.py` or `setup.cfg` | `version=` / `version =` |
| Python | `__version__` in `<package>/__init__.py` or `_version.py` | the string value |

`requirements.txt` lists dependencies and has no project version. If it is the only Python file found, tell the user, then ask which file holds the version. Never edit a dependency line.

If more than one stack is present (for example `package.json` and `Cargo.toml`), ask the user which one to bump. If no file is found, say so and stop.

## 3. Compute the new version

1. Read the current version. It must match `MAJOR.MINOR.PATCH`, with an optional pre-release or build suffix.
2. If the version has a suffix (`1.2.3-beta.1`, `1.2.3+build5`) or does not parse, stop and ask the user what to do. Do not guess.
3. Apply the bump:
   - `major`: MAJOR + 1, MINOR = 0, PATCH = 0
   - `minor`: MINOR + 1, PATCH = 0
   - `patch`: PATCH + 1
4. Treat a `0.x.y` version as normal. Do not special-case it.

## 4. Apply the change

- Use Edit to change only the version value. Keep all other text and formatting unchanged.
- In a Cargo workspace where members use `version.workspace = true`, change only `[workspace.package]`.
- Sync the lock file if one exists, without upgrading dependencies:
  - `package-lock.json`: edit the top-level `"version"` and `packages[""].version` to match. Do not run `npm install`.
  - `Cargo.lock`: edit the `version` of the root package entry only. If this is unclear, tell the user to run `cargo check`.
  - `poetry.lock` and `uv.lock`: do not edit them. Tell the user if a refresh is needed.

## 5. Report

Give one short result: the file changed, `old -> new`, and any lock file touched. Do not commit, tag, or push. If the user wants a commit or git tag, they must ask for it.
