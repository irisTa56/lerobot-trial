"""FastAPI application for Dora dataflow integration.

## HTTP Endpoints

- GET `/health`: Health check endpoint
- GET `/status`: Get current node status
- GET `/data`: Get all stored data
- POST `/data`: Post data to be processed by the dataflow

## Running Standalone

    uvicorn lerobot_trial.http.app:app --host 0.0.0.0 --port 8000
"""

import logging
import os
from typing import Any

import pyarrow as pa
from fastapi import FastAPI, HTTPException

from lerobot_trial.http.client import DoraClient

logger = logging.getLogger(__name__)

# Global Dora client instance shared between FastAPI app and Dora node
dora_client = DoraClient()


app = FastAPI(
    title="Dora HTTP Server Node",
    description="HTTP server for Dora dataflow",
)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint.

    Returns:
        Health status.

    """
    return {"status": "healthy"}


@app.get("/status")
async def status() -> dict[str, Any]:
    """Get current node status.

    Returns:
        Node status including Dora availability and data store size.

    """
    return {
        "dora_available": dora_client.is_available(),
        "data_store_size": len(dora_client.data_store),
        "dora_node_id": os.getenv("DORA_NODE_ID"),
    }


@app.get("/data")
async def get_data() -> dict[str, Any]:
    """Get all stored data.

    Returns:
        All data stored in the data store.

    """
    return {"data": dora_client.data_store}


@app.post("/data")
async def post_data(data: dict[str, Any]) -> dict[str, str]:
    """Post data to be forwarded to Dora dataflow.

    Args:
        data: Dictionary of key-value pairs to forward.

    Returns:
        Success message.

    Raises:
        HTTPException: If Dora node is not available or processing fails.

    """
    if not dora_client.is_available():
        raise HTTPException(
            status_code=503,
            detail="Dora node not available. Server running in standalone mode.",
        )

    try:
        dora_client.data_store.update(data)
        dora_client.send_output("request", pa.array([pa.Table.from_pydict(data)]))
        return {"status": "success", "message": "Data forwarded to dataflow"}
    except Exception as e:
        logger.exception("Failed to process data")
        raise HTTPException(status_code=500, detail=str(e)) from e
