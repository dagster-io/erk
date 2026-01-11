"""Session prompts and exchanges metadata block operations.

These support storing session prompts in GitHub issue comments for erk plan issues.
"""

import re


def render_session_prompts_block(
    prompts: list[str],
    *,
    max_prompt_display_length: int,
) -> str:
    """Render session prompts as a metadata block with numbered markdown blocks.

    Creates a collapsible metadata block containing user prompts from
    the planning session, formatted as numbered code blocks for readability.

    Args:
        prompts: List of user prompt strings to include.
        max_prompt_display_length: Maximum characters to show per prompt.
            Prompts longer than this are truncated with "..." suffix.

    Returns:
        Rendered metadata block markdown string.

    Example output:
        <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
        <!-- erk:metadata-block:planning-session-prompts -->
        <details>
        <summary><code>planning-session-prompts</code> (3 prompts)</summary>

        **Prompt 1:**

        ```
        Add a dark mode toggle
        ```

        **Prompt 2:**

        ```
        Make sure tests pass
        ```

        </details>
        <!-- /erk:metadata-block:planning-session-prompts -->
    """
    # Build the numbered prompt blocks
    prompt_blocks: list[str] = []
    for i, prompt in enumerate(prompts, start=1):
        # Truncate long prompts for display
        display_text = prompt
        if len(prompt) > max_prompt_display_length:
            display_text = prompt[: max_prompt_display_length - 3] + "..."

        block = f"""**Prompt {i}:**

```
{display_text}
```"""
        prompt_blocks.append(block)

    # Join blocks with blank lines
    content = "\n\n".join(prompt_blocks)

    # Summary shows count
    count_suffix = f" ({len(prompts)} prompt{'s' if len(prompts) != 1 else ''})"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:planning-session-prompts -->
<details>
<summary><code>planning-session-prompts</code>{count_suffix}</summary>

{content}

</details>
<!-- /erk:metadata-block:planning-session-prompts -->"""


def render_session_exchanges_block(
    exchanges: list[tuple[str | None, str]],
    *,
    max_text_display_length: int,
) -> str:
    """Render session exchanges as a metadata block with numbered markdown blocks.

    Creates a collapsible metadata block containing user prompts paired with
    the assistant messages that preceded them, providing context for responses
    like "yes" or "proceed".

    Args:
        exchanges: List of (preceding_assistant, user_prompt) tuples.
            preceding_assistant can be None for the first exchange in a session.
        max_text_display_length: Maximum characters to show per text field.
            Text longer than this is truncated with "..." suffix.

    Returns:
        Rendered metadata block markdown string.

    Example output:
        <!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
        <!-- erk:metadata-block:planning-session-prompts -->
        <details>
        <summary><code>planning-session-prompts</code> (2 exchanges)</summary>

        **Exchange 1:**

        *User:*
        ```
        what happened [PR URL]. why did this end up with .worker-impl file?
        ```

        **Exchange 2:**

        *Assistant:*
        ```
        I found the issue. The cleanup step is missing. Would you like me to fix?
        ```

        *User:*
        ```
        yes
        ```

        </details>
        <!-- /erk:metadata-block:planning-session-prompts -->
    """
    # Build the numbered exchange blocks
    exchange_blocks: list[str] = []
    for i, (assistant_text, user_text) in enumerate(exchanges, start=1):
        # Truncate long text for display
        if assistant_text is not None and len(assistant_text) > max_text_display_length:
            assistant_text = assistant_text[: max_text_display_length - 3] + "..."
        if len(user_text) > max_text_display_length:
            user_text = user_text[: max_text_display_length - 3] + "..."

        # Build the exchange block
        lines = [f"**Exchange {i}:**", ""]

        # Include assistant message if present
        if assistant_text is not None:
            lines.extend(
                [
                    "*Assistant:*",
                    "```",
                    assistant_text,
                    "```",
                    "",
                ]
            )

        # Always include user message
        lines.extend(
            [
                "*User:*",
                "```",
                user_text,
                "```",
            ]
        )

        exchange_blocks.append("\n".join(lines))

    # Join blocks with blank lines
    content = "\n\n".join(exchange_blocks)

    # Summary shows count - use "exchanges" as unit
    count_suffix = f" ({len(exchanges)} exchange{'s' if len(exchanges) != 1 else ''})"

    return f"""<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:planning-session-prompts -->
<details>
<summary><code>planning-session-prompts</code>{count_suffix}</summary>

{content}

</details>
<!-- /erk:metadata-block:planning-session-prompts -->"""


def extract_prompts_from_session_prompts_block(block_body: str) -> list[str] | None:
    """Extract prompts list from a planning-session-prompts metadata block.

    Parses the <details> structure to find numbered prompt blocks and extract
    the prompt text from each code fence.

    Args:
        block_body: Raw body content from a planning-session-prompts metadata block.

    Returns:
        List of prompt strings, or None if parsing fails.
    """
    # The planning-session-prompts block has format:
    # <details>
    # <summary><code>planning-session-prompts</code> (N prompts)</summary>
    #
    # **Prompt 1:**
    #
    # ```
    # First prompt text
    # ```
    #
    # **Prompt 2:**
    #
    # ```
    # Second prompt text
    # ```
    #
    # </details>

    # Find all prompt blocks: **Prompt N:** followed by a code fence
    # Pattern: **Prompt \d+:** followed by ``` ... ```
    pattern = r"\*\*Prompt \d+:\*\*\s*\n\n```\n(.*?)\n```"
    matches = re.findall(pattern, block_body, re.DOTALL)

    if not matches:
        return None

    return [match.strip() for match in matches]
