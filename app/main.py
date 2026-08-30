"""
Entry point: run the backup pipeline for every repo in config.yaml,
repeating every interval_minutes as set in the config's schedule.
"""

import logging
import signal
import time

from app.core.repo_pipeline import run_all_pipelines
from config import load_config, setup_logging

logger = logging.getLogger("gh_backup")

_stop_requested = False


def _request_stop(signum, frame) -> None:
    """Signal handler: flag a stop instead of exiting immediately."""
    global _stop_requested
    logger.info("stop requested, will exit after the current run finishes")
    _stop_requested = True


def run_loop() -> None:
    """
    Reload the config and run all pipelines, then sleep, repeating forever.

    On Ctrl+C (SIGINT) or SIGTERM, finishes the current pipeline run (so no
    repo is left mid-commit/mid-push) and exits cleanly instead of sleeping.
    """
    setup_logging()
    signal.signal(signal.SIGINT, _request_stop)
    signal.signal(signal.SIGTERM, _request_stop)

    while not _stop_requested:
        config = load_config()
        run_all_pipelines(config)

        if _stop_requested:
            break

        logger.info("sleeping for %s minutes...", config.interval_minutes)
        # sleep in short slices so a stop request is picked up quickly
        # instead of waiting out the full interval
        remaining = config.interval_minutes * 60
        while remaining > 0 and not _stop_requested:
            step = min(1, remaining)
            time.sleep(step)
            remaining -= step

    logger.info("stopped")


if __name__ == "__main__":
    run_loop()