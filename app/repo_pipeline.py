"""
Repo pipeline: init -> commit -> pull -> push.
"""
 
from app.repo_commit import commit_repo
from app.repo_init import init_repo
from app.repo_push import sync_repo
from config import Config, RepoConfig
 
 
def run_repo_pipeline(github_profile: str, repo: RepoConfig, token: str) -> None:
    """Run the full backup pipeline for a single repo."""
    init_repo(github_profile, repo, token)
    commit_repo(repo)
    sync_repo(repo)
 
 
def run_all_pipelines(config: Config) -> None:
    """Run run_repo_pipeline for every repo listed in the config."""
    for repo in config.repos:
        run_repo_pipeline(config.github_profile, repo, config.github_token)


if __name__ == "__main__":
    from config import load_config
 
    config = load_config()
    run_all_pipelines(config)