import json
from pathlib import Path

from .exceptions import SchemaMismatchedException


class SchemaValidator:
    def __init__(self, schema_dir: Path) -> None:
        self._schema_dir = schema_dir
        self._cache: dict[str, dict] = {}

    def load_schema(self, schema_file: str) -> dict:
        if schema_file in self._cache:
            return self._cache[schema_file]
        path = self._schema_dir / schema_file
        if not path.exists():
            raise SchemaMismatchedException(f"Schema not found: {path}")
        schema = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(schema, dict):
            raise SchemaMismatchedException(f"Schema root must be an object: {schema_file}")
        self._cache[schema_file] = schema
        return schema

    def validate(self, schema_file: str, instance: object) -> None:
        schema = self.load_schema(schema_file)
        self._validate_node(schema, instance, path="$")

    def _fail(self, path: str, msg: str) -> None:
        raise SchemaMismatchedException(f"{path}: {msg}")

    def _validate_node(self, schema: dict, instance: object, path: str) -> None:
        if "const" in schema:
            if instance != schema["const"]:
                self._fail(path, f"Expected const={schema['const']!r}, got {instance!r}")

        if "enum" in schema:
            allowed = schema["enum"]
            if instance not in allowed:
                self._fail(path, f"Expected one of {allowed!r}, got {instance!r}")

        expected_type = schema.get("type")
        if expected_type is not None:
            self._validate_type(expected_type, instance, path)

        if expected_type == "object":
            self._validate_object(schema, instance, path)
        elif expected_type == "array":
            self._validate_array(schema, instance, path)
        elif expected_type == "string":
            self._validate_string(schema, instance, path)
        elif expected_type == "number":
            self._validate_number(schema, instance, path)

    def _validate_type(self, expected_type: str, instance: object, path: str) -> None:
        if expected_type == "object":
            if not isinstance(instance, dict):
                self._fail(path, f"Expected object, got {type(instance).__name__}")
        elif expected_type == "array":
            if not isinstance(instance, list):
                self._fail(path, f"Expected array, got {type(instance).__name__}")
        elif expected_type == "string":
            if not isinstance(instance, str):
                self._fail(path, f"Expected string, got {type(instance).__name__}")
        elif expected_type == "boolean":
            if not isinstance(instance, bool):
                self._fail(path, f"Expected boolean, got {type(instance).__name__}")
        elif expected_type == "number":
            if isinstance(instance, bool) or not isinstance(instance, (int, float)):
                self._fail(path, f"Expected number, got {type(instance).__name__}")
        else:
            self._fail(path, f"Unsupported schema type: {expected_type!r}")

    def _validate_object(self, schema: dict, instance: object, path: str) -> None:
        if not isinstance(instance, dict):
            self._fail(path, f"Expected object, got {type(instance).__name__}")

        required = schema.get("required", [])
        if required:
            if not isinstance(required, list):
                self._fail(path, "Schema 'required' must be an array")
            for key in required:
                if key not in instance:
                    self._fail(path, f"Missing required key: {key!r}")

        properties = schema.get("properties", {}) or {}
        if properties and not isinstance(properties, dict):
            self._fail(path, "Schema 'properties' must be an object")

        additional = schema.get("additionalProperties", True)
        if additional is False and properties:
            for key in instance.keys():
                if key not in properties:
                    self._fail(path, f"Unexpected key (additionalProperties=false): {key!r}")

        for key, prop_schema in properties.items():
            if key in instance:
                if not isinstance(prop_schema, dict):
                    self._fail(f"{path}.{key}", "Property schema must be an object")
                self._validate_node(prop_schema, instance[key], path=f"{path}.{key}")

    def _validate_array(self, schema: dict, instance: object, path: str) -> None:
        if not isinstance(instance, list):
            self._fail(path, f"Expected array, got {type(instance).__name__}")

        min_items = schema.get("minItems")
        if min_items is not None:
            if not isinstance(min_items, int):
                self._fail(path, "Schema 'minItems' must be an integer")
            if len(instance) < min_items:
                self._fail(path, f"Expected at least {min_items} items, got {len(instance)}")

        items_schema = schema.get("items")
        if items_schema is not None:
            if not isinstance(items_schema, dict):
                self._fail(path, "Schema 'items' must be an object")
            for idx, item in enumerate(instance):
                self._validate_node(items_schema, item, path=f"{path}[{idx}]")

    def _validate_string(self, schema: dict, instance: object, path: str) -> None:
        if not isinstance(instance, str):
            self._fail(path, f"Expected string, got {type(instance).__name__}")
        min_len = schema.get("minLength")
        if min_len is not None:
            if not isinstance(min_len, int):
                self._fail(path, "Schema 'minLength' must be an integer")
            if len(instance) < min_len:
                self._fail(path, f"Expected minLength {min_len}, got {len(instance)}")

    def _validate_number(self, schema: dict, instance: object, path: str) -> None:
        if isinstance(instance, bool) or not isinstance(instance, (int, float)):
            self._fail(path, f"Expected number, got {type(instance).__name__}")
        minimum = schema.get("minimum")
        if minimum is not None and instance < minimum:
            self._fail(path, f"Expected minimum {minimum}, got {instance}")
        maximum = schema.get("maximum")
        if maximum is not None and instance > maximum:
            self._fail(path, f"Expected maximum {maximum}, got {instance}")
