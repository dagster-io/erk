"""Tests for extracting tripwire candidates from learn plan markdown."""

from erk_shared.learn.tripwire_candidates import TripwireCandidate, extract_tripwire_candidates


def test_well_formed_section_with_multiple_docs() -> None:
    """Extract tripwires from a plan with multiple target docs."""
    plan_body = """\
## Summary

Some learn plan summary.

## Tripwire Additions

### For `architecture/foo.md`

```yaml
tripwires:
  - action: "calling foo() without bar"
    warning: "Always pass bar=True to foo()."
```

### For `cli/output-styling.md`

```yaml
tripwires:
  - action: "using print() for CLI output"
    warning: "Use user_output() instead of print()."
  - action: "using click.echo() after user_output()"
    warning: "Mixing output functions causes buffering issues."
```

## Other Section

Some other content.
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert len(candidates) == 3

    assert candidates[0] == TripwireCandidate(
        action="calling foo() without bar",
        warning="Always pass bar=True to foo().",
        target_doc_path="architecture/foo.md",
    )
    assert candidates[1] == TripwireCandidate(
        action="using print() for CLI output",
        warning="Use user_output() instead of print().",
        target_doc_path="cli/output-styling.md",
    )
    assert candidates[2] == TripwireCandidate(
        action="using click.echo() after user_output()",
        warning="Mixing output functions causes buffering issues.",
        target_doc_path="cli/output-styling.md",
    )


def test_no_tripwire_section_returns_empty() -> None:
    """Return empty list when plan has no Tripwire Additions section."""
    plan_body = """\
## Summary

This plan has no tripwires.

## Implementation

Just code changes.
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert candidates == []


def test_malformed_yaml_returns_empty() -> None:
    """Return empty list when YAML in tripwire section is malformed."""
    plan_body = """\
## Tripwire Additions

### For `architecture/foo.md`

```yaml
tripwires:
  - action: "something
    warning: this is invalid yaml [
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert candidates == []


def test_multiple_tripwires_for_same_doc() -> None:
    """Extract multiple tripwires targeting the same document."""
    plan_body = """\
## Tripwire Additions

### For `testing/testing.md`

```yaml
tripwires:
  - action: "writing tests without fakes"
    warning: "Use fake-driven testing pattern."
  - action: "using mock.patch in tests"
    warning: "Use constructor injection with fakes instead."
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert len(candidates) == 2
    assert all(c.target_doc_path == "testing/testing.md" for c in candidates)


def test_empty_tripwires_list_returns_empty() -> None:
    """Return empty list when tripwires key has empty list."""
    plan_body = """\
## Tripwire Additions

### For `architecture/foo.md`

```yaml
tripwires: []
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert candidates == []


def test_missing_action_or_warning_skipped() -> None:
    """Skip entries that lack action or warning fields."""
    plan_body = """\
## Tripwire Additions

### For `architecture/foo.md`

```yaml
tripwires:
  - action: "has action only"
  - warning: "has warning only"
  - action: "complete entry"
    warning: "This one is valid."
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert len(candidates) == 1
    assert candidates[0].action == "complete entry"


def test_non_dict_yaml_returns_empty() -> None:
    """Return empty list when YAML content is not a dict."""
    plan_body = """\
## Tripwire Additions

### For `architecture/foo.md`

```yaml
- just a list
- not a dict
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert candidates == []


def test_tripwire_section_at_end_of_document() -> None:
    """Extract tripwires when section is the last in the document."""
    plan_body = """\
## Summary

Plan summary.

## Tripwire Additions

### For `planning/lifecycle.md`

```yaml
tripwires:
  - action: "creating plans without metadata"
    warning: "Use erk exec plan-save-to-issue."
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert len(candidates) == 1
    assert candidates[0].target_doc_path == "planning/lifecycle.md"


def test_yaml_block_with_yml_fence() -> None:
    """Extract tripwires from ```yml fenced blocks (not just ```yaml)."""
    plan_body = """\
## Tripwire Additions

### For `architecture/foo.md`

```yml
tripwires:
  - action: "using yml fence"
    warning: "Both yml and yaml fences work."
```
"""
    candidates = extract_tripwire_candidates(plan_body)
    assert len(candidates) == 1
    assert candidates[0].action == "using yml fence"
