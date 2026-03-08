"""Shared manifest reader for session branches."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from erk_shared.gateway.git.abc import Git


def read_session_manifest(
    git: Git,
    *,
    repo_root: Path,
    session_branch: str,
) -> dict | None:
    """Read and parse .erk/sessions/manifest.json from a git ref.

    This is the leaf function: no branch existence check, no fetch.
    Callers are responsible for ensuring the ref exists and is fetched.

    Args:
        git: Git gateway instance.
        repo_root: Repository root path.
        session_branch: Branch name (used as origin/{session_branch} ref).

    Returns:
        Parsed manifest dict if found and valid, None otherwise.
    """
    raw = git.commit.read_file_from_ref(
        repo_root,
        ref=f"origin/{session_branch}",
        file_path=".erk/sessions/manifest.json",
    )
    if raw is None:
        return None
    content = raw.decode("utf-8").strip()
    if not content:
        return None
    return json.loads(content)
