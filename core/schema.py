"""Minimal JSON-schema-like validation and deterministic hashing.

This module intentionally implements a small subset of JSON Schema, enough for
strict payload validation in the handshake pipeline without third-party deps.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Iterable

from core.types import JSONValue, JSONObject, is_json_value


class SchemaValidationError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class Schema:
    schema_id: str
    definition: JSONObject

    def canonical_definition(self) -> str:
        return canonical_json(self.definition)

    def hash(self) -> str:
        return sha256_hex(self.canonical_definition().encode("utf-8"))


def canonical_json(value: JSONValue) -> str:
    if not is_json_value(value):
        raise TypeError("Value is not JSON-serializable within declared JSONValue.")
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signature_for(schema: Schema, payload: JSONValue) -> str:
    payload_canon = canonical_json(payload)
    material = f"{schema.hash()}:{payload_canon}".encode("utf-8")
    return sha256_hex(material)


def validate_against_schema(payload: Any, schema_def: JSONObject) -> None:
    _validate(payload, schema_def, path="$")


def _validate(value: Any, schema_def: JSONObject, *, path: str) -> None:
    if "type" not in schema_def:
        raise SchemaValidationError(f"{path}: schema missing 'type'")

    expected_type = schema_def["type"]
    if expected_type == "object":
        if not isinstance(value, dict):
            raise SchemaValidationError(f"{path}: expected object")
        _validate_object(value, schema_def, path=path)
        return
    if expected_type == "array":
        if not isinstance(value, list):
            raise SchemaValidationError(f"{path}: expected array")
        items = schema_def.get("items")
        if isinstance(items, dict):
            for idx, item in enumerate(value):
                _validate(item, items, path=f"{path}[{idx}]")
        return
    if expected_type == "string":
        if not isinstance(value, str):
            raise SchemaValidationError(f"{path}: expected string")
        return
    if expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            raise SchemaValidationError(f"{path}: expected integer")
        return
    if expected_type == "number":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise SchemaValidationError(f"{path}: expected number")
        return
    if expected_type == "boolean":
        if not isinstance(value, bool):
            raise SchemaValidationError(f"{path}: expected boolean")
        return
    if expected_type == "null":
        if value is not None:
            raise SchemaValidationError(f"{path}: expected null")
        return

    raise SchemaValidationError(f"{path}: unsupported schema type: {expected_type!r}")


def _validate_object(value: dict[str, Any], schema_def: JSONObject, *, path: str) -> None:
    properties = schema_def.get("properties")
    if properties is not None and not isinstance(properties, dict):
        raise SchemaValidationError(f"{path}: properties must be object")

    required = schema_def.get("required", [])
    if not isinstance(required, list) or not all(isinstance(x, str) for x in required):
        raise SchemaValidationError(f"{path}: required must be list[str]")

    additional = schema_def.get("additionalProperties", False)
    if not isinstance(additional, bool):
        raise SchemaValidationError(f"{path}: additionalProperties must be boolean")

    for key in required:
        if key not in value:
            raise SchemaValidationError(f"{path}: missing required key {key!r}")

    if properties:
        for key, prop_schema in properties.items():
            if key not in value:
                continue
            if not isinstance(prop_schema, dict):
                raise SchemaValidationError(f"{path}.{key}: property schema must be object")
            _validate(value[key], prop_schema, path=f"{path}.{key}")

    if not additional and properties is not None:
        allowed = set(properties.keys())
        extras = [k for k in value.keys() if k not in allowed]
        if extras:
            raise SchemaValidationError(f"{path}: unexpected keys: {', '.join(extras)}")


def ensure_keys(value: dict[str, Any], *, required: Iterable[str], path: str) -> None:
    for key in required:
        if key not in value:
            raise SchemaValidationError(f"{path}: missing required key {key!r}")

