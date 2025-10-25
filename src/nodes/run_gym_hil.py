import logging
import time

from dora import Node
from lerobot.utils.utils import init_logging

from lerobot_trial.dora_ch import (
    ChannelId,
    parse_single_value_in_event,
)
from lerobot_trial.gym_hil import action_to_env_array, init_action, make_env


def main() -> None:
    init_logging()
    logging.info("Starting Gym-HIL node...")

    node = Node()

    env = make_env(headless=False)
    _obs, _info = env.reset()
    should_step = True

    action = init_action()

    for event in node:
        match (event["type"], event.get("id")):
            case ("INPUT", "tick"):
                if not should_step:
                    continue

                start = time.perf_counter()
                env_action = action_to_env_array(action)
                obs, _reward, terminated, truncated, _info = env.step(env_action)
                logging.debug(f"Step took {time.perf_counter() - start:.4f} seconds.")

                if terminated or truncated:
                    logging.info(f"Done: {terminated=}, {truncated=}")
                    should_step = False

            case ("INPUT", ChannelId.ACTION):
                action = parse_single_value_in_event(event)

            case ("STOP", _):
                logging.info("Received stop signal from Dora.")
            case _:
                logging.warning(f"Unknown event: {event}")

    env.close()


if __name__ == "__main__":
    main()
