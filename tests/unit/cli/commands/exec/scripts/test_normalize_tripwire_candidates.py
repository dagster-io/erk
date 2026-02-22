"""Tests for erk exec normalize-tripwire-candidates command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.normalize_tripwire_candidates import (
    normalize_tripwire_candidates,
)


def _write_json(tmp_path: Path, data: dict) -> Path:
    """Write JSON data to a file and return its path."""
    json_file = tmp_path / "tripwire-candidates.json"
    json_file.write_text(json.dumps(data), encoding="utf-8")
    return json_file


def test_already_correct_passes_through(tmp_path: Path) -> None:
    """Already-correct JSON passes through with normalized=false."""
    candidates_file = _write_json(
        tmp_path,
        {
            "candidates": [
                {
                    "action": "calling foo()",
                    "warning": "Use bar() instead.",
                    "target_doc_path": "architecture/foo.md",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["normalized"] is False
    assert output["count"] == 1


def test_root_key_tripwire_candidates_normalized(tmp_path: Path) -> None:
    """tripwire_candidates root key gets normalized to candidates."""
    candidates_file = _write_json(
        tmp_path,
        {
            "tripwire_candidates": [
                {
                    "action": "calling foo()",
                    "warning": "Use bar().",
                    "target_doc_path": "architecture/foo.md",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["normalized"] is True
    assert output["count"] == 1

    # Verify file was rewritten with correct root key
    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    assert "candidates" in rewritten
    assert "tripwire_candidates" not in rewritten


def test_description_mapped_to_warning(tmp_path: Path) -> None:
    """description field gets mapped to warning."""
    candidates_file = _write_json(
        tmp_path,
        {
            "candidates": [
                {
                    "action": "calling foo()",
                    "description": "Use bar() instead.",
                    "target_doc_path": "architecture/foo.md",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["normalized"] is True

    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    candidate = rewritten["candidates"][0]
    assert candidate["warning"] == "Use bar() instead."
    assert "description" not in candidate


def test_title_mapped_to_action(tmp_path: Path) -> None:
    """title field gets mapped to action."""
    candidates_file = _write_json(
        tmp_path,
        {
            "candidates": [
                {
                    "title": "calling foo()",
                    "warning": "Use bar().",
                    "target_doc_path": "architecture/foo.md",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["normalized"] is True

    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    candidate = rewritten["candidates"][0]
    assert candidate["action"] == "calling foo()"
    assert "title" not in candidate


def test_mixed_schema_normalization(tmp_path: Path) -> None:
    """Mixed schema with some canonical and some drifted fields."""
    candidates_file = _write_json(
        tmp_path,
        {
            "tripwire_candidates": [
                {
                    "title": "editing CI files",
                    "description": "Check template paths first.",
                    "target_doc_path": "ci/templates.md",
                    "priority": "high",
                    "source_files": ["ci.yml"],
                },
                {
                    "action": "modifying gateways",
                    "warning": "Update all 4 implementations.",
                    "target_doc_path": "architecture/gateways.md",
                },
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["normalized"] is True
    assert output["count"] == 2

    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    assert "candidates" in rewritten

    first = rewritten["candidates"][0]
    assert first["action"] == "editing CI files"
    assert first["warning"] == "Check template paths first."
    assert first["target_doc_path"] == "ci/templates.md"
    assert "priority" not in first
    assert "source_files" not in first

    second = rewritten["candidates"][1]
    assert second["action"] == "modifying gateways"
    assert second["warning"] == "Update all 4 implementations."


def test_extra_fields_stripped(tmp_path: Path) -> None:
    """Extra fields are stripped from candidates."""
    candidates_file = _write_json(
        tmp_path,
        {
            "candidates": [
                {
                    "action": "calling foo()",
                    "warning": "Use bar().",
                    "target_doc_path": "architecture/foo.md",
                    "check_type": "pre_edit",
                    "priority": "high",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["normalized"] is True

    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    candidate = rewritten["candidates"][0]
    assert set(candidate.keys()) == {"action", "warning", "target_doc_path"}


def test_empty_candidates(tmp_path: Path) -> None:
    """Empty candidates list passes through unchanged."""
    candidates_file = _write_json(tmp_path, {"candidates": []})

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["normalized"] is False
    assert output["count"] == 0


def test_missing_file(tmp_path: Path) -> None:
    """Error when candidates file does not exist."""
    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(tmp_path / "nonexistent.json")],
    )

    assert result.exit_code == 1


def test_invalid_json(tmp_path: Path) -> None:
    """Error when candidates file has invalid JSON."""
    json_file = tmp_path / "bad.json"
    json_file.write_text("not json", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(json_file)],
    )

    assert result.exit_code == 1


def test_name_mapped_to_action(tmp_path: Path) -> None:
    """name field gets mapped to action."""
    candidates_file = _write_json(
        tmp_path,
        {
            "candidates": [
                {
                    "name": "calling foo()",
                    "warning": "Use bar().",
                    "target_doc_path": "architecture/foo.md",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["normalized"] is True

    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    assert rewritten["candidates"][0]["action"] == "calling foo()"


def test_canonical_field_not_overwritten_by_alias(tmp_path: Path) -> None:
    """When both canonical and alias fields exist, canonical wins."""
    candidates_file = _write_json(
        tmp_path,
        {
            "candidates": [
                {
                    "action": "correct action",
                    "title": "wrong action",
                    "warning": "correct warning",
                    "description": "wrong warning",
                    "target_doc_path": "architecture/foo.md",
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 0
    rewritten = json.loads(candidates_file.read_text(encoding="utf-8"))
    candidate = rewritten["candidates"][0]
    assert candidate["action"] == "correct action"
    assert candidate["warning"] == "correct warning"


def test_unsalvageable_array_root(tmp_path: Path) -> None:
    """JSON array input is unsalvageable and exits 1."""
    json_file = tmp_path / "array.json"
    json_file.write_text("[1, 2, 3]", encoding="utf-8")

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(json_file)],
    )

    assert result.exit_code == 1


def test_unsalvageable_no_candidates_key(tmp_path: Path) -> None:
    """JSON object without candidates key or alias is unsalvageable."""
    candidates_file = _write_json(tmp_path, {"data": [{"action": "foo"}]})

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 1


def test_unsalvageable_candidates_not_list(tmp_path: Path) -> None:
    """JSON object with candidates as a string is unsalvageable."""
    candidates_file = _write_json(tmp_path, {"candidates": "not a list"})

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 1


def test_post_normalization_validation_rejects_missing_fields(tmp_path: Path) -> None:
    """Normalizable root key but still-invalid candidates after normalization exits 1."""
    candidates_file = _write_json(
        tmp_path,
        {
            "tripwire_candidates": [
                {
                    "action": "calling foo()",
                    # missing warning and target_doc_path even after normalization
                }
            ]
        },
    )

    runner = CliRunner()
    result = runner.invoke(
        normalize_tripwire_candidates,
        ["--candidates-file", str(candidates_file)],
    )

    assert result.exit_code == 1
