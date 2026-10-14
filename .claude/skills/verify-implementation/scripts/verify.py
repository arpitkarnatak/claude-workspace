#!/usr/bin/env python3
"""verify-implementation hook.

  verify.py snapshot   UserPromptSubmit hook: record file hashes before Claude works.
  verify.py check      Stop hook: if files changed since the snapshot, run format,
                       lint and tests for each affected project. Exit 2 on failure
                       so Claude sees the output and fixes it. Exit 0 and print
                       nothing when no file changed.

Extra directories to watch (colon separated): env VERIFY_IMPL_DIRS.
Per-project override: <root>/.verify.json  {"format": [...], "lint": [...], "test": [...]}
"""
import hashlib, json, os, shlex, shutil, subprocess, sys
from pathlib import Path

STATE_DIR = Path.home() / ".claude" / "verify-implementation"
MAX_ATTEMPTS = 3
CMD_TIMEOUT = 600
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
             "target", ".next", ".turbo", ".pytest_cache", ".ruff_cache", ".mypy_cache"}
DOC_EXT = {".md", ".txt", ".rst"}
MANIFESTS = ["package.json", "pyproject.toml", "go.mod", "Cargo.toml", ".verify.json"]
MAX_HASH_SIZE = 2_000_000


def watch_dirs(cwd):
    dirs = [Path(cwd)]
    for d in filter(None, os.environ.get("VERIFY_IMPL_DIRS", "").split(":")):
        dirs.append(Path(d).expanduser())
    return [d for d in dirs if d.is_dir()]


def list_files(base):
    try:
        out = subprocess.run(["git", "ls-files", "-co", "--exclude-standard"], cwd=base,
                             capture_output=True, text=True, timeout=30)
        if out.returncode == 0:
            return [base / p for p in out.stdout.splitlines() if (base / p).is_file()]
    except (OSError, subprocess.SubprocessError):
        pass
    files = []
    for dp, dn, fn in os.walk(base):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        files += [Path(dp) / f for f in fn]
    return files


def fingerprint(base):
    snap = {}
    for f in list_files(base):
        if SKIP_DIRS & set(f.parts):
            continue
        try:
            st = f.stat()
            if st.st_size > MAX_HASH_SIZE:
                snap[str(f)] = f"{st.st_size}:{st.st_mtime_ns}"
            else:
                snap[str(f)] = hashlib.sha1(f.read_bytes()).hexdigest()
        except OSError:
            continue
    return snap


def snapshot_all(cwd):
    snap = {}
    for d in watch_dirs(cwd):
        snap.update(fingerprint(d))
    return snap


def state_path(session):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    return STATE_DIR / f"{session or 'default'}.json"


def load_state(session):
    try:
        return json.loads(state_path(session).read_text())
    except (OSError, ValueError):
        return None


def save_state(session, baseline, attempts=0):
    state_path(session).write_text(json.dumps({"baseline": baseline, "attempts": attempts}))


def find_root(path):
    for p in [path.parent, *path.parent.parents]:
        if any((p / m).exists() for m in MANIFESTS):
            return p
    return None


def pkg_runner(root):
    for lock, pm in [("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"),
                     ("bun.lockb", "bun"), ("bun.lock", "bun")]:
        if (root / lock).exists():
            return pm
    return "npm"


def detect(root):
    """Return {"format": [...], "lint": [...], "test": [...]} shell commands."""
    cfg = root / ".verify.json"
    if cfg.exists():
        try:
            c = json.loads(cfg.read_text())
            return {k: c.get(k, []) for k in ("format", "lint", "test")}
        except ValueError:
            pass
    cmds = {"format": [], "lint": [], "test": []}
    if (root / "package.json").exists():
        try:
            scripts = json.loads((root / "package.json").read_text()).get("scripts", {})
        except ValueError:
            scripts = {}
        pm = pkg_runner(root)
        run = f"{pm} run" if pm != "yarn" else "yarn"
        for kind, names in (("format", ["format", "fmt"]),
                            ("lint", ["lint", "typecheck", "type-check"]),
                            ("test", ["test"])):
            for n in names:
                if n in scripts and "no test specified" not in scripts[n]:
                    cmds[kind].append(f"{run} {n}")
                    if kind == "test":
                        break
    pyproj = root / "pyproject.toml"
    if pyproj.exists():
        text = pyproj.read_text()
        if shutil.which("ruff") and ("[tool.ruff" in text or (root / "ruff.toml").exists()):
            cmds["format"].append("ruff format .")
            cmds["lint"].append("ruff check --fix .")
        if shutil.which("pytest") and ("[tool.pytest" in text or (root / "tests").is_dir()):
            cmds["test"].append("pytest -q")
    if (root / "go.mod").exists() and shutil.which("go"):
        cmds["format"].append("go fmt ./...")
        cmds["lint"].append("go vet ./...")
        cmds["test"].append("go test ./...")
    if (root / "Cargo.toml").exists() and shutil.which("cargo"):
        cmds["format"].append("cargo fmt")
        cmds["lint"].append("cargo clippy -- -D warnings")
        cmds["test"].append("cargo test")
    return cmds


def run(cmd, cwd):
    try:
        p = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True,
                           timeout=CMD_TIMEOUT)
        return p.returncode, (p.stdout + p.stderr).strip()
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {CMD_TIMEOUT}s"


def tail(text, n=60):
    lines = text.splitlines()
    return "\n".join((["... (truncated)"] if len(lines) > n else []) + lines[-n:])


def cmd_snapshot(data):
    save_state(data.get("session_id"), snapshot_all(data.get("cwd") or os.getcwd()))
    return 0


def cmd_check(data):
    session = data.get("session_id")
    cwd = data.get("cwd") or os.getcwd()
    state = load_state(session)
    if state is None:
        return 0  # no snapshot: cannot tell what changed, so do not fire
    current = snapshot_all(cwd)
    baseline = state["baseline"]
    changed = [p for p, h in current.items() if baseline.get(p) != h]
    changed += [p for p in baseline if p not in current]
    changed = [Path(p) for p in changed if Path(p).suffix not in DOC_EXT]
    if not changed:
        return 0

    roots = sorted({r for r in (find_root(p) for p in changed) if r})
    failures = []
    for root in roots:
        for kind, cmds in detect(root).items():
            for cmd in cmds:
                code, out = run(cmd, root)
                if code != 0:
                    failures.append(f"[{kind}] {root}$ {cmd} (exit {code})\n{tail(out)}")
    attempts = state.get("attempts", 0) + 1
    if not failures:
        save_state(session, snapshot_all(cwd))  # includes formatter edits
        return 0
    if attempts >= MAX_ATTEMPTS:
        save_state(session, snapshot_all(cwd))
        print(f"verify-implementation: still failing after {MAX_ATTEMPTS} attempts. "
              "Stop and report these failures to the user:\n\n" + "\n\n".join(failures),
              file=sys.stderr)
        return 0
    save_state(session, baseline, attempts)
    print("verify-implementation failed. Fix these problems, then finish:\n\n"
          + "\n\n".join(failures), file=sys.stderr)
    return 2


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        data = {}
    mode = sys.argv[1] if len(sys.argv) > 1 else "check"
    sys.exit({"snapshot": cmd_snapshot, "check": cmd_check}[mode](data))


if __name__ == "__main__":
    main()
