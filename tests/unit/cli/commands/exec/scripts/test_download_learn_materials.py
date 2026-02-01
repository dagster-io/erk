"""Unit tests for download-learn-materials exec script.

Tests downloading learn materials from a gist and splitting into individual files.
Tests round-trip behavior with upload_learn_materials format.
"""

from pathlib import Path

from erk.cli.commands.exec.scripts.download_learn_materials import (
    _extract_gist_id,
)

# ============================================================================
# Helper Functions Tests (Layer 1: Pure Functions)
# ============================================================================


def test_extract_gist_id_from_full_url() -> None:
    """Test extracting gist ID from full GitHub gist URL."""
    url = "https://gist.github.com/username/abc123def456"
    gist_id = _extract_gist_id(url)
    assert gist_id == "abc123def456"


def test_extract_gist_id_from_short_url() -> None:
    """Test extracting gist ID from short gist URL."""
    url = "https://gist.github.com/abc123def456"
    gist_id = _extract_gist_id(url)
    assert gist_id == "abc123def456"


def test_extract_gist_id_with_trailing_slash() -> None:
    """Test extracting gist ID from URL with trailing slash."""
    url = "https://gist.github.com/username/abc123def456/"
    gist_id = _extract_gist_id(url)
    assert gist_id == "abc123def456"


def test_extract_gist_id_invalid_url() -> None:
    """Test error on invalid URL format."""
    try:
        _extract_gist_id("")
        raise AssertionError("Should have raised ValueError")
    except ValueError as e:
        assert "Invalid gist URL format" in str(e)


# ============================================================================
# Parsing Helper
# ============================================================================


def _parse_combined_gist_content(*, content: str, output_dir: Path) -> list[str]:
    """Parse combined gist format into individual files.

    Replicates the parsing logic from download_learn_materials to test
    round-trip behavior without network calls.

    Returns list of filenames written.
    """
    files_written: list[str] = []
    current_filename: str | None = None
    current_content_lines: list[str] = []
    in_header = False

    for line in content.splitlines():
        if line.strip() == "=" * 60:
            if not in_header and current_filename is not None:
                file_path = output_dir / current_filename
                file_content = "\n".join(current_content_lines).rstrip() + "\n"
                file_path.write_text(file_content, encoding="utf-8")
                files_written.append(current_filename)
                current_content_lines = []
                current_filename = None
            in_header = not in_header
            continue

        if in_header and line.startswith("FILE: "):
            current_filename = line[6:].strip()
            continue

        if not in_header and current_filename is not None:
            current_content_lines.append(line)

    # Handle last file if there was no trailing delimiter
    if current_filename is not None and current_content_lines:
        file_path = output_dir / current_filename
        file_content = "\n".join(current_content_lines).rstrip() + "\n"
        file_path.write_text(file_content, encoding="utf-8")
        files_written.append(current_filename)

    return files_written


# ============================================================================
# Round-Trip Tests (Layer 4: Business Logic)
# ============================================================================


def test_download_parses_upload_format_single_file(tmp_path: Path) -> None:
    """Test downloading and parsing combined gist format with single file."""
    gist_content = """============================================================
FILE: planning-abc123.xml
============================================================
<session>test content</session>
"""

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    files_written = _parse_combined_gist_content(content=gist_content, output_dir=output_dir)

    assert len(files_written) == 1
    assert files_written[0] == "planning-abc123.xml"

    extracted_file = output_dir / "planning-abc123.xml"
    assert extracted_file.exists()
    assert extracted_file.read_text() == "<session>test content</session>\n"


def test_download_parses_upload_format_multiple_files(tmp_path: Path) -> None:
    """Test downloading and parsing combined gist format with multiple files."""
    gist_content = """============================================================
FILE: planning-abc123.xml
============================================================
<session>planning data</session>

============================================================
FILE: impl-def456.xml
============================================================
<session>impl data</session>

============================================================
FILE: pr-comments.json
============================================================
{"comments": []}
"""

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    files_written = _parse_combined_gist_content(content=gist_content, output_dir=output_dir)

    assert len(files_written) == 3
    assert "planning-abc123.xml" in files_written
    assert "impl-def456.xml" in files_written
    assert "pr-comments.json" in files_written

    planning_file = output_dir / "planning-abc123.xml"
    assert planning_file.read_text() == "<session>planning data</session>\n"

    impl_file = output_dir / "impl-def456.xml"
    assert impl_file.read_text() == "<session>impl data</session>\n"

    comments_file = output_dir / "pr-comments.json"
    assert comments_file.read_text() == '{"comments": []}\n'


def test_download_handles_multiline_content(tmp_path: Path) -> None:
    """Test parsing files with multiline content."""
    gist_content = """============================================================
FILE: test.txt
============================================================
Line 1
Line 2
Line 3
"""

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    files_written = _parse_combined_gist_content(content=gist_content, output_dir=output_dir)

    assert len(files_written) == 1
    test_file = output_dir / "test.txt"
    assert test_file.read_text() == "Line 1\nLine 2\nLine 3\n"


def test_download_preserves_empty_lines(tmp_path: Path) -> None:
    """Test that empty lines within file content are preserved."""
    gist_content = """============================================================
FILE: test.txt
============================================================
Line 1

Line 3
"""

    output_dir = tmp_path / "output"
    output_dir.mkdir()

    files_written = _parse_combined_gist_content(content=gist_content, output_dir=output_dir)

    assert len(files_written) == 1
    test_file = output_dir / "test.txt"
    content = test_file.read_text()
    assert content == "Line 1\n\nLine 3\n"
