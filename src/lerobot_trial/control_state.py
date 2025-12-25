"""Thread-safe control state for start/stop functionality."""

import threading


class ControlState:
    """Thread-safe control state for start/stop functionality."""

    def __init__(self) -> None:
        self._running = False
        self._lock = threading.Lock()

    def start(self) -> bool:
        """Start control loop.

        Returns True if state changed, False if already running.
        """
        with self._lock:
            if self._running:
                return False
            self._running = True
            return True

    def stop(self) -> bool:
        """Stop control loop.

        Returns True if state changed, False if already stopped.
        """
        with self._lock:
            if not self._running:
                return False
            self._running = False
            return True

    def is_running(self) -> bool:
        with self._lock:
            return self._running
