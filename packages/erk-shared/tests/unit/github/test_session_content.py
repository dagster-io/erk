"""Tests for session prompts and exchanges metadata block functions."""

import re

from erk_shared.github.metadata.session import (
    extract_prompts_from_session_prompts_block,
    render_session_exchanges_block,
    render_session_prompts_block,
)

# =============================================================================
# Tests for render_session_prompts_block
# =============================================================================


def test_render_session_prompts_block_basic() -> None:
    """Basic rendering includes metadata block markers and numbered prompts."""
    prompts = ["Add dark mode", "Run tests"]
    result = render_session_prompts_block(prompts, max_prompt_display_length=500)

    assert "<!-- erk:metadata-block:planning-session-prompts -->" in result
    assert "<!-- /erk:metadata-block:planning-session-prompts -->" in result
    assert "<details>" in result
    assert "</details>" in result
    assert "**Prompt 1:**" in result
    assert "**Prompt 2:**" in result
    assert "Add dark mode" in result
    assert "Run tests" in result


def test_render_session_prompts_block_includes_warning() -> None:
    """The machine-generated warning comment is included."""
    result = render_session_prompts_block(["Test prompt"], max_prompt_display_length=500)

    assert "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->" in result


def test_render_session_prompts_block_includes_summary_with_count() -> None:
    """The summary tag includes prompt count."""
    result = render_session_prompts_block(["Test prompt"], max_prompt_display_length=500)
    assert "<summary><code>planning-session-prompts</code> (1 prompt)</summary>" in result

    result2 = render_session_prompts_block(["A", "B"], max_prompt_display_length=500)
    assert "<summary><code>planning-session-prompts</code> (2 prompts)</summary>" in result2


def test_render_session_prompts_block_empty_list() -> None:
    """Empty prompt list renders with count 0."""
    result = render_session_prompts_block([], max_prompt_display_length=500)

    assert "(0 prompts)" in result
    # No prompt blocks for empty list
    assert "**Prompt" not in result


def test_render_session_prompts_block_preserves_special_characters() -> None:
    """Prompts with special characters are preserved."""
    prompts = ['Add "dark mode" feature', "Fix bug: can't save"]
    result = render_session_prompts_block(prompts, max_prompt_display_length=500)

    assert 'Add "dark mode" feature' in result
    assert "can't save" in result


def test_render_session_prompts_block_truncates_long_prompts() -> None:
    """Long prompts are truncated with ellipsis."""
    long_prompt = "This is a very long prompt that should be truncated"
    result = render_session_prompts_block([long_prompt], max_prompt_display_length=25)

    assert "This is a very long pr..." in result
    assert long_prompt not in result  # Full text should not appear


# =============================================================================
# Tests for extract_prompts_from_session_prompts_block
# =============================================================================


def test_extract_prompts_from_session_prompts_block_basic() -> None:
    """Extracts prompts from a valid planning-session-prompts block body."""
    block_body = """<details>
<summary><code>planning-session-prompts</code> (2 prompts)</summary>

**Prompt 1:**

```
First prompt
```

**Prompt 2:**

```
Second prompt
```

</details>"""

    result = extract_prompts_from_session_prompts_block(block_body)

    assert result is not None
    assert result == ["First prompt", "Second prompt"]


def test_extract_prompts_from_session_prompts_block_no_prompts_returns_none() -> None:
    """Returns None when no prompt blocks are found."""
    block_body = """<details>
<summary><code>planning-session-prompts</code> (0 prompts)</summary>

No prompt blocks here

</details>"""

    result = extract_prompts_from_session_prompts_block(block_body)

    assert result is None


def test_extract_prompts_from_session_prompts_block_multiline() -> None:
    """Extracts prompts with multiline content."""
    block_body = """<details>
<summary><code>planning-session-prompts</code> (1 prompt)</summary>

**Prompt 1:**

```
First line
Second line
Third line
```

</details>"""

    result = extract_prompts_from_session_prompts_block(block_body)

    assert result is not None
    assert len(result) == 1
    assert "First line" in result[0]
    assert "Third line" in result[0]


def test_session_prompts_roundtrip() -> None:
    """Prompts survive render -> extract roundtrip."""
    original_prompts = ["Add a feature", "Run tests", "Fix the bug"]

    # Render the prompts
    rendered = render_session_prompts_block(original_prompts, max_prompt_display_length=500)

    # Extract from the rendered block body (strip the HTML comment wrappers)
    # Find the body between the markers
    start_marker = "<!-- erk:metadata-block:planning-session-prompts -->"
    end_marker = "<!-- /erk:metadata-block:planning-session-prompts -->"
    pattern = rf"{re.escape(start_marker)}(.+?){re.escape(end_marker)}"
    match = re.search(pattern, rendered, re.DOTALL)
    assert match is not None
    block_body = match.group(1).strip()

    # Extract prompts back
    extracted = extract_prompts_from_session_prompts_block(block_body)

    assert extracted is not None
    assert extracted == original_prompts


# =============================================================================
# Tests for render_session_exchanges_block
# =============================================================================


def test_render_session_exchanges_block_basic() -> None:
    """Basic rendering includes metadata block markers and numbered exchanges."""
    exchanges = [(None, "First user prompt"), ("Assistant response", "Second prompt")]
    result = render_session_exchanges_block(exchanges, max_text_display_length=500)

    assert "<!-- erk:metadata-block:planning-session-prompts -->" in result
    assert "<!-- /erk:metadata-block:planning-session-prompts -->" in result
    assert "<details>" in result
    assert "</details>" in result
    assert "**Exchange 1:**" in result
    assert "**Exchange 2:**" in result
    assert "First user prompt" in result
    assert "Assistant response" in result
    assert "Second prompt" in result


def test_render_session_exchanges_block_includes_warning() -> None:
    """The machine-generated warning comment is included."""
    result = render_session_exchanges_block([(None, "Test")], max_text_display_length=500)

    assert "<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->" in result


def test_render_session_exchanges_block_includes_summary_with_count() -> None:
    """The summary tag includes exchange count."""
    result = render_session_exchanges_block([(None, "Test")], max_text_display_length=500)
    assert "(1 exchange)" in result

    result2 = render_session_exchanges_block(
        [(None, "A"), ("Response", "B")], max_text_display_length=500
    )
    assert "(2 exchanges)" in result2


def test_render_session_exchanges_block_empty_list() -> None:
    """Empty exchange list renders with count 0."""
    result = render_session_exchanges_block([], max_text_display_length=500)

    assert "(0 exchanges)" in result
    # No exchange blocks for empty list
    assert "**Exchange" not in result


def test_render_session_exchanges_block_no_preceding_assistant() -> None:
    """Exchange without preceding assistant only shows user prompt."""
    exchanges = [(None, "User prompt without context")]
    result = render_session_exchanges_block(exchanges, max_text_display_length=500)

    assert "*User:*" in result
    assert "User prompt without context" in result
    # Should NOT include Assistant section for first exchange
    assert result.count("*Assistant:*") == 0


def test_render_session_exchanges_block_with_assistant() -> None:
    """Exchange with preceding assistant shows both assistant and user."""
    exchanges = [("Assistant asked a question", "User replied yes")]
    result = render_session_exchanges_block(exchanges, max_text_display_length=500)

    assert "*Assistant:*" in result
    assert "Assistant asked a question" in result
    assert "*User:*" in result
    assert "User replied yes" in result


def test_render_session_exchanges_block_truncates_long_text() -> None:
    """Long text is truncated with ellipsis."""
    long_text = "This is a very long text that should be truncated"
    exchanges = [(long_text, long_text)]
    result = render_session_exchanges_block(exchanges, max_text_display_length=25)

    assert "This is a very long te..." in result
    assert long_text not in result  # Full text should not appear


def test_render_session_exchanges_block_preserves_special_characters() -> None:
    """Exchanges with special characters are preserved."""
    exchanges = [('Should I add "dark mode"?', "yes, that's what I want")]
    result = render_session_exchanges_block(exchanges, max_text_display_length=500)

    assert '"dark mode"' in result
    assert "that's what" in result


def test_render_session_exchanges_block_multiple_exchanges() -> None:
    """Multiple exchanges are numbered sequentially."""
    exchanges = [
        (None, "First prompt"),
        ("Response 1", "Second prompt"),
        ("Response 2", "Third prompt"),
    ]
    result = render_session_exchanges_block(exchanges, max_text_display_length=500)

    assert "**Exchange 1:**" in result
    assert "**Exchange 2:**" in result
    assert "**Exchange 3:**" in result
    # First exchange has no assistant
    lines = result.split("\n")
    exchange1_start = next(i for i, line in enumerate(lines) if "**Exchange 1:**" in line)
    exchange2_start = next(i for i, line in enumerate(lines) if "**Exchange 2:**" in line)
    # Between Exchange 1 and Exchange 2, there should be no *Assistant:* (only *User:*)
    between = lines[exchange1_start:exchange2_start]
    assert "*User:*" in "\n".join(between)
    # Exchange 2 should have *Assistant:*
    after_exchange2 = lines[exchange2_start:]
    assert "*Assistant:*" in "\n".join(after_exchange2)
