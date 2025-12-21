"""Dora node using Rust-based binding implementation.

This node demonstrates how to use the Rust-implemented DoraHandler and RerunRecorder
that handles Dora event processing and Rerun logging.

## Architecture

- State data (observation.state): Received by Rust, logged to Rerun, passed to Python
- Image data: Read from MJPEG HTTP stream, logged via Rust

## Dora Channels

### Inputs

- state: Robot state data (received by Rust, forwarded to Python)

### Outputs

- None
"""

import logging
import os
import threading
import time

import cv2
from lerobot.utils.utils import init_logging

from lerobot_trial._rust import DoraHandler, RerunRecorder, create_handlers

NO_DATA_SLEEP_INTERVAL = 5e-3  # seconds

logger = logging.getLogger(__name__)


def get_python_log_level() -> str:
    return os.getenv("PYTHON_LOG", "INFO").upper()


def get_rerun_rrd_path() -> str | None:
    return os.getenv("RERUN_RRD_PATH")


def get_mjpeg_stream_url() -> str:
    host = os.getenv("MJPEG_HOST", "localhost")
    port = os.getenv("MJPEG_PORT", "8080")
    return f"http://{host}:{port}/stream"


def image_logger_thread(rerun: RerunRecorder, dora_handler: DoraHandler) -> None:
    """Thread for reading image data from MJPEG stream and logging to Rerun."""
    logger.info("Starting image logger thread for MJPEG stream")

    stream_url = get_mjpeg_stream_url()
    logger.info(f"Opening MJPEG stream: {stream_url}")

    cap = cv2.VideoCapture(stream_url)
    if not cap.isOpened():
        logger.error(f"Cannot open MJPEG stream {stream_url}")
        return

    try:
        while dora_handler.is_running():
            success, frame = cap.read()
            if not success:
                logger.warning("Failed to read frame from MJPEG stream")
                time.sleep(NO_DATA_SLEEP_INTERVAL)
                continue

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            height, width, _ = frame_rgb.shape

            rerun.log_image("mjpeg_stream/image", frame_rgb.tobytes(), width, height)
            logger.debug(f"Logged image from MJPEG stream: {width}x{height}")

    except (cv2.error, OSError, ValueError) as e:
        logger.error(f"Error in image logger thread: {e}")
    finally:
        cap.release()
        logger.info("Image logger thread exiting")


def main() -> None:
    # Create DoraHandler and RerunRecorder together
    dora_handler, rerun = create_handlers(get_rerun_rrd_path())
    logger.info("DoraHandler and RerunRecorder initialized successfully")

    image_thread = threading.Thread(
        target=image_logger_thread,
        args=(rerun, dora_handler),
        daemon=True,
    )
    image_thread.start()

    # Main loop: receive state data
    while dora_handler.is_running():
        # Receive state data from Rust (already logged by Rust)
        if state_data := dora_handler.try_recv():
            logger.debug(f"Received state data: {state_data.id}")
            # State data is already logged by Rust, just receive it
            # Process state data here if needed
        else:
            time.sleep(NO_DATA_SLEEP_INTERVAL)

    image_thread.join(timeout=5.0)


if __name__ == "__main__":
    init_logging(console_level=get_python_log_level())
    main()
