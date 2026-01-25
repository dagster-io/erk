"""Tests for erk exec promote-to-tripwire command."""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.promote_to_tripwire import promote_to_tripwire
from erk_shared.context.context import ErkContext


def _setup_doc(tmp_path: Path, relative_path: str, content: str) -> None:
    """Create a doc file under docs/learned/ in a temp project root."""
    full_path = tmp_path / "docs" / "learned" / relative_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content, encoding="utf-8")


def test_promote_success(tmp_path: Path) -> None:
    """Successfully promote a tripwire to an existing doc."""
    _setup_doc(
        tmp_path,
        "architecture/test.md",
        """\
---
title: Test Doc
---

# Test Doc
""",
    )

    runner = CliRunner()
    result = runner.invoke(
        promote_to_tripwire,
        [
            "--target-doc",
            "architecture/test.md",
            "--action",
            "doing something risky",
            "--warning",
            "Read test doc first.",
            "--no-sync",
        ],
        obj=ErkContext.for_test(repo_root=tmp_path),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["target_doc_path"] == "architecture/test.md"

    # Verify file was updated
    content = (tmp_path / "docs" / "learned" / "architecture" / "test.md").read_text(
        encoding="utf-8"
    )
    assert "doing something risky" in content
    assert "Read test doc first." in content


def test_promote_file_not_found(tmp_path: Path) -> None:
    """Return error when target doc does not exist."""
    runner = CliRunner()
    result = runner.invoke(
        promote_to_tripwire,
        [
            "--target-doc",
            "architecture/missing.md",
            "--action",
            "some action",
            "--warning",
            "some warning",
            "--no-sync",
        ],
        obj=ErkContext.for_test(repo_root=tmp_path),
    )

    assert result.exit_code == 1


def test_promote_no_frontmatter(tmp_path: Path) -> None:
    """Return error when doc has no frontmatter."""
    _setup_doc(
        tmp_path,
        "architecture/nofm.md",
        "# No Frontmatter\n\nJust content.\n",
    )

    runner = CliRunner()
    result = runner.invoke(
        promote_to_tripwire,
        [
            "--target-doc",
            "architecture/nofm.md",
            "--action",
            "some action",
            "--warning",
            "some warning",
            "--no-sync",
        ],
        obj=ErkContext.for_test(repo_root=tmp_path),
    )

    assert result.exit_code == 1
