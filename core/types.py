"""Shared type definitions."""

from __future__ import annotations

from typing import Any, TypeAlias

JSONValue: TypeAlias = (
    None | bool | int | float | str | list["JSONValue"] | dict[str, "JSONValue"]
)

JSONObject: TypeAlias = dict[str, JSONValue]


def is_json_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (bool, int, float, str)):
        return True
    if isinstance(value, list):
        return all(is_json_value(v) for v in value)
    if isinstance(value, dict):
        return all(isinstance(k, str) and is_json_value(v) for k, v in value.items())
    return False

