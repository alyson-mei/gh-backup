"""
Repo pipeline: init -> commit -> pull -> push.
"""

import logging
import time

from app.core.repo_commit import commit_repo
from app.core.repo_init import init_repo
from app.core.repo_push import sync_repo
from config import Config, RepoConfig, GITHUB_API_DELAY_SECONDS

logger = logging.getLogger("gh_backup")


def run_repo_pipeline(github_profile: str, repo: RepoConfig, token: str) -> None:
    """Run the full backup pipeline for a single repo."""
    init_repo(github_profile, repo, token)
    commit_repo(repo)
    sync_repo(repo)


def run_all_pipelines(config: Config) -> None:
    """
    Run run_repo_pipeline for every repo listed in the config.

    A failure in one repo (network hiccup, conflict, permission issue on
    that specific repo, etc.) is logged and skipped so it doesn't stop the
    rest of the repos from being processed.
    """
    for repo in config.repos:
        try:
            run_repo_pipeline(config.github_profile, repo, config.github_token)
        except Exception:
            logger.exception("[%s] pipeline failed, skipping this repo", repo.repo_name)
        time.sleep(GITHUB_API_DELAY_SECONDS)  # avoid hitting GitHub API rate limits


if __name__ == "__main__":
    from config import load_config, setup_logging

    setup_logging()
    config = load_config()
    run_all_pipelines(config)