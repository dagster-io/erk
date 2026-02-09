"""Tests for generate_category_tripwires_doc with pattern field."""

from erk.agent_docs.models import CollectedTripwire
from erk.agent_docs.operations import generate_category_tripwires_doc


def test_tripwire_without_pattern_uses_action_only() -> None:
    tripwires = [
        CollectedTripwire(
            action="choosing between exceptions and discriminated unions",
            warning="If callers branch on the error, use discriminated unions.",
            pattern=None,
            doc_path="architecture/discriminated-union-error-handling.md",
            doc_title="Discriminated Union Error Handling",
        )
    ]
    result = generate_category_tripwires_doc("architecture", tripwires)

    assert "**choosing between exceptions and discriminated unions**" in result
    assert "CRITICAL: Before" not in result
    assert "[pattern:" not in result


def test_tripwire_with_pattern_includes_inline_annotation() -> None:
    tripwires = [
        CollectedTripwire(
            action="using bare subprocess.run with check=True",
            warning="Use wrapper functions.",
            pattern="subprocess\\.run\\(",
            doc_path="architecture/subprocess-wrappers.md",
            doc_title="Subprocess Wrappers",
        )
    ]
    result = generate_category_tripwires_doc("architecture", tripwires)

    assert "**using bare subprocess.run with check=True**" in result
    assert "[pattern: `subprocess\\.run\\(`]" in result
    assert "CRITICAL: Before" not in result


def test_header_uses_updated_text() -> None:
    tripwires = [
        CollectedTripwire(
            action="some action",
            warning="some warning",
            pattern=None,
            doc_path="testing/some-doc.md",
            doc_title="Some Doc",
        )
    ]
    result = generate_category_tripwires_doc("testing", tripwires)

    assert "Rules triggered by matching actions in code" in result
    assert "Consult BEFORE taking any matching action" not in result


def test_mixed_pattern_and_no_pattern_tripwires() -> None:
    tripwires = [
        CollectedTripwire(
            action="calling os.chdir()",
            warning="Regenerate context after.",
            pattern="os\\.chdir\\(",
            doc_path="architecture/erk-architecture.md",
            doc_title="Erk Architecture Patterns",
        ),
        CollectedTripwire(
            action="choosing between exceptions and discriminated unions",
            warning="If callers branch on the error, use discriminated unions.",
            pattern=None,
            doc_path="architecture/discriminated-union-error-handling.md",
            doc_title="Discriminated Union Error Handling",
        ),
    ]
    result = generate_category_tripwires_doc("architecture", tripwires)

    assert "[pattern: `os\\.chdir\\(`]" in result
    assert "choosing between exceptions" in result
    # The no-pattern entry should not have [pattern: ...]
    lines = result.split("\n")
    for line in lines:
        if "choosing between exceptions" in line:
            assert "[pattern:" not in line


def test_empty_category_unchanged() -> None:
    result = generate_category_tripwires_doc("testing", [])

    assert "*No tripwires defined for this category.*" in result
