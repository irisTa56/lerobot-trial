"""FastAPI application for LeRobot control loop.

## HTTP Endpoints

- GET `/health`: Health check endpoint
- POST `/control/start`: Start control loop and recording
- POST `/control/stop`: Stop control loop and recording
- POST `/control/reset`: Reset the gym environment
"""

import logging
import threading
from typing import Protocol, cast

from fastapi import FastAPI, status
from starlette.datastructures import State

from lerobot_trial._rust import DoraHandler, RerunRecorder

logger = logging.getLogger(__name__)


class ControlState:
    """Thread-safe control state for start/stop functionality."""

    def __init__(self) -> None:
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start control loop. Returns True if state changed, False if already running."""
        with self._lock:
            if self._running:
                return False
            self._running = True
            return True

    def stop(self) -> bool:
        """Stop control loop. Returns True if state changed, False if already stopped."""
        with self._lock:
            if not self._running:
                return False
            self._running = False
            return True

    def is_running(self) -> bool:
        with self._lock:
            return self._running


class AppStateProtocol(Protocol):
    control_state: ControlState
    rerun_recorder: RerunRecorder
    dora_handler: DoraHandler


app = FastAPI(
    title="LeRobot Control Server",
    description="HTTP server for controlling LeRobot control loop",
)
app.state = State()


def get_state() -> AppStateProtocol:
    """Get application state with type safety."""
    return cast(AppStateProtocol, app.state)


def set_state(
    control_state: ControlState,
    rerun_recorder: RerunRecorder,
    dora_handler: DoraHandler,
) -> None:
    """Set application state."""
    state = cast(AppStateProtocol, app.state)
    state.control_state = control_state
    state.rerun_recorder = rerun_recorder
    state.dora_handler = dora_handler


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/control/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_control() -> None:
    """Start control loop and start recording."""
    state = get_state()

    if state.control_state.start():
        logger.info("Control loop started via HTTP")
        state.rerun_recorder.start_recording()
        logger.info("Rerun recording started")
    else:
        logger.info("Control loop start requested but already running")


@app.post("/control/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_control() -> None:
    """Stop control loop and stop recording."""
    state = get_state()

    if state.control_state.stop():
        logger.info("Control loop stopped via HTTP")
        state.rerun_recorder.stop_recording()
        logger.info("Rerun recording stopped")
    else:
        logger.info("Control loop stop requested but already stopped")


@app.post("/control/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_environment() -> None:
    """Reset the gym environment."""
    state = get_state()

    state.dora_handler.send_reset()
    logger.info("Reset command sent to gym_aloha")
