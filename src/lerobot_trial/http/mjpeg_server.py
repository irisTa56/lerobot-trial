"""MJPEG streaming server for sharing camera images over HTTP."""

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import cv2
from numpy.typing import NDArray

logger = logging.getLogger(__name__)


class _FrameHolder:
    def __init__(self) -> None:
        self.frame: NDArray | None = None
        self.lock = threading.Lock()
        self.event = threading.Event()

    def update(self, frame: NDArray) -> None:
        with self.lock:
            self.frame = frame.copy()
        self.event.set()

    def get(self) -> NDArray | None:
        with self.lock:
            return self.frame

    def wait_for_update(self, timeout: float | None = None) -> bool:
        result = self.event.wait(timeout)
        self.event.clear()
        return result


_frame_holder = _FrameHolder()


class MJPEGStreamHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args: object) -> None:
        pass  # Suppress HTTP server logging

    def do_GET(self) -> None:
        if self.path == "/stream":
            self.send_response(200)
            self.send_header(
                "Content-Type", "multipart/x-mixed-replace; boundary=frame"
            )
            self.end_headers()

            try:
                while True:
                    _frame_holder.wait_for_update(timeout=1.0)
                    frame = _frame_holder.get()
                    if frame is None:
                        continue
                    _, jpeg = cv2.imencode(".jpg", frame)
                    frame_bytes = jpeg.tobytes()
                    self.wfile.write(b"--frame\r\n")
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(frame_bytes)))
                    self.end_headers()
                    self.wfile.write(frame_bytes)
                    self.wfile.write(b"\r\n")
            except (BrokenPipeError, ConnectionResetError):
                logger.debug("Client disconnected")
        else:
            self.send_error(404)


def update_frame(frame: NDArray) -> None:
    """Update the latest frame (BGR format)."""
    _frame_holder.update(frame)


def start_mjpeg_server(host: str = "localhost", port: int = 8080) -> None:
    """Start MJPEG server in background thread."""
    server = HTTPServer((host, port), MJPEGStreamHandler)
    logger.info(f"MJPEG server started at http://{host}:{port}/stream")
    threading.Thread(target=server.serve_forever, daemon=True).start()
