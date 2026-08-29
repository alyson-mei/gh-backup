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
import time
import urllib.error
import urllib.request

from app.git_helpers import get_remote_url, is_git_repo, run_git
from config import RepoConfig

GITHUB_API_DELAY_SECONDS = 1


def init_local_repo(local_path) -> None:
    """Create local_path if missing and run `git init` if it isn't a repo yet."""
    local_path.mkdir(parents=True, exist_ok=True)
    if is_git_repo(local_path):
        print(f"[{local_path}] repo already initialized, skipping")
        return

    code, out, err = run_git(["init"], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{local_path}] git init failed: {err}")
    print(f"[{local_path}] repo initialized")


def github_repo_exists(github_profile: str, repo_name: str, token: str) -> bool:
    """Check via the GitHub API whether repo_name exists under github_profile."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{github_profile}/{repo_name}",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        urllib.request.urlopen(req, timeout=10)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise
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
        urllib.request.urlopen(req, timeout=10)
        print(f"[{repo_name}] created on GitHub ({visibility})")
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"[{repo_name}] failed to create on GitHub: {e.read().decode()}")
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
        print(f"[{local_path}] remote origin already set, skipping")
        return

    time.sleep(GITHUB_API_DELAY_SECONDS)
    if not github_repo_exists(github_profile, repo_name, token):
        create_github_repo(repo_name, visibility, token)
    else:
        print(f"[{repo_name}] already exists on GitHub")

    url = build_remote_url(github_profile, repo_name, token)
    code, out, err = run_git(["remote", "add", "origin", url], cwd=local_path)
    if code != 0:
        raise RuntimeError(f"[{local_path}] failed to add remote: {err}")
    print(f"[{local_path}] remote origin set")


def init_repo(github_profile: str, repo: RepoConfig, token: str) -> None:
    """Run the local init + remote setup steps for a single repo."""
    init_local_repo(repo.local_path)
    ensure_remote(repo.local_path, github_profile, repo.repo_name, repo.visibility, token)


if __name__ == "__main__":
    from config import load_config

    config = load_config()
    for repo in config.repos:
        init_repo(config.github_profile, repo, config.github_token)