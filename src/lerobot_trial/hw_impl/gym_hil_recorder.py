from dataclasses import dataclass

from lerobot.robots import RobotConfig
from lerobot.teleoperators import TeleoperatorConfig

from ..gym_hil import ActionDim, make_env
from .base_robot import ActionMode, BaseRobot
from .base_teleop import BaseTeleop
from .common import PolicyFeature


@RobotConfig.register_subclass("gym_hil_recorder")
@dataclass
class GymHILRecorderRobotConfig(RobotConfig):  # type: ignore[misc]
    pass


class GymHILRecorderRobot(BaseRobot):
    config_class = GymHILRecorderRobotConfig
    name = "gym_hil_recorder"

    def __init__(self, config: GymHILRecorderRobotConfig) -> None:
        env = make_env(headless=True)
        super().__init__(config, env=env, action_mode=ActionMode.TELEOP)
        env.close()

    @property
    def action_features(self) -> dict[str, PolicyFeature]:
        return {
            ActionDim.X: float,
            ActionDim.Y: float,
            ActionDim.Z: float,
            ActionDim.GRIPPER: float,
        }


@TeleoperatorConfig.register_subclass("gym_hil_recorder")
@dataclass
class GymHILRecorderTeleopConfig(TeleoperatorConfig):  # type: ignore[misc]
    pass


class GymHILRecorderTeleop(BaseTeleop):
    config_class = GymHILRecorderTeleopConfig
    name = "gym_hil_recorder"

    @property
    def action_features(self) -> dict[str, PolicyFeature]:
        return {
            ActionDim.X: float,
            ActionDim.Y: float,
            ActionDim.Z: float,
            ActionDim.GRIPPER: float,
        }
