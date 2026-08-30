"""
Shared low-level git helpers, used by repo_init.py, repo_commit.py, repo_push.py, etc.
"""

import subprocess
from pathlib import Path

from config import DEFAULT_TIMEOUT_SECONDS


def run_git(args: list[str], cwd: Path, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> tuple[int, str, str]:
    """
    Run a git command in cwd, return (returncode, stdout, stderr).

    Raises RuntimeError if the command doesn't finish within `timeout` seconds
    (e.g. a hung network connection during pull/push).
    """
    try:
        result = subprocess.run(
            ["git", *args], cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"[{cwd}] git {' '.join(args)} timed out after {timeout}s")
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