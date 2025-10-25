"""Single-thread global control event dictionary.

This aims to replace LeRobot's control event dictionary created at:
https://github.com/huggingface/lerobot/blob/v0.4.0/src/lerobot/utils/control_utils.py#L134
"""

from enum import Enum


class ControlEventKey(str, Enum):
    EXIT_EARLY = "exit_early"
    RERECORD_EPISODE = "rerecord_episode"
    STOP_RECORDING = "stop_recording"

    def __str__(self) -> str:
        return self.value


lerobot_control_events: dict[ControlEventKey, bool] = {
    ControlEventKey.EXIT_EARLY: False,
    ControlEventKey.RERECORD_EPISODE: False,
    ControlEventKey.STOP_RECORDING: False,
}
