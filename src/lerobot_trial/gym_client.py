import logging
import time
from typing import Any

from dora import Node
from lerobot.utils.errors import DeviceNotConnectedError

from .dora_ch import (
    ChannelId,
    ControlCmd,
    is_timeout_event,
    try_recv_event,
)
from .gym_utils import episode_frame_from_event
from .lerobot_control_events import ControlEventKey, lerobot_control_events

logger = logging.getLogger(__name__)


class DoraEventStreamClosed(Exception):
    pass


class GymClient:
    """Single-thread client to interact with a Gym environment via Dora."""

    _instance = None

    def __new__(cls) -> "GymClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._node = Node()
        return cls._instance

    def connect(self) -> None:
        while not self.is_connected():
            self._try_recv()
            time.sleep(0.1)  # Prevent busy waiting

    def get_action(self) -> dict[str, float]:
        if not self.is_connected():
            raise DeviceNotConnectedError("GymClient is not connected.")
        # Use data received at the same time as the latest observation.
        return self._latest_action

    def get_observation(self) -> dict[str, Any]:
        if not self.is_connected():
            raise DeviceNotConnectedError("GymClient is not connected.")

        self._try_recv()
        return self._latest_observation

    def is_connected(self) -> bool:
        return hasattr(self, "_latest_action") and hasattr(self, "_latest_observation")

    def _try_recv(self) -> None:
        while event := try_recv_event(self._node):
            if is_timeout_event(event):
                return

            match (event["type"], event.get("id")):
                case ("INPUT", ChannelId.CONTROL):
                    control = ControlCmd.from_event(event)
                    self._handle_control_event(control)
                case ("INPUT", ChannelId.EPISODE):
                    action, observation = episode_frame_from_event(event)
                    self._latest_action = action
                    self._latest_observation = observation
                case ("STOP", _):
                    logging.info("Received stop signal from Dora.")
                case _:
                    logging.warning(f"Unknown event: {event}")

        raise DoraEventStreamClosed()

    def _handle_control_event(self, control: ControlCmd) -> None:
        match control:
            case ControlCmd.ESC:
                logger.info("Received ESC event. Stop data recording...")
                lerobot_control_events[ControlEventKey.EXIT_EARLY] = True
                lerobot_control_events[ControlEventKey.STOP_RECORDING] = True
            case ControlCmd.CTRL:
                logger.info("Received CTRL event. Rerecord the last episode...")
                lerobot_control_events[ControlEventKey.EXIT_EARLY] = True
                lerobot_control_events[ControlEventKey.RERECORD_EPISODE] = True
            case ControlCmd.SPACE:
                logger.info("Received SPACE event. Finish environment reset...")
                lerobot_control_events[ControlEventKey.EXIT_EARLY] = True
