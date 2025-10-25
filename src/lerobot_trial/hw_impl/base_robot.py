from typing import Any

import gymnasium as gym
import numpy as np
from lerobot.processor import (
    RobotAction,
    RobotObservation,
)
from lerobot.robots import Robot, RobotConfig

from ..gym_client import GymClient
from .common import PolicyFeature


class BaseRobot(Robot):  # type: ignore[misc]
    def __init__(self, config: RobotConfig, env: gym.Env) -> None:  # type: ignore[type-arg]
        super().__init__(config)
        self._client = GymClient()

        if not isinstance(env.observation_space, gym.spaces.Dict):
            raise ValueError("Observation space is not a dictionary")

        self._observation_features = _make_observation_features(env.observation_space)

        self.cameras = {
            k: None  # Camera only exists virtually.
            for k, v in self._observation_features.items()
            if _is_visual_feature(v)
        }

    @property
    def observation_features(self) -> dict[str, PolicyFeature]:
        return self._observation_features

    @property
    def action_features(self) -> dict[str, PolicyFeature]:
        raise NotImplementedError("Action features are not defined for BaseRobot.")

    def get_observation(self) -> RobotObservation:
        env_observation = self._client.get_observation()
        return _make_observations(env_observation)

    def send_action(self, action: RobotAction) -> RobotAction:
        return action

    @property
    def is_connected(self) -> bool:
        return self._client.is_connected()

    def connect(self) -> None:
        self._client.connect()  # Idempotent

    def disconnect(self) -> None:
        pass

    @property
    def is_calibrated(self) -> bool:
        return self.is_connected

    def calibrate(self) -> None:
        pass

    def configure(self) -> None:
        pass


def _make_observations(original: dict[str, Any]) -> RobotObservation:
    observations = {}
    for key, val in original.items():
        if isinstance(val, dict):
            # Will flatten nested pixel (image) observations
            observations.update(_make_observations(val))
        elif isinstance(val, np.ndarray) and val.ndim == 1:
            # Will flatten a state vector as indexed scalars
            observations.update({f"{key}.{i:02d}": v for i, v in enumerate(val)})
        elif isinstance(val, np.ndarray) and val.ndim == 3:
            observations[key] = val  # Keep an image as is
        else:
            raise ValueError(f"Unsupported observation at '{key}': {val}")

    return observations


def _make_observation_features(
    root_space: gym.spaces.Dict,
) -> dict[str, PolicyFeature]:
    features = {}
    for key, space in root_space.spaces.items():
        if isinstance(space, gym.spaces.Dict):
            features.update(_make_observation_features(space))
        elif isinstance(space, gym.spaces.Box) and len(space.shape) == 1:
            features.update({f"{key}.{i:02d}": float for i in range(space.shape[0])})
        elif isinstance(space, gym.spaces.Box) and len(space.shape) == 3:
            features[key] = space.shape
        else:
            raise ValueError(f"Unsupported observation space at '{key}': {space}")

    return features


def _is_visual_feature(ft: PolicyFeature) -> bool:
    return isinstance(ft, tuple) and len(ft) == 3
