import logging
import time
from typing import Any

from dora import Node
from lerobot.utils.errors import DeviceNotConnectedError

from .dora_ch import (
    ChannelId,
    ControlCmd,
    is_timeout_event,
    make_dict_message,
    try_recv_event,
)
from .gym_utils import step_io_from_event
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
            cls._last_action: dict[str, float] | None = None  # action at t
            cls._last_observation: dict[str, Any] | None = None  # observation at t
            cls._updated_observation: dict[str, Any] | None = None  # observation at t+1
        return cls._instance

    def connect(self) -> None:
        while not self.is_connected():
            self._try_handle_event()
            time.sleep(0.1)  # Prevent busy waiting

    def get_action(self) -> dict[str, float]:
        """Get the latest action."""

        if not self.is_connected():
            raise DeviceNotConnectedError("GymClient is not connected.")

        # Use data received at the same time as the latest observation.
        return self._last_action  # type: ignore[return-value]

    def get_observation(self, synchronized: bool = False) -> dict[str, Any]:
        """Get the latest observation.

        If `synchronized` is True, returns the observation corresponding
        to the latest action (i.e., observation at time t). Otherwise, returns
        the most recently updated observation (i.e., observation at time t+1).
        """

        if not self.is_connected():
            raise DeviceNotConnectedError("GymClient is not connected.")

        self._try_handle_event()
        return self._last_observation if synchronized else self._updated_observation  # type: ignore[return-value]

    def send_action(self, action: dict[str, float]) -> None:
        message = make_dict_message(action)
        self._node.send_output(ChannelId.ACTION, message)

    def is_connected(self) -> bool:
        return (
            self._last_action is not None
            and self._last_observation is not None
            and self._updated_observation is not None
        )

    def _try_handle_event(self) -> None:
        while event := try_recv_event(self._node):
            if is_timeout_event(event):
                return

            match (event["type"], event.get("id")):
                case ("INPUT", ChannelId.CONTROL):
                    control = ControlCmd.from_event(event)
                    self._handle_control_event(control)
                case ("INPUT", ChannelId.EPISODE):
                    action, observation = step_io_from_event(event)
                    self._last_action = action
                    self._last_observation = self._updated_observation
                    self._updated_observation = observation
                case ("STOP", _):
                    logging.info("Received stop signal from Dora.")
                case _:
                    logging.warning(f"Unknown event: {event}")

        raise DoraEventStreamClosed()

    def _handle_control_event(self, control: ControlCmd) -> None:
        match control:
            case ControlCmd.ESC:
                logger.info("Stop data recording...")
                lerobot_control_events[ControlEventKey.EXIT_EARLY] = True
                lerobot_control_events[ControlEventKey.STOP_RECORDING] = True
            case ControlCmd.CTRL:
                logger.info("Re-record the last episode...")
                lerobot_control_events[ControlEventKey.EXIT_EARLY] = True
                lerobot_control_events[ControlEventKey.RERECORD_EPISODE] = True
            case ControlCmd.SPACE:
                logger.info("Finish episode (or resetting phase)...")
                lerobot_control_events[ControlEventKey.EXIT_EARLY] = True
