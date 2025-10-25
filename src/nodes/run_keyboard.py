import logging
import threading
from typing import Any

import pyarrow as pa
from dora import Node
from lerobot.utils.utils import init_logging
from pynput.keyboard import Key, Listener

from lerobot_trial.dora_ch import (
    ChannelId,
    ControlCmd,
    is_timeout_event,
    make_dict_message,
    try_recv_event,
)
from lerobot_trial.gym_hil import ActionDim, init_action

CONTROL_KEY_MAP = {
    Key.esc: ControlCmd.ESC,
    Key.ctrl: ControlCmd.CTRL,
    Key.space: ControlCmd.SPACE,
}


class ActionState:
    def __init__(self) -> None:
        self._state = init_action()
        self._step_sizes = {
            ActionDim.X: 0.005,
            ActionDim.Y: 0.005,
            ActionDim.Z: 0.005,
        }
        self._pressed_positive = {
            ActionDim.X: False,
            ActionDim.Y: False,
            ActionDim.Z: False,
        }
        self._pressed_negative = {
            ActionDim.X: False,
            ActionDim.Y: False,
            ActionDim.Z: False,
        }

    def reset(self) -> None:
        self._state = init_action()

    def handle_key_event(self, key: Key, pressed: bool) -> None:
        if key == Key.up:
            self._pressed_positive[ActionDim.Y] = pressed
        elif key == Key.down:
            self._pressed_negative[ActionDim.Y] = pressed
        elif key == Key.left:
            self._pressed_negative[ActionDim.X] = pressed
        elif key == Key.right:
            self._pressed_positive[ActionDim.X] = pressed
        elif key == Key.shift:
            self._pressed_negative[ActionDim.Z] = pressed
        elif key == Key.shift_r:
            self._pressed_positive[ActionDim.Z] = pressed
        elif key == Key.cmd_r:
            self._state[ActionDim.GRIPPER] = 1.0 if pressed else 0.0
        elif key == Key.cmd_l:
            self._state[ActionDim.GRIPPER] = -1.0 if pressed else 0.0

    def tick_to_message(self) -> pa.Array:
        # Increment x, y, z for absolute position control.
        for dim in [ActionDim.X, ActionDim.Y, ActionDim.Z]:
            sign = int(self._pressed_positive[dim]) - int(self._pressed_negative[dim])
            self._state[dim] += sign * self._step_sizes[dim]

        return make_dict_message(self._state)


def main() -> None:
    init_logging()
    logging.info("Starting Keyboard node...")

    node = Node()
    lock = threading.Lock()

    action = ActionState()

    def handle_key_event(key: Key, pressed: bool) -> None:
        if not pressed and key in CONTROL_KEY_MAP:
            command = CONTROL_KEY_MAP[key]
            with lock:
                node.send_output(ChannelId.CONTROL, command.to_message())
                action.reset()
        else:
            with lock:
                action.handle_key_event(key, pressed)

    def try_recv_dora_event() -> dict[str, Any] | None:
        with lock:
            return try_recv_event(node)

    with Listener(
        on_press=lambda key: handle_key_event(key, True),
        on_release=lambda key: handle_key_event(key, False),
    ):
        while event := try_recv_dora_event():
            if is_timeout_event(event):
                continue

            match (event["type"], event.get("id")):
                case ("INPUT", "tick"):
                    with lock:
                        output = action.tick_to_message()
                        node.send_output(ChannelId.ACTION, output)
                case ("STOP", _):
                    logging.info("Received stop signal from Dora.")
                case _:
                    logging.warning(f"Unknown event: {event}")


if __name__ == "__main__":
    main()
