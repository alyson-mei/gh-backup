"""
Entry point: run the backup pipeline for every repo in config.yaml,
repeating every interval_minutes as set in the config's schedule.
"""
 
import time
 
from app.repo_pipeline import run_all_pipelines
from config import load_config
 
 
def run_loop() -> None:
    """Reload the config and run all pipelines, then sleep, forever."""
    while True:
        config = load_config()
        run_all_pipelines(config)
        print(f"sleeping for {config.interval_minutes} minutes...")
        time.sleep(config.interval_minutes * 60)
 
 
if __name__ == "__main__":
    run_loop()
 