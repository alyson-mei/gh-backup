import os
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
 
    return Config(
        github_profile=raw["github_profile"],
        github_token=token,
        repos=repos,
        interval_minutes=raw.get("schedule", {}).get("interval_minutes", 60),
    )
