"""Thin bootstrap CLI that delegates to project-local erk."""

import os
import sys
from dataclasses import dataclass
from pathlib import Path

VENV_NAMES = [".venv", "venv"]


@dataclass(frozen=True)
class ErkNotFound:
    """Result when erk binary not found."""

    venv_found: bool  # True if a venv dir was found (but no erk inside)


def find_local_erk() -> str | ErkNotFound:
    """Walk up from cwd to find venv/bin/erk.

    Returns:
        Path to erk binary if found, or ErkNotFound with context.
    """
    # Explicit override via environment variable
    override = os.environ.get("ERK_VENV")
    if override:
        erk_path = Path(override) / "bin" / "erk"
        if erk_path.exists():
            return str(erk_path)

    # Walk up looking for conventional venv names
    cwd = Path.cwd()
    venv_found = False
    for parent in [cwd, *cwd.parents]:
        for venv_name in VENV_NAMES:
            venv_dir = parent / venv_name
            if venv_dir.is_dir():
                venv_found = True
                local_erk = venv_dir / "bin" / "erk"
                if local_erk.exists():
                    return str(local_erk)

    return ErkNotFound(venv_found=venv_found)


def main() -> None:
    """Entry point for erk-bootstrap."""
    result = find_local_erk()

    # Found erk - delegate to it
    if isinstance(result, str):
        local_erk = result
        os.execv(local_erk, [local_erk, *sys.argv[1:]])

    # Not found - show appropriate error
    if "_ERK_COMPLETE" in os.environ:
        sys.exit(0)  # No completions outside projects

    if result.venv_found:
        # Case 2: In a project but erk not installed
        print("erk: not installed in this project", file=sys.stderr)
        print("hint: Run 'uv add erk && uv sync' to install", file=sys.stderr)
        print("hint: Set ERK_VENV=/path/to/venv for non-standard locations", file=sys.stderr)
    else:
        # Case 1: Not in any project
        # Silence message in home directory (expected during shell init)
        if Path.cwd() != Path.home():
            print("erk: no project found", file=sys.stderr)

    sys.exit(1)


if __name__ == "__main__":
    main()
