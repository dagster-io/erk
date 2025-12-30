#!/usr/bin/env python3
"""SessionStart hook to check virtual environment activation.

Uses signal file pattern to allow user bypass after acknowledgment.
Exit codes:
  0 - Allow session to start
  2 - Block session start
"""

import os
import sys
from pathlib import Path


def get_signal_file_path() -> Path:
    """Get path to the venv-bypass signal file."""
    session_id = os.environ.get("CLAUDE_SESSION_ID", "unknown")
    return Path(".erk/scratch/sessions") / session_id / "venv-bypass.signal"


def is_venv_activated() -> bool:
    """Check if the correct venv is activated."""
    venv_dir = Path(".venv")
    if not venv_dir.is_dir():
        return True  # No venv expected, allow

    expected_venv = str(venv_dir.resolve())
    actual_venv = os.environ.get("VIRTUAL_ENV", "")
    return actual_venv == expected_venv


def main() -> None:
    # Check if venv is properly activated
    if is_venv_activated():
        sys.exit(0)

    signal_file = get_signal_file_path()

    # Check for bypass signal file
    if signal_file.exists():
        # Allow but show how to re-enable check
        print("⚠️ Venv not activated (bypassed)")
        print(f"   Re-enable check:  ! rm {signal_file}")
        sys.exit(0)

    # Block session start
    print("❌ Virtual environment .venv exists but is not activated.")
    print("")
    print("Options:")
    print("  1. Activate:  ! source .venv/bin/activate")
    print(f"  2. Bypass:    ! mkdir -p {signal_file.parent} && touch {signal_file}")
    sys.exit(2)


if __name__ == "__main__":
    main()
