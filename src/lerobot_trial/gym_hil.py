"""Utilities to interact with the Gym-HIL environment."""

from enum import Enum

import gymnasium as gym
import numpy as np
from gym_hil import GymRenderingSpec, PassiveViewerWrapper
from gym_hil.envs import PandaPickCubeGymEnv
from numpy.typing import NDArray

from .config import COMMON_CONFIG


class ActionDim(str, Enum):
    X = "x"
    Y = "y"
    Z = "z"
    GRIPPER = "gripper"

    def __str__(self) -> str:
        return self.value


def init_action() -> dict[ActionDim, float]:
    return {
        ActionDim.X: 0.0,
        ActionDim.Y: 0.0,
        ActionDim.Z: 0.0,
        ActionDim.GRIPPER: 0.0,
    }


def make_env(headless: bool) -> PandaPickCubeGymEnv:
    env = gym.make(
        id="gym_hil/PandaPickCubeBase-v0",
        # Unlimited steps; episode will be done on success or user interrupt.
        max_episode_steps=-1,
        seed=0,
        control_dt=COMMON_CONFIG.control_dt,
        physics_dt=0.002,
        render_spec=GymRenderingSpec(),
        # FIXME: Currently, setting a render mode emits a warning.
        # render_mode="human",
        image_obs=True,
        reward_type="sparse",
        random_block_position=True,
    )

    return env if headless else PassiveViewerWrapper(env)


def action_to_env_array(action: dict[ActionDim, float]) -> NDArray[np.floating]:
    env_action = [
        action[ActionDim.X],
        action[ActionDim.Y],
        action[ActionDim.Z],
        0.0,  # No orientation control
        0.0,
        0.0,
        action[ActionDim.GRIPPER],
    ]
    return np.array(env_action)
