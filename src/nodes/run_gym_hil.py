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
from lerobot_trial.gym_hil import action_to_env_array, init_action, make_env
from lerobot_trial.gym_utils import episode_frame_to_message


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
    state = State.BEFORE_DONE

    action = init_action()

    for event in node:
        match (event["type"], event.get("id")):
            case ("INPUT", ChannelId.ACTION):
                if state != State.BEFORE_DONE:
                    continue

                start = time.perf_counter()
                action = parse_single_value_in_event(event)
                env_action = action_to_env_array(action)
                obs, _reward, terminated, truncated, _info = env.step(env_action)
                output = episode_frame_to_message(action, obs)
                node.send_output(ChannelId.EPISODE, output)
                logging.debug(f"Step took {time.perf_counter() - start:.4f} secs.")

                if terminated or truncated:
                    logging.info(f"Done: {terminated=}, {truncated=}")
                    state = State.AFTER_DONE

            case ("INPUT", ChannelId.CONTROL):
                control = ControlCmd.from_event(event)

                if control == ControlCmd.ESC:
                    logging.info("Received ESC event. Closing environment...")
                    break
                elif state == State.RESETTING:
                    logging.info("Entering the next episode...")
                    _obs, _info = env.reset()
                    state = State.BEFORE_DONE
                else:
                    logging.info("Entering resetting phase...")
                    state = State.RESETTING

            case ("STOP", _):
                logging.info("Received stop signal from Dora.")
            case _:
                logging.warning(f"Unknown event: {event}")

    env.close()


if __name__ == "__main__":
    main()
