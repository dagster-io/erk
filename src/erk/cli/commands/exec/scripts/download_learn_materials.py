"""Download learn materials from a GitHub gist and split into individual files.

This exec command downloads a gist containing combined learn materials
and splits it back into individual files using the delimiter format
from upload_learn_materials.

The gist URL should be in one of these formats:
- https://gist.github.com/user/abc123
- https://gist.github.com/abc123

The script will fetch the raw content from the gist and parse it back
into individual files.

Usage:
    erk exec download-learn-materials --gist-url <url> --output-dir <dir>

Output:
    Structured JSON output with success status and file information

Exit Codes:
    0: Success (gist downloaded and split)
    1: Error (download failed, parsing failed)

Examples:
    $ erk exec download-learn-materials --gist-url https://gist.github.com/user/abc \\
        --output-dir .erk/scratch/learn
    {
      "success": true,
      "file_count": 3,
      "files": ["planning-session.xml", "impl-session.xml", "pr-review-comments.json"]
    }

    $ # On failure:
    {
      "success": false,
      "error": "Failed to download gist: not found"
    }
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

import click


def _extract_gist_id(gist_url: str) -> str:
    """Extract gist ID from a GitHub gist URL.

    Args:
        gist_url: Full gist URL (e.g., https://gist.github.com/user/abc123)

    Returns:
        The gist ID (the last path component)

    Raises:
        ValueError: If the URL format is invalid
    """
    # Remove trailing slash if present
    url = gist_url.rstrip("/")

    # Extract the last path component (gist ID)
    parts = url.split("/")
    gist_id = parts[-1]

    if not gist_id:
        raise ValueError(f"Invalid gist URL format: {gist_url}")

    return gist_id


def _download_gist_raw_content(gist_id: str) -> str:
    """Download raw content from a gist.

    GitHub gists can be accessed via their raw URL:
    https://gist.githubusercontent.com/{user}/{gist_id}/raw

    However, for secret gists, we need to use the main gist URL and
    extract the raw file URL from the HTML page.

    Args:
        gist_id: The gist ID

    Returns:
        The raw content of the gist file

    Raises:
        urllib.error.HTTPError: If the download fails
    """
    # Try candidate URLs in order. The first uses gist.githubusercontent.com/raw/
    # which works for public gists without knowing the owner. The fallback uses
    # the main gist URL with /raw suffix.
    candidate_urls = [
        f"https://gist.githubusercontent.com/raw/{gist_id}",
        f"https://gist.github.com/{gist_id}/raw",
    ]

    last_error: urllib.error.HTTPError | None = None
    for url in candidate_urls:
        try:
            with urllib.request.urlopen(url) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            last_error = e

    # All URLs failed — raise the last error
    # last_error is guaranteed non-None since candidate_urls is non-empty
    assert last_error is not None
    raise last_error


@click.command(name="download-learn-materials")
@click.option(
    "--gist-url",
    required=True,
    type=str,
    help="URL of the gist containing learn materials",
)
@click.option(
    "--output-dir",
    required=True,
    type=click.Path(path_type=Path),
    help="Directory to write the extracted files",
)
def download_learn_materials(
    *,
    gist_url: str,
    output_dir: Path,
) -> None:
    """Download learn materials from a gist and split into files.

    Downloads the gist content and parses the combined format back into
    individual files using the delimiter pattern from upload_learn_materials.

    Returns JSON with success status and file list.
    """
    # Validate and extract gist ID from URL (LBYL: check before calling)
    url_stripped = gist_url.rstrip("/")
    gist_id = url_stripped.split("/")[-1]
    if not gist_id:
        error_output = {
            "success": False,
            "error": f"Invalid gist URL format: {gist_url}",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    # Download the gist content
    try:
        content = _download_gist_raw_content(gist_id)
    except urllib.error.HTTPError as e:
        error_output = {
            "success": False,
            "error": f"Failed to download gist: {e}",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1) from e

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Parse the combined content back into individual files
    # Upload format per file:
    #   ============================================================
    #   FILE: filename.txt
    #   ============================================================
    #   <content lines>
    #   <blank line separator>
    #
    # The delimiter pair brackets the FILE: header. Content follows
    # AFTER the closing delimiter until the next opening delimiter.

    files_written: list[str] = []
    current_filename: str | None = None
    current_content_lines: list[str] = []
    in_header = False

    for line in content.splitlines():
        # Check for delimiter line (60 equals signs)
        if line.strip() == "=" * 60:
            if not in_header and current_filename is not None:
                # Entering a new header — save the previous file's content
                file_path = output_dir / current_filename
                file_content = "\n".join(current_content_lines).rstrip() + "\n"
                file_path.write_text(file_content, encoding="utf-8")
                files_written.append(current_filename)
                current_content_lines = []
                current_filename = None
            in_header = not in_header
            continue

        # Check for FILE: header (inside delimiter pair)
        if in_header and line.startswith("FILE: "):
            current_filename = line[6:].strip()
            continue

        # Accumulate content lines (outside delimiter pair, after a FILE: was set)
        if not in_header and current_filename is not None:
            current_content_lines.append(line)

    # Handle last file (no trailing delimiter pair after final content)
    if current_filename is not None and current_content_lines:
        file_path = output_dir / current_filename
        file_content = "\n".join(current_content_lines).rstrip() + "\n"
        file_path.write_text(file_content, encoding="utf-8")
        files_written.append(current_filename)

    if not files_written:
        error_output = {
            "success": False,
            "error": "No files found in gist content",
        }
        click.echo(json.dumps(error_output))
        raise SystemExit(1)

    result = {
        "success": True,
        "file_count": len(files_written),
        "files": files_written,
    }
    click.echo(json.dumps(result))
