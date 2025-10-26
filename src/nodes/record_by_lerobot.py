import logging
import os

import lerobot.scripts.lerobot_record as lsr
from lerobot.configs import parser
from lerobot.datasets.lerobot_dataset import LeRobotDataset
from lerobot.scripts.lerobot_record import RecordConfig, record
from lerobot.utils.utils import init_logging

import lerobot_trial.hw_impl  # noqa: F401
from lerobot_trial import COMMON_CONFIG, DoraEventStreamClosed, lerobot_control_events


@parser.wrap()  # type: ignore[misc]
def main(cfg: RecordConfig) -> None:
    init_logging()
    logging.info("Starting LeRobot node...")

    if os.environ.get("RESUME_RECORDING"):
        logging.info("Resuming previous recording...")
        dataset = LeRobotDataset(repo_id=cfg.dataset.repo_id, root=cfg.dataset.root)
        remaining_episodes = cfg.dataset.num_episodes - dataset.num_episodes
        cfg.dataset.num_episodes = max(0, remaining_episodes)
        cfg.resume = True

    # Adjust config values based on common settings.
    if cfg.dataset.fps != COMMON_CONFIG.fps:
        logging.info(f"Adjust {cfg.dataset.fps=} -> {COMMON_CONFIG.fps=}")
        cfg.dataset.fps = COMMON_CONFIG.fps

    # Give user control to start/stop episodes rather than fixed time.
    cfg.dataset.episode_time_s = float("inf")
    cfg.dataset.reset_time_s = float("inf")

    # Disable LeRobot's keyboard listener not to conflict with ours.
    lsr.init_keyboard_listener = lambda: (None, lerobot_control_events)

    try:
        record(cfg)
    except DoraEventStreamClosed:
        logging.info("Dora event stream closed. Exiting...")


if __name__ == "__main__":
    main()
