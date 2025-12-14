"""Dora node using Rust-based binding implementation.

This node demonstrates how to use the Rust-implemented DoraHandler and RerunRecorder
that handles Dora event processing and Rerun logging.

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
from lerobot.utils.utils import init_logging

from lerobot_trial._rust import DoraHandler, RerunRecorder

NO_DATA_SLEEP_INTERVAL = 5e-3  # seconds

logger = logging.getLogger(__name__)


def get_python_log_level() -> str:
    return os.getenv("PYTHON_LOG", "INFO").upper()


def get_rerun_rrd_path() -> str | None:
    return os.getenv("RERUN_RRD_PATH")


def main() -> None:
    dora = DoraHandler()
    rerun = RerunRecorder(get_rerun_rrd_path())
    logger.info("DoraHandler and RerunRecorder initialized successfully")

    while dora.is_running():
        if data := dora.try_recv():
            array = np.array(data.array).reshape(data.shape)
            match array.shape:
                case (_,) if array.dtype == np.float64:
                    rerun.log_scalars(data.id, array.tolist())
                case (height, width, 3) if array.dtype == np.uint8:
                    rerun.log_rgb_image(data.id, array.tobytes(), width, height)
                case _:
                    logger.warning(f"Unknown data: {data.id} - {type(array)}")
        else:
            logger.debug("No data received")
            time.sleep(NO_DATA_SLEEP_INTERVAL)


if __name__ == "__main__":
    init_logging(console_level=get_python_log_level())
    main()
