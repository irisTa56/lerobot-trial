from typing import Any

from lerobot.teleoperators import Teleoperator, TeleoperatorConfig

from ..gym_client import GymClient
from .common import PolicyFeature


class BaseTeleop(Teleoperator):  # type: ignore[misc]
    def __init__(self, config: TeleoperatorConfig):
        super().__init__(config)
        self._client = GymClient()

    @property
    def action_features(self) -> dict[str, PolicyFeature]:
        raise NotImplementedError("Action features are not defined for BaseTeleop.")

    @property
    def feedback_features(self) -> dict[str, PolicyFeature]:
        return {}

    def get_action(self) -> dict[str, float]:
        return self._client.get_action()

    def send_feedback(self, _feedback: dict[str, Any]) -> None:
        pass

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
