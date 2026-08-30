"""
Config loading for the backup tool.

Handles:
    - reading GITHUB_TOKEN from .env
    - parsing config.yaml into typed Config/RepoConfig objects
    - checking that git is installed and available in PATH
    - making sure this machine has basic git settings (user.name, user.email,
      default branch), so init/commit don't fail or silently fall back to
      git's own defaults (e.g. branch 'master')
    - setting up logging for the whole app
"""

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path

import yaml
from dotenv import load_dotenv

logger = logging.getLogger("gh_backup")

DEFAULT_TIMEOUT_SECONDS = 10

LOG_FILE = "gh_backup.log"
LOG_MAX_BYTES = 1_000_000  # ~1 MB per file
LOG_BACKUP_COUNT = 3  # keep gh_backup.log + 3 rotated backups (~4 MB total)


@dataclass
class RepoConfig:
    """A single repo entry from config.yaml."""

    repo_name: str
    local_path: Path
    visibility: str


@dataclass
class Config:
    """Fully loaded, ready-to-use app configuration."""

    github_profile: str
    github_token: str
    repos: list[RepoConfig]
    interval_minutes: int


def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure the app-wide logger: prints to console and writes to a
    size-limited, rotating log file (LOG_FILE, capped at roughly
    LOG_MAX_BYTES * (LOG_BACKUP_COUNT + 1) total on disk).
    """
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)


def ensure_git_available() -> None:
    """Check that git is installed and available in PATH; raise a clear error if not."""
    if shutil.which("git") is None:
        raise RuntimeError(
            "git was not found in PATH. Install git and make sure it's available "
            "in your terminal before running this tool."
        )


def _git_global(key: str) -> str | None:
    """Read a --global git config value; None if unset."""
    result = subprocess.run(["git", "config", "--global", key], capture_output=True, text=True)
    value = result.stdout.strip()
    return value if result.returncode == 0 and value else None


def _ensure_git_global(key: str, default: str) -> None:
    """Set a --global git config value if it isn't already set."""
    if _git_global(key) is None:
        subprocess.run(["git", "config", "--global", key, default], capture_output=True, text=True)
        logger.info("git config --global %s was not set, defaulted to '%s'", key, default)


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
    """
    Load and validate the full app config.

    Reads GITHUB_TOKEN from .env, parses config.yaml, checks that git is
    installed, and makes sure this machine has basic git settings configured.
    """
    ensure_git_available()

    load_dotenv()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise ValueError(
            "GITHUB_TOKEN not found. Create a .env file next to config.yaml "
            "with a line like: GITHUB_TOKEN=ghp_xxxxxxxx"
        )

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