import logging
import time
from enum import Enum

from dora import Node
from lerobot.utils.utils import init_logging

from lerobot_trial.dora_ch import (
    ChannelId,
    ControlCmd,
    parse_single_value_in_event,
)
from lerobot_trial.gym_hil import init_action, make_action_array, make_env
from lerobot_trial.gym_utils import step_io_to_message


class State(int, Enum):
    BEFORE_DONE = 0
    AFTER_DONE = 1
    RESETTING = 2


def main() -> None:
    init_logging()
    logging.info("Starting Gym-HIL node...")

    node = Node()

    env = make_env(headless=False)

    _obs, _info = env.reset()
    action = init_action()
    countdown_to_reset = None

    state = State.BEFORE_DONE
    action_recv_count = 0

    for event in node:
        match (event["type"], event.get("id")):
            case ("INPUT", "tick"):
                start = time.perf_counter()

                env_action = make_action_array(action)
                obs, _reward, terminated, truncated, _info = env.step(env_action)
                output = step_io_to_message(action, obs)
                node.send_output(ChannelId.EPISODE, output)

                logging.debug(f"Step took {time.perf_counter() - start:.4f} secs.")

                if state == State.BEFORE_DONE and (terminated or truncated):
                    logging.info(f"Done: {terminated=}, {truncated=}")
                    state = State.AFTER_DONE

                if countdown_to_reset is not None:
                    countdown_to_reset -= 1

            case ("INPUT", ChannelId.ACTION):
                if state != State.BEFORE_DONE:
                    continue

                # Discard the first action after reset to ignore lingering user inputs.
                if action_recv_count > 0:
                    action = parse_single_value_in_event(event)

                action_recv_count += 1

            case ("INPUT", ChannelId.CONTROL):
                if ControlCmd.from_event(event) == ControlCmd.ESC:
                    logging.info("Closing environment...")
                    break

                if state == State.RESETTING:
                    logging.info("Entering the next episode...")
                    state = State.BEFORE_DONE
                    action_recv_count = 0
                else:
                    logging.info("Entering resetting phase...")
                    state = State.RESETTING
                    # Delay the reset to prevent post-reset frames from being recorded.
                    countdown_to_reset = 10

            case ("STOP", _):
                logging.info("Received stop signal from Dora.")
            case _:
                logging.warning(f"Unknown event: {event}")

        if countdown_to_reset == 0:
            logging.info("Resetting environment...")
            _obs, _info = env.reset()
            action = init_action()
            countdown_to_reset = None

    env.close()


if __name__ == "__main__":
    main()
