"""Thin bootstrap CLI that delegates to project-local erk."""

import os
import sys
from pathlib import Path

VENV_NAMES = [".venv", "venv"]


def find_local_erk() -> str | None:
    """Walk up from cwd to find venv/bin/erk."""
    # Explicit override via environment variable
    override = os.environ.get("ERK_VENV")
    if override:
        erk_path = Path(override) / "bin" / "erk"
        if erk_path.exists():
            return str(erk_path)

    # Walk up looking for conventional venv names
    cwd = Path.cwd()
    for parent in [cwd, *cwd.parents]:
        for venv_name in VENV_NAMES:
            local_erk = parent / venv_name / "bin" / "erk"
            if local_erk.exists():
                return str(local_erk)
    return None


def main() -> None:
    """Entry point for erk-bootstrap."""
    local_erk = find_local_erk()

    # For completion: delegate or return empty
    if "_ERK_COMPLETE" in os.environ:
        if local_erk:
            os.execv(local_erk, [local_erk, *sys.argv[1:]])
        sys.exit(0)  # No completions outside projects

    # For commands: delegate or error
    if local_erk:
        os.execv(local_erk, [local_erk, *sys.argv[1:]])

    print("erk: No .venv/bin/erk found in current directory or parents", file=sys.stderr)
    print("hint: Run 'uv add erk && uv sync' in your project", file=sys.stderr)
    print("hint: Set ERK_VENV=/path/to/venv for non-standard locations", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
