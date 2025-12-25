"""FastAPI application for LeRobot control loop.

## HTTP Endpoints

- GET `/status`: Get control loop status
- POST `/control/start`: Start control loop and recording
- POST `/control/stop`: Stop control loop and recording
- POST `/control/reset`: Reset the gym environment
"""

from fastapi import FastAPI, HTTPException, status

from lerobot_trial._rust import DoraHandler, RerunClient
from lerobot_trial.control_state import ControlState


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

    @app.get("/status")
    async def get_status() -> dict[str, bool]:
        """Get control loop status."""
        return {"running": control_state.is_running()}

    @app.post("/control/start")
    async def start_control() -> dict[str, bool]:
        """Start control loop and start recording."""
        if not control_state.start():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Control loop is already running",
            )
        rerun_recorder.start_recording()
        return {"running": True}

    @app.post("/control/stop")
    async def stop_control() -> dict[str, bool]:
        """Stop control loop and stop recording."""
        if not control_state.stop():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Control loop is already stopped",
            )
        rerun_recorder.stop_recording()
        return {"running": False}

    @app.post("/control/reset")
    async def reset_environment() -> dict[str, bool]:
        """Reset the gym environment."""
        dora_handler.send_reset()
        return {"running": control_state.is_running()}

    return app
