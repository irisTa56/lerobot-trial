"""Dora client for sharing state between Dora node and FastAPI app."""

import logging
from typing import Any

import pyarrow as pa
from dora import Node

logger = logging.getLogger(__name__)


class DoraClient:
    """Client for interacting with Dora dataflow.

    This class provides a bridge between the Dora node and the FastAPI application,
    allowing them to share state and send outputs to the dataflow.
    """

    def __init__(self) -> None:
        """Initialize Dora client."""
        self.node: Node | None = None
        self.data_store: dict[str, Any] = {}

    def set_node(self, node: Node) -> None:
        """Set Dora node instance.

        Args:
            node: Dora node instance.

        """
        self.node = node
        logger.info("Dora node set")

    def send_output(
        self,
        output_id: str,
        data: pa.Array,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Send output to Dora dataflow.

        Args:
            output_id: Output channel ID.
            data: PyArrow array to send.
            metadata: Optional metadata.

        Raises:
            RuntimeError: If Dora node is not initialized.

        """
        if self.node is None:
            raise RuntimeError("Dora node not initialized")
        self.node.send_output(output_id, data, metadata or {})

    def is_available(self) -> bool:
        """Check if Dora node is available.

        Returns:
            True if Dora node is initialized, False otherwise.

        """
        return self.node is not None
