"""Download preprocessed session files from a GitHub gist.

This exec script handles downloading session data for remote learn workflow:
1. Extracts gist ID from URL
2. Lists files in the gist via gh gist view
3. Downloads each file to the output directory

Usage:
    erk exec download-gist-sessions --gist-url https://gist.github.com/... --output-dir /path/to/dir

Output:
    JSON object with download results:
    {
        "success": true,
        "files": ["planning-abc.xml", "impl-def.xml", ...],
        "count": 3,
        "output_dir": "/path/to/dir"
    }

Exit Codes:
    0: Success
    1: Error (invalid URL, gist not found, download failure)
"""

import json
import re
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

import click


@dataclass(frozen=True)
class DownloadSuccess:
    """Success result for download-gist-sessions command."""

    success: bool
    files: list[str]
    count: int
    output_dir: str


@dataclass(frozen=True)
class DownloadError:
    """Error result when download fails."""

    success: bool
    error: str


def _extract_gist_id(gist_url: str) -> str | None:
    """Extract gist ID from URL.

    Handles various URL formats:
    - https://gist.github.com/username/abc123
    - https://gist.github.com/abc123
    - gist.github.com/abc123

    Args:
        gist_url: URL of the gist

    Returns:
        Gist ID or None if invalid
    """
    # Remove trailing slash
    url = gist_url.rstrip("/")

    # Match gist ID (alphanumeric, typically 32 chars)
    match = re.search(r"gist\.github\.com/(?:[^/]+/)?([a-f0-9]+)$", url)
    if match:
        return match.group(1)

    # Also handle raw gist ID passed directly
    if re.match(r"^[a-f0-9]+$", url):
        return url

    return None


def _list_gist_files(gist_id: str) -> list[str] | None:
    """List files in a gist.

    Args:
        gist_id: The gist ID

    Returns:
        List of filenames or None on error
    """
    result = subprocess.run(
        ["gh", "gist", "view", gist_id, "--files"],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return None

    # Output is one filename per line
    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    return files


def _download_gist_file(gist_id: str, filename: str, output_dir: Path) -> bool:
    """Download a single file from a gist.

    Args:
        gist_id: The gist ID
        filename: Name of the file to download
        output_dir: Directory to save the file

    Returns:
        True if successful, False otherwise
    """
    result = subprocess.run(
        ["gh", "gist", "view", gist_id, "-f", filename],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        return False

    output_path = output_dir / filename
    output_path.write_text(result.stdout, encoding="utf-8")
    return True


@click.command(name="download-gist-sessions")
@click.option(
    "--gist-url",
    "gist_url",
    type=str,
    required=True,
    help="URL of the gist to download",
)
@click.option(
    "--output-dir",
    "output_dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Directory to save downloaded files",
)
def download_gist_sessions(
    *,
    gist_url: str,
    output_dir: Path,
) -> None:
    """Download preprocessed session files from a gist.

    Downloads all files from the specified gist to the output directory.
    Used by /erk:learn when running remotely with session data from a gist.

    Outputs JSON with file list and count.
    """
    # Extract gist ID
    gist_id = _extract_gist_id(gist_url)
    if gist_id is None:
        error = DownloadError(
            success=False,
            error=f"Invalid gist URL: {gist_url}",
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    # List files in gist
    files = _list_gist_files(gist_id)
    if files is None:
        error = DownloadError(
            success=False,
            error=f"Failed to list files in gist {gist_id}",
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    if not files:
        error = DownloadError(
            success=False,
            error=f"Gist {gist_id} contains no files",
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Download each file
    downloaded: list[str] = []
    for filename in files:
        if _download_gist_file(gist_id, filename, output_dir):
            downloaded.append(filename)

    if not downloaded:
        error = DownloadError(
            success=False,
            error="Failed to download any files from gist",
        )
        click.echo(json.dumps(asdict(error), indent=2))
        raise SystemExit(1)

    success = DownloadSuccess(
        success=True,
        files=downloaded,
        count=len(downloaded),
        output_dir=str(output_dir),
    )
    click.echo(json.dumps(asdict(success), indent=2))
