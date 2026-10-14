# Claude workspace

This workspace holds project-level Claude configuration. It is not an application. See [CLAUDE.md](CLAUDE.md) for the layout.

## Update the skills for your tech stack

Two skills are stack-specific. Before you use this workspace on a new project, update them to match the tech stack of that project.

| Skill | Why it depends on the stack | What to update |
|---|---|---|
| [verify-implementation](.claude/skills/verify-implementation/SKILL.md) | It runs the formatter, linter and test commands of the stack. | The detection and commands in `scripts/verify.py`. Or add a `.verify.json` file in the project root. |
| [bump-semver](.claude/skills/bump-semver/SKILL.md) | It edits the version file and lock file of the stack. | The version file table (step 2), the lock file rules (step 4) and `allowed-tools` in the front matter. |

### verify-implementation

The skill detects Node, Python, Go and Rust projects. If your stack is different, or your project uses other commands, do one of these:

- Add `<project root>/.verify.json` to override the commands for one project:

  ```json
  { "format": ["pnpm prettier --write ."], "lint": ["pnpm eslint ."], "test": ["pnpm vitest run"] }
  ```

- Edit `scripts/verify.py` to add a new stack, or to change the default commands.
- Set `VERIFY_IMPL_DIRS=/path/a:/path/b` if you work in directories outside the session `cwd`.

Read `SKILL.md` of the skill before you change the hook behavior.

### bump-semver

The skill supports `package.json`, `Cargo.toml`, `pyproject.toml`, `setup.py`, `setup.cfg` and `__version__` in Python packages. For a different stack (for example `pom.xml`, `build.gradle`, `go.mod` tags or a `VERSION` file):

1. Add the file and the version field to the table in step 2.
2. Add the lock file rule in step 4, if the stack has a lock file.
3. Add the commands the stack needs to `allowed-tools`, for example `Bash(mvn:*)`.
4. Remove the stacks that your project does not use, to keep the skill short.

## Check your changes

After you update a skill, test it on a small project of the target stack:

- `verify-implementation`: run `verify.py snapshot`, edit a file, then run `verify.py check`. See the Debugging section of its `SKILL.md`.
- `bump-semver`: run `/bump-semver patch` and make sure that only the version value changes.
