"""
Local repo initialization pipeline.

For each repo in the config:
    1. Ensure a local git repo exists at local_path (init if missing, skip otherwise).
    2. Ensure a remote 'origin' is set:
        - if already set, leave it untouched
        - if not set, check whether the repo exists on GitHub (create it if not,
          using the configured visibility), then add origin with the token
          embedded in the URL for authentication.
"""

import json
import logging
import time
import urllib.error
import urllib.request

from app.utils.git_helpers import get_remote_url, is_git_repo, run_git
from config import DEFAULT_TIMEOUT_SECONDS, RepoConfig

logger = logging.getLogger("gh_backup")

GITHUB_API_DELAY_SECONDS = 1


def init_local_repo(repo: RepoConfig) -> None:
    """Create repo.local_path if missing and run `git init` if it isn't a repo yet."""
    local_path = repo.local_path
    try:
        local_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise RuntimeError(f"[{repo.repo_name}] cannot create local directory: {e}")

    if is_git_repo(local_path):
        logger.info("[%s] repo already initialized, skipping", repo.repo_name)
        return

    code, out, err = run_git(["init"], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{repo.repo_name}] git init failed: {err}")
    logger.info("[%s] repo initialized", repo.repo_name)


def _raise_for_github_error(repo_name: str, e: urllib.error.HTTPError, action: str) -> None:
    """Turn a GitHub API HTTPError into a RuntimeError with a specific, actionable message."""
    body = e.read().decode(errors="replace")
    if e.code == 401:
        raise RuntimeError(
            f"[{repo_name}] GitHub rejected the token while trying to {action} "
            f"(401 Unauthorized). The token may be missing, invalid, or expired."
        )
    if e.code == 403:
        raise RuntimeError(
            f"[{repo_name}] GitHub denied the request to {action} (403 Forbidden). "
            f"This usually means the token lacks the required permissions "
            f"(needs 'Contents' and 'Administration' repository permissions), "
            f"or a rate limit was hit. Response: {body}"
        )
    if e.code == 422:
        raise RuntimeError(
            f"[{repo_name}] GitHub rejected the request to {action} (422 Unprocessable). "
            f"This can happen if a repo with this name already exists under a "
            f"different owner, or the name/visibility is invalid. Response: {body}"
        )
    raise RuntimeError(f"[{repo_name}] failed to {action} ({e.code}): {body}")


def github_repo_exists(github_profile: str, repo_name: str, token: str) -> bool:
    """Check via the GitHub API whether repo_name exists under github_profile."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{github_profile}/{repo_name}",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        _raise_for_github_error(repo_name, e, "check repo existence")
    except urllib.error.URLError as e:
        raise RuntimeError(f"[{repo_name}] could not reach GitHub API: {e.reason}")


def create_github_repo(repo_name: str, visibility: str, token: str) -> None:
    """Create a new GitHub repo named repo_name with the given visibility."""
    data = json.dumps({"name": repo_name, "private": visibility == "private"}).encode()
    req = urllib.request.Request(
        "https://api.github.com/user/repos",
        data=data,
        method="POST",
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
    )
    try:
        urllib.request.urlopen(req, timeout=DEFAULT_TIMEOUT_SECONDS)
        logger.info("[%s] created on GitHub (%s)", repo_name, visibility)
    except urllib.error.HTTPError as e:
        _raise_for_github_error(repo_name, e, "create repo")
    except urllib.error.URLError as e:
        raise RuntimeError(f"[{repo_name}] could not reach GitHub API: {e.reason}")


def build_remote_url(github_profile: str, repo_name: str, token: str) -> str:
    """Build an HTTPS remote URL with the token embedded for authentication."""
    return f"https://{token}@github.com/{github_profile}/{repo_name}.git"


def ensure_remote(local_path, github_profile: str, repo_name: str, visibility: str, token: str) -> None:
    """
    Make sure local_path has an 'origin' remote.

    If origin is already set, do nothing. Otherwise, create the repo on
    GitHub if it doesn't exist yet, then add origin pointing to it.
    """
    if get_remote_url(local_path) is not None:
        logger.info("[%s] remote origin already set, skipping", repo_name)
        return

    time.sleep(GITHUB_API_DELAY_SECONDS)
    if not github_repo_exists(github_profile, repo_name, token):
        create_github_repo(repo_name, visibility, token)
    else:
        logger.info("[%s] already exists on GitHub", repo_name)

    url = build_remote_url(github_profile, repo_name, token)
    code, out, err = run_git(["remote", "add", "origin", url], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{repo_name}] failed to add remote: {err}")
    logger.info("[%s] remote origin set", repo_name)


def init_repo(github_profile: str, repo: RepoConfig, token: str) -> None:
    """Run the local init + remote setup steps for a single repo."""
    init_local_repo(repo)
    ensure_remote(repo.local_path, github_profile, repo.repo_name, repo.visibility, token)


if __name__ == "__main__":
    from config import load_config, setup_logging

    setup_logging()
    config = load_config()
    for repo in config.repos:
        init_repo(config.github_profile, repo, config.github_token)