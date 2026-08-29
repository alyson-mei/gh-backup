"""
Technical script for testing: reset repos to a clean state.

For each repo in the config:
    1. Delete the remote repo on GitHub, if it exists.
    2. Delete the local .git directory (local files are left untouched).
"""

import shutil
import urllib.error
import urllib.request

from config import Config, RepoConfig, load_config


def delete_github_repo(github_profile: str, repo_name: str, token: str) -> None:
    """Delete repo_name on GitHub under github_profile, if it exists."""
    req = urllib.request.Request(
        f"https://api.github.com/repos/{github_profile}/{repo_name}",
        method="DELETE",
        headers={"Authorization": f"token {token}", "Accept": "application/vnd.github+json"},
    )
    try:
        urllib.request.urlopen(req)
        print(f"[{repo_name}] deleted on GitHub")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            print(f"[{repo_name}] not found on GitHub, skipping")
        else:
            raise RuntimeError(f"[{repo_name}] failed to delete on GitHub: {e.read().decode()}")


def delete_local_git(local_path) -> None:
    """Remove the .git directory at local_path, if it exists."""
    git_dir = local_path / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)
        print(f"[{local_path}] .git removed")
    else:
        print(f"[{local_path}] no .git found, skipping")


def clear_repo(github_profile: str, repo: RepoConfig, token: str) -> None:
    """Delete the remote GitHub repo, then the local .git directory, for one repo."""
    delete_github_repo(github_profile, repo.repo_name, token)
    delete_local_git(repo.local_path)


def clear_all(config: Config) -> None:
    """Run clear_repo for every repo listed in the config."""
    for repo in config.repos:
        clear_repo(config.github_profile, repo, config.github_token)


if __name__ == "__main__":
    config = load_config()
    clear_all(config)