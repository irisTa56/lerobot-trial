"""HTTP server node for Dora dataflow.

## Dora Integration

This module provides a Dora Python node that runs a FastAPI application.
The server runs in a background thread and is controlled by the Dora event loop.

## Dora Channels

### Inputs

- `tick`: Timer signal to keep the node alive (dora/timer/secs/1)

### Outputs

- `request`: Output channel for forwarding HTTP POST requests to the dataflow
"""

import contextlib
import logging
import os
import threading
import time
from collections.abc import Generator

import uvicorn
from dora import Node
from lerobot.utils.utils import init_logging

from lerobot_trial.http.app import app, dora_client

logger = logging.getLogger(__name__)


class UvicornServer(uvicorn.Server):
    """Uvicorn server for running in background thread."""

    @contextlib.contextmanager
    def run_in_thread(self) -> Generator[None, None, None]:
        """Run server in background thread with context manager.

        Yields:
            Server is ready to accept connections.

        """
        thread = threading.Thread(target=self.run, daemon=True)
        thread.start()
        try:
            # Wait for server to be ready
            while not self.started:
                time.sleep(1e-3)
            yield
        finally:
            logger.info("Shutting down HTTP server")
            self.should_exit = True
            thread.join(timeout=3.0)
            logger.info("HTTP server stopped")


def main() -> None:
    host = os.getenv("HTTP_HOST", "0.0.0.0")
    port = int(os.getenv("HTTP_PORT", "8000"))

    config = uvicorn.Config(app, host=host, port=port)
    server = UvicornServer(config=config)

    with server.run_in_thread():
        node = Node()
        dora_client.set_node(node)

        for event in node:
            match (event["type"], event.get("id")):
                case ("INPUT", "tick"):
                    pass  # Keep-alive tick, do nothing
                case ("STOP", _):
                    logger.info("Received stop signal from Dora.")
                case _:
                    logger.warning(f"Unexpected event: {event}")


if __name__ == "__main__":
    init_logging(console_level=os.getenv("PYTHON_LOG", "INFO"))
    main()
