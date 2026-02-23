"""Tests for NodeSlugGenerator."""

from erk.core.node_slug_generator import NodeSlugGenerator, _postprocess_node_slug
from tests.fakes.prompt_executor import FakePromptExecutor


def test_successful_batch_generation() -> None:
    """Test successful slug generation from multiple descriptions."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="add-user-model\nwire-cli\nfix-auth",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Wire into CLI", "Fix auth bug"])

    assert result.success is True
    assert result.slugs == ["add-user-model", "wire-cli", "fix-auth"]
    assert result.error_message is None


def test_empty_descriptions() -> None:
    """Empty description list returns empty slugs."""
    executor = FakePromptExecutor(available=True, simulated_prompt_output="")
    generator = NodeSlugGenerator(executor)
    result = generator.generate([])

    assert result.success is True
    assert result.slugs == []


def test_single_description() -> None:
    """Single description generates single slug."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="add-user-model",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model"])

    assert result.success is True
    assert result.slugs == ["add-user-model"]


def test_falls_back_on_executor_failure() -> None:
    """Executor failure triggers hash-based fallback."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_error="LLM unavailable",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Wire into CLI"])

    assert result.success is True
    assert len(result.slugs) == 2
    # Fallback uses hash-based slugify_node_description
    assert result.slugs[0].startswith("node-")
    assert result.slugs[1].startswith("node-")


def test_falls_back_on_wrong_count() -> None:
    """LLM returning wrong number of slugs triggers fallback."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="only-one-slug",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Wire into CLI"])

    assert result.success is True
    assert len(result.slugs) == 2
    # Fallback hash-based slugs
    assert result.slugs[0].startswith("node-")
    assert result.slugs[1].startswith("node-")


def test_duplicate_slugs_from_llm_preserved() -> None:
    """Duplicate slugs from LLM are preserved as-is (no deduplication)."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="add-model\nadd-model",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Add data model"])

    assert result.success is True
    assert result.slugs == ["add-model", "add-model"]


def test_invalid_slug_falls_back_per_item() -> None:
    """Individual invalid slugs fall back while valid ones pass through."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="add-user-model\nX\nfix-auth",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Wire into CLI", "Fix auth bug"])

    assert result.success is True
    assert result.slugs[0] == "add-user-model"
    # "X" is invalid (too short), falls back to hash-based
    assert result.slugs[1].startswith("node-")
    assert result.slugs[2] == "fix-auth"


def test_strips_quotes_from_llm_output() -> None:
    """Surrounding quotes are stripped from LLM slugs."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="\"add-user-model\"\n`wire-cli`\n'fix-auth'",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Wire into CLI", "Fix auth bug"])

    assert result.success is True
    assert result.slugs == ["add-user-model", "wire-cli", "fix-auth"]


def test_strips_numbering_from_llm_output() -> None:
    """Numbering prefixes are stripped from LLM slugs."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="1. add-user-model\n2) wire-cli",
    )
    generator = NodeSlugGenerator(executor)
    result = generator.generate(["Add user model", "Wire into CLI"])

    assert result.success is True
    assert result.slugs == ["add-user-model", "wire-cli"]


def test_uses_haiku_model() -> None:
    """Generator uses the haiku model for LLM calls."""
    executor = FakePromptExecutor(
        available=True,
        simulated_prompt_output="add-user-model",
    )
    generator = NodeSlugGenerator(executor)
    generator.generate(["Add user model"])

    assert len(executor.prompt_calls) == 1
    _prompt, system_prompt, dangerous = executor.prompt_calls[0]
    assert system_prompt is not None
    assert dangerous is False


# ---------------------------------------------------------------------------
# _postprocess_node_slug tests
# ---------------------------------------------------------------------------


def test_postprocess_valid_slug() -> None:
    """Valid slug passes through unchanged."""
    assert _postprocess_node_slug("add-user-model") == "add-user-model"


def test_postprocess_strips_quotes() -> None:
    """Quotes and backticks are stripped."""
    assert _postprocess_node_slug('"add-user"') == "add-user"
    assert _postprocess_node_slug("`add-user`") == "add-user"
    assert _postprocess_node_slug("'add-user'") == "add-user"


def test_postprocess_strips_numbering() -> None:
    """Numbered list prefixes are removed."""
    assert _postprocess_node_slug("1. add-user") == "add-user"
    assert _postprocess_node_slug("2) wire-cli") == "wire-cli"


def test_postprocess_lowercases() -> None:
    """Output is lowercased."""
    assert _postprocess_node_slug("Add-User") == "add-user"


def test_postprocess_replaces_special_chars() -> None:
    """Non-alphanumeric characters become hyphens."""
    assert _postprocess_node_slug("add user model") == "add-user-model"


def test_postprocess_returns_none_for_invalid() -> None:
    """Returns None for output that can't be salvaged."""
    assert _postprocess_node_slug("") is None
    assert _postprocess_node_slug("X") is None
