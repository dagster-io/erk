"""Tests for JSON output utility functions: emit_json, emit_json_result, read_stdin_json."""

import json
from dataclasses import dataclass
from typing import Any

import pytest

from erk_shared.agentclick.json_command import emit_json, emit_json_result


def test_emit_json_adds_success(capsys: pytest.CaptureFixture[str]) -> None:
    """emit_json adds success=True to output."""
    emit_json({"key": "value"})
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["success"] is True
    assert data["key"] == "value"


def test_emit_json_result_with_to_json_dict(capsys: pytest.CaptureFixture[str]) -> None:
    """emit_json_result uses to_json_dict() when available."""

    @dataclass(frozen=True)
    class MyResult:
        value: int

        def to_json_dict(self) -> dict[str, Any]:
            return {"custom": self.value * 2}

    emit_json_result(MyResult(value=21))
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["success"] is True
    assert data["custom"] == 42


def test_emit_json_result_with_plain_dataclass(capsys: pytest.CaptureFixture[str]) -> None:
    """emit_json_result falls back to dataclasses.asdict for plain dataclasses."""

    @dataclass(frozen=True)
    class PlainResult:
        name: str
        count: int

    emit_json_result(PlainResult(name="test", count=7))
    captured = capsys.readouterr()
    data = json.loads(captured.out.strip())
    assert data["success"] is True
    assert data["name"] == "test"
    assert data["count"] == 7


def test_emit_json_result_non_dataclass_raises() -> None:
    """emit_json_result raises TypeError for non-serializable objects."""
    with pytest.raises(TypeError, match="Cannot serialize"):
        emit_json_result("not a dataclass")
