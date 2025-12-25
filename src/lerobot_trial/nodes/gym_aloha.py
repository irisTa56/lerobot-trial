"""Gym-ALOHA environment node for Dora dataflow.

## Dora Channels

### Inputs

- `tick`: Trigger signal to execute one environment step.
- `action`: Action to be applied to the environment (flattened PyArrow array).

### Outputs

- `agent_pos`: Robot joint positions as flattened PyArrow array.
  Original shape: (14,) - [left_arm(6), right_arm(6), gripper_left(1), gripper_right(1)]

Note: Images are served via MJPEG HTTP stream instead of Dora channels.
"""

import logging
import os
import time
from dataclasses import asdict, replace
from pprint import pformat

import cv2
import gym_aloha  # noqa: F401
import gymnasium as gym
import pyarrow as pa
from dora import Node
from lerobot.configs import parser
from lerobot.envs.configs import AlohaEnv
from lerobot.utils.utils import init_logging
from numpy.typing import NDArray

from lerobot_trial.http.mjpeg_server import start_mjpeg_server, update_frame

logger = logging.getLogger(__name__)


def get_python_log_level() -> str:
    return os.getenv("PYTHON_LOG", "INFO")


def get_mjpeg_host() -> str:
    return os.getenv("MJPEG_HOST", "localhost")


def get_mjpeg_port() -> int:
    return int(os.getenv("MJPEG_PORT", "8080"))


def make_env(cfg: AlohaEnv) -> gym.Env:
    """Create Gym-ALOHA environment from configuration."""
    return gym.make(
        cfg.gym_id,
        disable_env_checker=cfg.disable_env_checker,
        **cfg.gym_kwargs,
    )


@parser.wrap()
def main(cfg: AlohaEnv) -> None:
    cfg = replace(cfg, max_parallel_tasks=-1)  # Disable internal episode termination
    logger.info(f"Start Gym-ALOHA node with:\n{pformat(asdict(cfg))}")

    node = Node()

    env = make_env(cfg)
    obs, _info = env.reset()
    action = obs["agent_pos"]

    for event in node:
        match (event["type"], event.get("id")):
            case ("INPUT", "tick"):
                start = time.perf_counter()

                obs, _reward, _terminated, _truncated, _info = env.step(action)

                agent_pos: NDArray = obs["agent_pos"]
                node.send_output(
                    "agent_pos",
                    pa.array(agent_pos),
                    {"shape": list(agent_pos.shape)},
                )

                image_bgr = cv2.cvtColor(obs["pixels"]["top"], cv2.COLOR_RGB2BGR)
                update_frame(image_bgr)

                logger.debug(f"Step took {time.perf_counter() - start:.4f} secs.")

            case ("INPUT", "action"):
                action: NDArray = event["value"].to_numpy()
                logger.debug(f"Received action: shape={action.shape}")

            case ("INPUT", "reset"):
                logger.debug("Received reset command.")
                obs, _ = env.reset()
                action = obs["agent_pos"]
                logger.debug("Environment reset complete.")

            case ("STOP", _):
                logger.info("Received stop signal from Dora.")
            case _:
                logger.warning(f"Unexpected event: {event}")


if __name__ == "__main__":
    init_logging(console_level=get_python_log_level())
    start_mjpeg_server(get_mjpeg_host(), get_mjpeg_port())
    main()
