from dataclasses import dataclass


@dataclass
class CommonConfig:
    # Must match with the tick interval in dataflow-*.yaml (dora/timer/millis)
    control_dt: float = 0.1

    def __post_init__(self) -> None:
        self.fps = int(1.0 / self.control_dt)


COMMON_CONFIG = CommonConfig()
