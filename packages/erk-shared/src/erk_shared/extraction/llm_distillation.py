"""LLM-based session distillation for extraction workflow.

Two-stage preprocessing architecture:
1. Stage 1: Deterministic mechanical reduction (session_preprocessing module)
2. Stage 2: Haiku distillation (this module) - semantic judgment calls

This module provides Stage 2: Haiku handles all semantic judgment calls in a single pass:
- Detect and filter noise (log discovery commands, warmup content)
- Deduplicate semantically similar blocks
- Prune verbose outputs to essential content
- Tailor for downstream doc extraction

Uses Claude Code subprocess for authentication, avoiding direct API dependencies.
"""

import subprocess
from pathlib import Path

from erk_shared.scratch.scratch import write_scratch_file

# Prompt template for Haiku distillation
DISTILLATION_PROMPT = """You are preprocessing a Claude Code session log for doc extraction.

The session has been mechanically cleaned (metadata stripped). Your task:
1. Remove clearly duplicate content (verbatim repeated command docs, system prompts)
2. Filter obvious log discovery noise (pwd, ls ~/.claude, session ID lookups)
3. Preserve technical decisions, insights, and implementation details

IMPORTANT: Be conservative. When in doubt, RETAIN the content.
It's better to keep something potentially useful than to discard it.
Only remove content you are confident is noise or duplication.

ESPECIALLY PRESERVE:
- Error messages, stack traces, and failures (essential for understanding problems)
- Log output and command output (shows what actually happened)
- Warnings and unexpected behavior
- Debugging steps and their results

These are critical for understanding when things went wrong.

Output: Compressed session content preserving the conversation flow.
Keep tool uses with their essential parameters and results.

Session:
"""


def distill_with_haiku(
    reduced_content: str,
    *,
    session_id: str,
    repo_root: Path | None = None,
) -> str:
    """Stage 2: Semantic distillation via Haiku.

    Invokes Claude Code subprocess to piggyback on its auth.
    Uses --model haiku for cheap/fast distillation.

    Args:
        reduced_content: XML content from Stage 1 mechanical reduction
        session_id: Claude session ID for scratch file isolation.
        repo_root: Repo root path. If None, auto-detects via git.

    Returns:
        Distilled content with noise removed and duplicates collapsed

    Raises:
        RuntimeError: If Claude Code subprocess fails
    """
    # Write reduced content to scratch for debugging/auditing
    scratch_path = write_scratch_file(
        reduced_content,
        session_id=session_id,
        suffix=".xml",
        prefix="haiku-input-",
        repo_root=repo_root,
    )

    try:
        # Build the full prompt
        full_prompt = DISTILLATION_PROMPT + reduced_content

        # Run Claude Code with haiku model
        result = subprocess.run(
            [
                "claude",
                "--model",
                "haiku",
                "--print",
                "-p",
                full_prompt,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Claude Code distillation failed: {e.stderr}") from e

    finally:
        # Clean up scratch file
        if scratch_path.exists():
            scratch_path.unlink()
