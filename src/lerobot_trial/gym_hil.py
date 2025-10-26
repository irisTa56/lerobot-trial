"""Utilities to interact with the Gym-HIL environment."""

from enum import Enum
from typing import Any, SupportsFloat

import gymnasium as gym
import numpy as np
from gym_hil import GymRenderingSpec, MujocoGymEnv, PassiveViewerWrapper
from numpy.typing import NDArray

from .config import COMMON_CONFIG


class ActionDim(str, Enum):
    X = "x"
    Y = "y"
    Z = "z"
    GRIPPER = "gripper"

    def __str__(self) -> str:
        return self.value


class AbsolutePositionControl(gym.Wrapper):  # type: ignore[type-arg]
    """Gym wrapper to accept absolute position commands."""

    def __init__(self, env: MujocoGymEnv) -> None:
        super().__init__(env)

    def reset(
        self, *, seed: int | None = None, options: dict[str, Any] | None = None
    ) -> tuple[Any, dict[str, Any]]:
        obs, info = self.env.reset(seed=seed, options=options)
        self._origin_xyz = self._get_xyz()
        return obs, info

    def step(
        self, action: NDArray[np.floating]
    ) -> tuple[Any, SupportsFloat, bool, bool, dict[str, Any]]:
        current_xyz = self._get_xyz() - self._origin_xyz
        action[:3] -= current_xyz
        # Map from [0, 1] to [-1, 1] where 0 becomes open command.
        # This mimics absolute position control as 1 must be held to stay closed.
        pseudo_grasp = 2 * action[6] - 1.0
        action[6] = pseudo_grasp
        return self.env.step(action)

    def _get_xyz(self) -> NDArray[np.floating]:
        env: MujocoGymEnv = self.unwrapped
        return env.data.mocap_pos[0].copy()  # type: ignore[no-any-return]


def init_action() -> dict[ActionDim, float]:
    return {
        ActionDim.X: 0.0,
        ActionDim.Y: 0.0,
        ActionDim.Z: 0.0,
        ActionDim.GRIPPER: 0.0,
    }


def make_env(headless: bool) -> MujocoGymEnv:
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

    env = env if headless else PassiveViewerWrapper(env)
    return AbsolutePositionControl(env)


def make_action_array(action: dict[ActionDim, float]) -> NDArray[np.floating]:
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
