from dataclasses import dataclass

from lerobot.robots import RobotConfig

from ..gym_hil import ActionDim, make_env
from .base_robot import ActionMode, BaseRobot
from .common import PolicyFeature


@RobotConfig.register_subclass("gym_hil_evaluator")
@dataclass
class GymHILEvaluatorRobotConfig(RobotConfig):  # type: ignore[misc]
    pass


class GymHILEvaluatorRobot(BaseRobot):
    config_class = GymHILEvaluatorRobotConfig
    name = "gym_hil_evaluator"

    def __init__(self, config: GymHILEvaluatorRobotConfig) -> None:
        env = make_env(headless=True)
        super().__init__(config, env=env, action_mode=ActionMode.POLICY)
        env.close()

    @property
    def action_features(self) -> dict[str, PolicyFeature]:
        return {
            ActionDim.X: float,
            ActionDim.Y: float,
            ActionDim.Z: float,
            ActionDim.GRIPPER: float,
        }
