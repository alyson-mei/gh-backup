"""
Pull/push pipeline.

For each repo: pull from origin on the current branch (conflicts are left
for the user to resolve manually, not handled automatically), then push.
"""

import logging

from app.utils.git_helpers import get_current_branch, run_git
from config import RepoConfig

logger = logging.getLogger("gh_backup")


def pull_repo(repo: RepoConfig) -> bool:
    """
    Pull origin into the current branch.

    Returns True if it's safe to proceed (up to date, fast-forwarded, or
    remote branch didn't exist yet). Returns False on a real conflict,
    which is left for the user to resolve manually.
    """
    local_path = repo.local_path
    branch = get_current_branch(local_path)

    code, out, err = run_git(["pull", "--no-rebase", "origin", branch], cwd=local_path)
    if code == 0:
        logger.info("[%s] pull: %s", repo.repo_name, out or "up to date")
        return True

    low = (out + err).lower()
    if "conflict" in low:
        logger.error("[%s] CONFLICT during pull, resolve manually:\n%s", repo.repo_name, err or out)
        return False
    if "couldn't find remote ref" in low or "unrelated histories" in low:
        # remote branch doesn't exist yet (freshly created repo) - nothing to pull
        logger.info("[%s] pull skipped (remote branch not found yet)", repo.repo_name)
        return True

    logger.error("[%s] pull failed: %s", repo.repo_name, err or out)
    return False


def push_repo(repo: RepoConfig) -> None:
    """Push the current branch to origin."""
    local_path = repo.local_path
    branch = get_current_branch(local_path)

    code, out, err = run_git(["push", "-u", "origin", branch], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{repo.repo_name}] push failed: {err}")
    logger.info("[%s] pushed: %s", repo.repo_name, out or err or "ok")


def sync_repo(repo: RepoConfig) -> None:
    """Pull then push a single repo. Skips push if pull hit a conflict."""
    if not pull_repo(repo):
        return
    push_repo(repo)


if __name__ == "__main__":
    from config import load_config, setup_logging

    setup_logging()
    config = load_config()
    for repo in config.repos:
        sync_repo(repo)