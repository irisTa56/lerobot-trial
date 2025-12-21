def hello_from_bin() -> str: ...
def create_handlers(
    rrd_path: str | None = None,
) -> tuple[DoraHandler, RerunRecorder]: ...

class DoraHandler:
    def try_recv(self) -> DoraInput | None: ...
    def is_running(self) -> bool: ...
    def send_action(self, data: list[float]) -> None: ...

class DoraInput:
    id: str
    array: object
    shape: list[int]

class RerunRecorder:
    def log_image(
        self,
        path: str,
        data: bytes,
        width: int,
        height: int,
    ) -> None: ...
    def is_running(self) -> bool: ...
