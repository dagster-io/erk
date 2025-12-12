"""Tests for plan title to filename conversion."""

from erk_shared.naming import generate_filename_from_title

# Alias for backward compatibility with existing tests
plan_title_to_filename = generate_filename_from_title


def test_basic_title() -> None:
    """Convert simple title to kebab-case."""
    assert plan_title_to_filename("Replace gt sync with targeted restack") == (
        "replace-gt-sync-with-targeted-restack-plan.md"
    )


def test_special_characters() -> None:
    """Remove special characters."""
    assert plan_title_to_filename("Fix: Bug #123!") == "fix-bug-123-plan.md"


def test_consecutive_hyphens() -> None:
    """Collapse multiple hyphens."""
    assert plan_title_to_filename("Feature  ---  Implementation") == (
        "feature-implementation-plan.md"
    )


def test_leading_trailing_hyphens() -> None:
    """Strip leading and trailing hyphens."""
    assert plan_title_to_filename("---Fix Bug---") == "fix-bug-plan.md"


def test_emoji() -> None:
    """Remove emojis."""
    assert plan_title_to_filename("🚀 Awesome Feature!") == "awesome-feature-plan.md"


def test_empty_after_cleanup() -> None:
    """Empty string after cleanup returns plan.md."""
    assert plan_title_to_filename("!!!") == "plan.md"
    assert plan_title_to_filename("") == "plan.md"
    assert plan_title_to_filename("   ") == "plan.md"


def test_unicode() -> None:
    """Handle unicode characters."""
    assert plan_title_to_filename("Café Feature") == "cafe-feature-plan.md"


def test_long_title() -> None:
    """Long titles are NOT truncated by kit command."""
    long_title = "Very Long Feature Name With Many Words That Exceeds Thirty Characters"
    result = plan_title_to_filename(long_title)
    # Should NOT be truncated - erk create handles that
    assert len(result) > 30
    assert result.endswith("-plan.md")


# Unicode Normalization Tests


def test_unicode_combining_characters() -> None:
    """Handle combining characters (NFC normalization)."""
    # é as combining characters (e + combining acute accent)
    combining = "cafe\u0301"  # café with combining accent
    assert plan_title_to_filename(combining) == "cafe-plan.md"


def test_unicode_nfc_vs_nfd() -> None:
    """Normalize different Unicode forms to consistent output."""
    # Both NFC and NFD forms should produce same output
    nfc_form = "café"  # Precomposed
    nfd_form = "cafe\u0301"  # Decomposed
    assert plan_title_to_filename(nfc_form) == plan_title_to_filename(nfd_form)


def test_unicode_cjk_characters() -> None:
    """Handle CJK characters with punctuation."""
    assert plan_title_to_filename("测试 Feature！") == "feature-plan.md"
    assert plan_title_to_filename("テスト Plan") == "plan-plan.md"


# Complex Emoji Tests


def test_multi_codepoint_emoji() -> None:
    """Remove multi-codepoint emojis (family emoji)."""
    assert plan_title_to_filename("👨‍👩‍👧‍👦 Family Plan") == "family-plan-plan.md"


def test_emoji_with_skin_tone() -> None:
    """Remove emoji with skin tone modifiers."""
    assert plan_title_to_filename("🤝🏽 Partnership") == "partnership-plan.md"
    assert plan_title_to_filename("👍🏿 Approval") == "approval-plan.md"


def test_mixed_text_and_emoji() -> None:
    """Handle mixed text and emoji sequences."""
    assert plan_title_to_filename("🚀 Launch Feature 🎉") == "launch-feature-plan.md"
    assert plan_title_to_filename("✨ New ✨ Design ✨") == "new-design-plan.md"


# Edge Case Tests


def test_only_special_characters() -> None:
    """Only special characters should return plan.md."""
    assert plan_title_to_filename("!@#$%^&*()") == "plan.md"
    assert plan_title_to_filename("---") == "plan.md"


def test_consecutive_hyphens_collapse() -> None:
    """Multiple consecutive hyphens should collapse to single hyphen."""
    assert plan_title_to_filename("A -- B --- C") == "a-b-c-plan.md"


def test_leading_trailing_whitespace_and_hyphens() -> None:
    """Strip leading/trailing whitespace and hyphens."""
    assert plan_title_to_filename("  --test--  ") == "test-plan.md"


def test_very_long_title_no_truncation() -> None:
    """Very long titles should NOT be truncated."""
    long_title = "A" * 100
    result = plan_title_to_filename(long_title)
    assert result == f"{'a' * 100}-plan.md"


# Prefix Pattern Tests


def test_prefix_plan() -> None:
    """Handle 'Plan:' prefix patterns."""
    assert plan_title_to_filename("Plan: Feature Name") == "plan-feature-name-plan.md"


def test_prefix_implementation_plan() -> None:
    """Handle 'Implementation Plan:' prefix patterns."""
    assert plan_title_to_filename("Implementation Plan: Auth") == "implementation-plan-auth-plan.md"


def test_prefix_feature_plan() -> None:
    """Handle various prefix patterns."""
    assert plan_title_to_filename("Feature Plan: New UI") == "feature-plan-new-ui-plan.md"
