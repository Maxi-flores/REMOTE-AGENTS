from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List


def utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


@dataclass
class ImplementationPackage:
    package_id: str
    generated_utc: str
    source_batch_id: str
    title: str
    objective: str
    target_files: List[str]
    expected_changes: Dict[str, Any]
    validation_commands: List[str]
    risks: List[str]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "package_id": self.package_id,
            "generated_utc": self.generated_utc,
            "source_batch_id": self.source_batch_id,
            "title": self.title,
            "objective": self.objective,
            "target_files": list(self.target_files),
            "expected_changes": dict(self.expected_changes),
            "validation_commands": list(self.validation_commands),
            "risks": list(self.risks),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class CodexImplementationPrompt:
    prompt_id: str
    package_id: str
    prompt_text: str
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "package_id": self.package_id,
            "prompt_text": self.prompt_text,
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


@dataclass
class ImplementationPackageReport:
    report_id: str
    generated_utc: str
    source_remediation_report_id: str
    packages: List[Dict[str, Any]]
    advisory_only: bool
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "report_id": self.report_id,
            "generated_utc": self.generated_utc,
            "source_remediation_report_id": self.source_remediation_report_id,
            "packages": list(self.packages),
            "advisory_only": bool(self.advisory_only),
            "metadata": dict(self.metadata),
        }


def validate_implementation_package_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "package_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_batch_id")
    _require_str(payload, "title")
    _require_str(payload, "objective")
    _require_list(payload, "target_files")
    _require_dict(payload, "expected_changes")
    _require_list(payload, "validation_commands")
    _require_list(payload, "risks")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_codex_implementation_prompt_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "prompt_id")
    _require_str(payload, "package_id")
    _require_str(payload, "prompt_text")
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def validate_implementation_package_report_dict(payload: Dict[str, Any]) -> None:
    _require_str(payload, "report_id")
    _require_str(payload, "generated_utc")
    _require_str(payload, "source_remediation_report_id")
    _require_list(payload, "packages")
    for package in payload.get("packages", []):
        if isinstance(package, dict):
            validate_implementation_package_dict(package)
            if isinstance(package.get("codex_prompt"), dict):
                validate_codex_implementation_prompt_dict(package["codex_prompt"])
    _require_bool(payload, "advisory_only")
    _require_dict(payload, "metadata")


def _require_str(payload: Dict[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} required")
    return value


def _require_list(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), list):
        raise ValueError(f"{key} must be list")


def _require_dict(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), dict):
        raise ValueError(f"{key} must be dict")


def _require_bool(payload: Dict[str, Any], key: str) -> None:
    if not isinstance(payload.get(key), bool):
        raise ValueError(f"{key} must be bool")
