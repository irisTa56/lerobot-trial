"""FastAPI application for LeRobot control loop.

## HTTP Endpoints

- GET `/health`: Health check endpoint
- POST `/control/start`: Start control loop and recording
- POST `/control/stop`: Stop control loop and recording
- POST `/control/reset`: Reset the gym environment
"""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, status

from lerobot_trial._rust import DoraHandler, RerunClient
from lerobot_trial.control_state import ControlState

logger = logging.getLogger(__name__)


def create_app(
    control_state: ControlState,
    rerun_recorder: RerunClient,
    dora_handler: DoraHandler,
) -> FastAPI:
    """Create FastAPI application with dependencies.

    Args:
        control_state: Control loop state manager
        rerun_recorder: Rerun recording client
        dora_handler: Dora dataflow handler

    Returns:
        Configured FastAPI application

    """
    app = FastAPI(
        title="LeRobot Control Server",
        description="HTTP server for controlling LeRobot control loop",
    )

    def get_control_state() -> ControlState:
        return control_state

    def get_rerun_recorder() -> RerunClient:
        return rerun_recorder

    def get_dora_handler() -> DoraHandler:
        return dora_handler

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Health check endpoint."""
        return {"status": "healthy"}

    @app.post("/control/start", status_code=status.HTTP_204_NO_CONTENT)
    async def start_control(
        state: Annotated[ControlState, Depends(get_control_state)],
        recorder: Annotated[RerunClient, Depends(get_rerun_recorder)],
    ) -> None:
        """Start control loop and start recording."""
        if state.start():
            logger.info("Control loop started via HTTP")
            recorder.start_recording()
            logger.info("Rerun recording started")
        else:
            logger.info("Control loop start requested but already running")

    @app.post("/control/stop", status_code=status.HTTP_204_NO_CONTENT)
    async def stop_control(
        state: Annotated[ControlState, Depends(get_control_state)],
        recorder: Annotated[RerunClient, Depends(get_rerun_recorder)],
    ) -> None:
        """Stop control loop and stop recording."""
        if state.stop():
            logger.info("Control loop stopped via HTTP")
            recorder.stop_recording()
            logger.info("Rerun recording stopped")
        else:
            logger.info("Control loop stop requested but already stopped")

    @app.post("/control/reset", status_code=status.HTTP_204_NO_CONTENT)
    async def reset_environment(
        handler: Annotated[DoraHandler, Depends(get_dora_handler)],
    ) -> None:
        """Reset the gym environment."""
        handler.send_reset()
        logger.info("Reset command sent to gym_aloha")

    return app
