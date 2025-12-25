"""FastAPI application for LeRobot control loop.

## HTTP Endpoints

- GET `/status`: Get control loop status
- POST `/control/start`: Start control loop and recording
- POST `/control/stop`: Stop control loop and recording
- POST `/control/reset`: Reset the gym environment
"""

import logging
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

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

    @app.get("/status")
    async def get_status(
        state: Annotated[ControlState, Depends(get_control_state)],
    ) -> dict[str, bool]:
        """Get control loop status."""
        return {"running": state.is_running()}

    @app.post("/control/start")
    async def start_control(
        state: Annotated[ControlState, Depends(get_control_state)],
        recorder: Annotated[RerunClient, Depends(get_rerun_recorder)],
    ) -> dict[str, bool]:
        """Start control loop and start recording."""
        if not state.start():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Control loop is already running",
            )
        recorder.start_recording()
        return {"running": True}

    @app.post("/control/stop")
    async def stop_control(
        state: Annotated[ControlState, Depends(get_control_state)],
        recorder: Annotated[RerunClient, Depends(get_rerun_recorder)],
    ) -> dict[str, bool]:
        """Stop control loop and stop recording."""
        if not state.stop():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Control loop is already stopped",
            )
        recorder.stop_recording()
        return {"running": False}

    @app.post("/control/reset")
    async def reset_environment(
        state: Annotated[ControlState, Depends(get_control_state)],
        handler: Annotated[DoraHandler, Depends(get_dora_handler)],
    ) -> dict[str, bool]:
        """Reset the gym environment."""
        handler.send_reset()
        return {"running": state.is_running()}

    return app
