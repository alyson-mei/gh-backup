import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
 
import yaml
from dotenv import load_dotenv
 
 
@dataclass
class RepoConfig:
    repo_name: str
    local_path: Path
    visibility: str
 
 
@dataclass
class Config:
    github_profile: str
    github_token: str
    repos: list[RepoConfig]
    interval_minutes: int
 
 
def _git_global(key: str) -> str | None:
    """Read a --global git config value; None if unset."""
    result = subprocess.run(["git", "config", "--global", key], capture_output=True, text=True)
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None
 
 
def _ensure_git_global(key: str, default: str) -> None:
    """Set a --global git config value if it isn't already set."""
    if _git_global(key) is None:
        subprocess.run(["git", "config", "--global", key, default], capture_output=True, text=True)
 
 
def ensure_git_configured(github_profile: str) -> None:
    """
    Make sure this machine has git basics set, so init/commit don't fail
    or fall back to git's own defaults (e.g. branch 'master').
 
    Anything already configured is left untouched.
    """
    _ensure_git_global("user.name", github_profile)
    _ensure_git_global("user.email", f"{github_profile}@users.noreply.github.com")
    _ensure_git_global("init.defaultBranch", "main")
 
 
def load_config(path: str = "config.yaml") -> Config:
    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError("GITHUB_TOKEN not found in .env")
 
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f)
 
    repos = [
        RepoConfig(
            repo_name=r["repo_name"],
            local_path=Path(r["local_path"]).expanduser().resolve(),
            visibility=r.get("visibility", "private"),
        )
        for r in raw["repos"]
    ]
 
    github_profile = raw["github_profile"]
    ensure_git_configured(github_profile)
 
    return Config(
        github_profile=github_profile,
        github_token=token,
        repos=repos,
        interval_minutes=raw.get("schedule", {}).get("interval_minutes", 60),
    )