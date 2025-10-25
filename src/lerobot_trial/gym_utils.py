from typing import Any

import numpy as np
import pyarrow as pa

from .dora_ch import DoraEvent, make_dict_message, parse_single_value_in_event


def episode_frame_to_message[T: str](
    action: dict[T, float],
    observation: dict[str, Any],
) -> pa.Array:
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


def episode_frame_from_event(
    event: DoraEvent,
) -> tuple[dict[str, float], dict[str, Any]]:
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
