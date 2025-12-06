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
import tempfile
from pathlib import Path

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


def distill_with_haiku(reduced_content: str) -> str:
    """Stage 2: Semantic distillation via Haiku.

    Invokes Claude Code subprocess to piggyback on its auth.
    Uses --model haiku for cheap/fast distillation.

    Args:
        reduced_content: XML content from Stage 1 mechanical reduction

    Returns:
        Distilled content with noise removed and duplicates collapsed

    Raises:
        RuntimeError: If Claude Code subprocess fails
    """
    # Write reduced content to temp file
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".xml",
        delete=False,
        encoding="utf-8",
    ) as tmp_file:
        tmp_file.write(reduced_content)
        tmp_path = Path(tmp_file.name)

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
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()
