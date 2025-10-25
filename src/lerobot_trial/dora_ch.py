"""Utilities for working with Dora channels."""

from enum import Enum
from typing import Any

import pyarrow as pa
from dora import Node

type DoraEvent = dict[str, Any]


class ChannelId(str, Enum):
    ACTION = "action"
    CONTROL = "control"
    EPISODE = "episode"
    SUCCESS = "success"

    def __str__(self) -> str:
        return self.value


class ControlCmd(str, Enum):
    ESC = "ESC"
    CTRL = "CTRL"
    SPACE = "SPACE"

    def __str__(self) -> str:
        return self.value

    @staticmethod
    def from_event(event: DoraEvent) -> "ControlCmd":
        return ControlCmd(parse_single_value_in_event(event))

    def to_message(self) -> pa.Array:
        return pa.array([self.value])


def try_recv_event(node: Node) -> dict[str, Any] | None:
    return node.next(timeout=0.001)


def is_timeout_event(event: dict[str, Any]) -> bool:
    error = event.get("error")
    return isinstance(error, str) and error.startswith("Timeout event stream error")


def make_dict_message[T: str](value: dict[T, Any]) -> pa.Array:
    return pa.array([pa.scalar(value)])


def parse_single_value_in_event(event: DoraEvent) -> Any:
    return event["value"][0].as_py()
