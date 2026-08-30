"""
Local commit pipeline.

For each repo in the config: stage all changes and commit them if there is
anything to commit; if the working tree is clean, skip.
"""

import logging
import time

from app.utils.git_helpers import run_git
from config import RepoConfig

logger = logging.getLogger("gh_backup")


def has_changes(local_path) -> bool:
    """Check whether the working tree has any staged/unstaged/untracked changes."""
    code, out, err = run_git(["status", "--porcelain"], cwd=local_path)
    return bool(out)


def commit_repo(repo: RepoConfig) -> None:
    """Stage and commit all changes in repo.local_path, if there are any."""
    local_path = repo.local_path

    if not has_changes(local_path):
        logger.info("[%s] no changes, skipping commit", repo.repo_name)
        return

    run_git(["add", "-A"], cwd=local_path)
    message = f"backup: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    code, out, err = run_git(["commit", "-m", message], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{repo.repo_name}] commit failed: {err}")
    logger.info("[%s] committed: %s", repo.repo_name, message)


if __name__ == "__main__":
    from config import load_config, setup_logging

    setup_logging()
    config = load_config()
    for repo in config.repos:
        commit_repo(repo)