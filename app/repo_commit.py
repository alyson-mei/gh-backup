"""
Local commit pipeline.

For each repo in the config: stage all changes and commit them if there is
anything to commit; if the working tree is clean, skip.
"""

import time

from app.git_helpers import run_git
from config import RepoConfig


def has_changes(local_path) -> bool:
    """Check whether the working tree has any staged/unstaged/untracked changes."""
    code, out, err = run_git(["status", "--porcelain"], cwd=local_path)
    return bool(out)


def commit_repo(repo: RepoConfig) -> None:
    """Stage and commit all changes in repo.local_path, if there are any."""
    local_path = repo.local_path

    if not has_changes(local_path):
        print(f"[{local_path}] no changes, skipping commit")
        return

    run_git(["add", "-A"], cwd=local_path)
    message = f"backup: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    code, out, err = run_git(["commit", "-m", message], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{local_path}] commit failed: {err}")
    print(f"[{local_path}] committed: {message}")


if __name__ == "__main__":
    from config import load_config
 
    config = load_config()
    for repo in config.repos:
        commit_repo(repo)
