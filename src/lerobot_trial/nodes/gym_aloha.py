"""Gym-ALOHA environment node for Dora dataflow.

## Dora Channels

### Inputs

- `tick`: Trigger signal to execute one environment step.

### Outputs

- `observation.state`: Robot joint positions and velocities as flattened PyArrow array.
  Original shape: (14,) - [left_arm(6), right_arm(6), gripper_left(1), gripper_right(1)]
  Metadata: {"shape": "(14,)", "dtype": "float64"}

- `observation.images.top`: Top camera RGB image as flattened PyArrow array.
  Original shape: (H, W, 3) - Height x Width x RGB channels
  Metadata: {"shape": "(H, W, 3)", "dtype": "uint8"}

Note: All arrays are flattened for transmission. Original shape and dtype are
preserved in the message metadata for reconstruction on the receiving end.
"""

import logging
import os
import time
from dataclasses import asdict
from pprint import pformat

import gym_aloha  # noqa: F401
import gymnasium as gym
import pyarrow as pa
from dora import Node
from lerobot.configs import parser
from lerobot.envs.configs import AlohaEnv
from lerobot.utils.utils import init_logging

OBSERVATION_CHANNELS_MAP = {
    "agent_pos": "observation.state",
    "pixels/top": "observation.images.top",
}

logger = logging.getLogger(__name__)


@parser.wrap()
def main(cfg: AlohaEnv) -> None:
    logger.info(f"Start Gym-ALOHA node with:\n{pformat(asdict(cfg))}")

    node = Node()

    env = gym.make(
        cfg.gym_id,
        disable_env_checker=cfg.disable_env_checker,
        **(cfg.gym_kwargs or {}),
    )

    obs, _info = env.reset()
    action = obs["agent_pos"]

    for event in node:
        match (event["type"], event.get("id")):
            case ("INPUT", "tick"):
                start = time.perf_counter()

                obs, _reward, terminated, truncated, _info = env.step(action)
                if terminated or truncated:
                    logger.info(f"Episode done: {terminated=}, {truncated=}")

                for k, v in obs.items():
                    if output_id := OBSERVATION_CHANNELS_MAP.get(k):
                        metadata = {"shape": str(v.shape), "dtype": str(v.dtype)}
                        node.send_output(output_id, pa.array(v.flatten()), metadata)

                logger.debug(f"Step took {time.perf_counter() - start:.4f} secs.")

            # TODO: Add a clause to update `action` based on input

            case ("STOP", _):
                logger.info("Received stop signal from Dora.")
            case _:
                logger.warning(f"Unknown event: {event}")


if __name__ == "__main__":
    init_logging(console_level=os.getenv("PYTHON_LOG", "INFO"))
    main()
