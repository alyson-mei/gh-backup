"""
Shared low-level git helpers, used by repo_init.py, repo_commit.py, repo_push.py, etc.
"""

import subprocess
from pathlib import Path


def run_git(args: list[str], cwd: Path) -> tuple[int, str, str]:
    """Run a git command in cwd, return (returncode, stdout, stderr)."""
    result = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)
    return result.returncode, result.stdout.strip(), result.stderr.strip()


def is_git_repo(local_path: Path) -> bool:
    """Check whether local_path already contains a .git directory."""
    return (local_path / ".git").exists()


def get_remote_url(local_path: Path) -> str | None:
    """Return the current 'origin' URL, or None if no origin is configured."""
    code, out, err = run_git(["remote", "get-url", "origin"], cwd=local_path)
    return out if code == 0 else None


def get_current_branch(local_path: Path) -> str:
    """Return the current checked-out branch name."""
    code, out, err = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{local_path}] failed to read current branch: {err}")
    return out