import logging
import threading
import time
from typing import Any, Literal

import pyarrow as pa
from dora import Node
from lerobot.utils.utils import init_logging
from pynput.keyboard import Key, Listener

from lerobot_trial.dora_ch import (
    ChannelId,
    is_timeout_event,
    make_dict_message,
    try_recv_event,
)
from lerobot_trial.gym_hil import ActionDim, init_action


class ActionState:
    def __init__(self) -> None:
        self._state = init_action()
        self._step_sizes = {
            ActionDim.X: 0.01,
            ActionDim.Y: 0.01,
            ActionDim.Z: 0.01,
            ActionDim.GRIPPER: 1.0,
        }

    def to_message(self) -> pa.Array:
        return make_dict_message(self._state)

    def update(self, key: Key, pressed: bool) -> bool:
        before = self._state.copy()

        if key == Key.up:
            self._update(ActionDim.Y, 1, pressed)
        elif key == Key.down:
            self._update(ActionDim.Y, -1, pressed)
        elif key == Key.left:
            self._update(ActionDim.X, -1, pressed)
        elif key == Key.right:
            self._update(ActionDim.X, 1, pressed)
        elif key == Key.shift:
            self._update(ActionDim.Z, -1, pressed)
        elif key == Key.shift_r:
            self._update(ActionDim.Z, 1, pressed)
        elif key == Key.cmd_r:
            self._update(ActionDim.GRIPPER, 1, pressed)
        elif key == Key.cmd_l:
            self._update(ActionDim.GRIPPER, -1, pressed)

        return self._state != before

    def _update(self, dim: ActionDim, sign: Literal[1, -1], pressed: bool) -> None:
        delta = sign * self._step_sizes[dim]
        self._state[dim] = delta if pressed else 0.0


def main() -> None:
    init_logging()
    logging.info("Starting Keyboard node...")

    node = Node()
    lock = threading.Lock()

    action = ActionState()

    def handle_key_event(key: Key, pressed: bool) -> None:
        if action.update(key, pressed):
            with lock:
                node.send_output(ChannelId.ACTION, action.to_message())

    def try_recv_dora_event() -> dict[str, Any] | None:
        with lock:
            return try_recv_event(node)

    with Listener(
        on_press=lambda key: handle_key_event(key, True),
        on_release=lambda key: handle_key_event(key, False),
    ):
        while event := try_recv_dora_event():
            if is_timeout_event(event):
                time.sleep(0.5)  # Prevent busy waiting
                continue

            match (event["type"], event.get("id")):
                case ("INPUT", "keep-alive"):
                    pass
                case ("STOP", _):
                    logging.info("Received stop signal from Dora.")
                case _:
                    logging.warning(f"Unknown event: {event}")


if __name__ == "__main__":
    main()
