"""FastAPI application for LeRobot control loop.

## HTTP Endpoints

- GET `/health`: Health check endpoint
- POST `/control/start`: Start control loop and recording
- POST `/control/stop`: Stop control loop and recording
- POST `/control/reset`: Reset the gym environment
"""

import logging
from typing import Annotated, Protocol, cast

from fastapi import Depends, FastAPI, status

from lerobot_trial._rust import DoraHandler, RerunClient
from lerobot_trial.control_state import ControlState

logger = logging.getLogger(__name__)


class AppStateProtocol(Protocol):
    control_state: ControlState
    rerun_recorder: RerunClient
    dora_handler: DoraHandler


app = FastAPI(
    title="LeRobot Control Server",
    description="HTTP server for controlling LeRobot control loop",
)


def set_state(
    control_state: ControlState,
    rerun_recorder: RerunClient,
    dora_handler: DoraHandler,
) -> None:
    state = _get_state()
    state.control_state = control_state
    state.rerun_recorder = rerun_recorder
    state.dora_handler = dora_handler


def _get_state() -> AppStateProtocol:
    return cast(AppStateProtocol, app.state)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/control/start", status_code=status.HTTP_204_NO_CONTENT)
async def start_control(
    state: Annotated[AppStateProtocol, Depends(_get_state)],
) -> None:
    """Start control loop and start recording."""

    if state.control_state.start():
        logger.info("Control loop started via HTTP")
        state.rerun_recorder.start_recording()
        logger.info("Rerun recording started")
    else:
        logger.info("Control loop start requested but already running")


@app.post("/control/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_control(
    state: Annotated[AppStateProtocol, Depends(_get_state)],
) -> None:
    """Stop control loop and stop recording."""

    if state.control_state.stop():
        logger.info("Control loop stopped via HTTP")
        state.rerun_recorder.stop_recording()
        logger.info("Rerun recording stopped")
    else:
        logger.info("Control loop stop requested but already stopped")


@app.post("/control/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_environment(
    state: Annotated[AppStateProtocol, Depends(_get_state)],
) -> None:
    """Reset the gym environment."""

    state.dora_handler.send_reset()
    logger.info("Reset command sent to gym_aloha")
