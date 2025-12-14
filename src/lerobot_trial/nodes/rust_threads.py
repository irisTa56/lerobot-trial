"""Dora node using Rust-based threading implementation.

This node demonstrates how to use the Rust-implemented DoraNode wrapper
that handles Dora event processing in separate threads.

## Dora Channels

### Inputs

- Any input channel defined in the dataflow configuration.

### Outputs

- Any output channel defined in the dataflow configuration.
"""

import logging
import os
import time

import numpy as np
import rerun as rr
from lerobot.utils.utils import init_logging

from lerobot_trial._rust import DoraNode

NO_DATA_SLEEP_INTERVAL = 5e-3  # seconds

logger = logging.getLogger(__name__)


def get_python_log_level() -> str:
    return os.getenv("PYTHON_LOG", "INFO").upper()


def get_rerun_session_name() -> str:
    return os.getenv("RERUN_SESSION_NAME", "lerobot_trial_session")


def get_rerun_server_address() -> str:
    return os.getenv("RERUN_SERVER_ADDRESS", "rerun+http://127.0.0.1:9876/proxy")


def main() -> None:
    node = DoraNode()
    logger.info("DoraNode initialized successfully")

    rr.init(get_rerun_session_name())
    rr.connect_grpc(get_rerun_server_address())

    while node.is_running():
        if data := node.try_recv():
            array = np.array(data.array).reshape(data.shape)
            if array.ndim == 1:
                rr.log(data.id, rr.Scalars(array))
            elif array.ndim == 3:
                rr.log(data.id, rr.Image(array))
            else:
                logger.warning(f"Unknown: {data.id=}, {array.dtype=} {array.shape=}")
        else:
            logger.debug("No data received")
            time.sleep(NO_DATA_SLEEP_INTERVAL)


if __name__ == "__main__":
    init_logging(console_level=get_python_log_level())
    main()
