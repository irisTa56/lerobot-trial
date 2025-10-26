from typing import Any

import numpy as np
import pyarrow as pa

from .dora_ch import DoraEvent, make_dict_message, parse_single_value_in_event


def step_io_to_message[T: str](
    action: dict[T, float],
    observation: dict[str, Any],
) -> pa.Array:
    """Converts a step input/output pair (action/observation) to a Dora message.

    Action at time t and observation at time t+1 should be provided together,
    i.e., the observation should be the result of applying the action.
    """
    flattened = {
        key: {
            k: {"array": v.flatten(), "shape": v.shape}
            for k, v in observation[key].items()
        }
        if key == "pixels"
        else val
        for key, val in observation.items()
    }

    message = {"action": action, "observation": flattened}
    return make_dict_message(message)


def step_io_from_event(
    event: DoraEvent,
) -> tuple[dict[str, float], dict[str, Any]]:
    """Extracts a step input/output pair (action/observation) from a Dora event.

    Action at time t and observation at time t+1 are returned together,
    i.e., the observation is the result of applying the action.
    """
    record = parse_single_value_in_event(event)
    observation = {
        key: {
            k: np.array(v["array"], dtype=np.uint8).reshape(v["shape"])
            for k, v in val.items()
        }
        if key == "pixels"
        else np.array(val)
        for key, val in record["observation"].items()
    }

    return record["action"], observation
