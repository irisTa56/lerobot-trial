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

from lerobot.utils.utils import init_logging

from lerobot_trial._rust import DoraNode

logger = logging.getLogger(__name__)


def main() -> None:
    node = DoraNode()
    logger.info("DoraNode initialized successfully")

    while node.is_running():
        if data := node.try_recv():
            logger.debug(f"Received data: {data.id=}, {type(data.array)=}")
        else:
            logger.debug("No data received")
            time.sleep(0.1)


if __name__ == "__main__":
    init_logging(console_level=os.getenv("PYTHON_LOG", "INFO"))
    main()
