"""Gym-ALOHA environment node for Dora dataflow.

## Dora Channels

### Inputs

- `tick`: Trigger signal to execute one environment step.

### Outputs

- `observation.state`: Robot joint positions (`agent_pos`) as flattened PyArrow array.
  Original shape: (14,) - [left_arm(6), right_arm(6), gripper_left(1), gripper_right(1)]

- `observation.images.top`: Top camera RGB image as flattened PyArrow array.
  Original shape: (H, W, 3) - Height x Width x RGB channels

Note: All arrays are sent as flattened PyArrow arrays with their original shape
stored in the metadata field.
"""

import logging
import os
import time
from collections.abc import Iterable
from dataclasses import asdict
from pprint import pformat
from typing import Any

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


def get_image_from_observation(obs: dict[str, Any]) -> NDArray:
    return obs["pixels"]["top"]


OBSERVATION_CHANNELS = {
    "observation.state": lambda obs: obs["agent_pos"],
    "observation.images.top": get_image_from_observation,
}

logger = logging.getLogger(__name__)


def make_env(cfg: AlohaEnv) -> gym.Env:
    """Create Gym-ALOHA environment from configuration."""
    return gym.make(
        cfg.gym_id,
        disable_env_checker=cfg.disable_env_checker,
        **cfg.gym_kwargs,
    )


def observation_to_dora_outputs(
    obs: dict[str, Any],
) -> Iterable[tuple[str, pa.Array, dict[str, Any]]]:
    """Convert Gym observations to publishable Dora outputs."""
    for ch, get in OBSERVATION_CHANNELS.items():
        v: NDArray = get(obs)
        yield (ch, pa.array(v.flatten()), {"shape": list(v.shape)})


@parser.wrap()
def main(cfg: AlohaEnv) -> None:
    logger.info(f"Start Gym-ALOHA node with:\n{pformat(asdict(cfg))}")

    node = Node()

    env = make_env(cfg)
    obs, _info = env.reset()
    action = obs["agent_pos"]
    done = False

    for event in node:
        match (event["type"], event.get("id")):
            case ("INPUT", "tick"):
                start = time.perf_counter()

                # action *= 1.01
                obs, _reward, terminated, truncated, _info = env.step(action)
                if (terminated or truncated) and not done:
                    logger.info(f"Episode done: {terminated=}, {truncated=}")
                    done = True

                for output_id, data, metadata in observation_to_dora_outputs(obs):
                    node.send_output(output_id, data, metadata)

                image = get_image_from_observation(obs)
                image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                update_frame(image_bgr)

                logger.debug(f"Step took {time.perf_counter() - start:.4f} secs.")

            # TODO: Add a clause to update `action` based on input

            case ("STOP", _):
                logger.info("Received stop signal from Dora.")
            case _:
                logger.warning(f"Unexpected event: {event}")


if __name__ == "__main__":
    init_logging(console_level=os.getenv("PYTHON_LOG", "INFO"))
    mjpeg_host = os.getenv("MJPEG_HOST", "localhost")
    mjpeg_port = int(os.getenv("MJPEG_PORT", "8080"))
    start_mjpeg_server(mjpeg_host, mjpeg_port)
    main()
