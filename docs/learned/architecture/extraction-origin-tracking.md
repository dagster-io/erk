---
title: Extraction Origin Tracking
read_when:
  - "understanding how extraction PRs are identified"
  - "modifying erk pr land behavior"
  - "working with erk-skip-extraction label"
---

# Extraction Origin Tracking

PRs that originate from extraction plans need to be identified during `erk pr land` to prevent infinite extraction loops.

## The Problem

When a PR is landed via `erk pr land`, the command normally queues the worktree for "pending extraction" - a state that enables later session analysis to extract documentation improvements.

However, PRs that _originate from_ extraction plans should not trigger another extraction cycle. Otherwise:

1. Extraction plan creates documentation PR
2. PR lands → queued for extraction
3. Extraction runs → finds documentation changes → creates new extraction plan
4. Repeat forever

## Design Decision: Labels over Body Markers

**Previous approach** (deprecated): A marker string (`**Extraction Origin:** true`) was embedded in PR bodies.

**Current approach**: The `erk-skip-extraction` GitHub label is added to PRs.

### Rationale

1. **Visibility**: Labels are visible in GitHub UI, making it easy to identify extraction PRs at a glance
2. **Simplicity**: Label checks are simpler than parsing PR body content
3. **Separation**: PR body content remains focused on the actual PR description
4. **Flexibility**: Labels can be manually added/removed for edge cases

## Implementation Flow

### 1. PR Creation (`submit.py`, `finalize.py`)

When creating a PR from an extraction plan:

```python
# Check if source is extraction plan
if is_extraction_plan(plan_metadata) or is_issue_extraction_plan(issue_metadata):
    # Add label to mark as extraction-originated
    github.add_label_to_pr(repo_root, pr_number, ERK_SKIP_EXTRACTION_LABEL)
```

The label is applied by:

- `erk plan submit` - Checks issue's `plan_type` field in plan-header metadata
- `gt finalize` - Checks `.impl/plan.md` for `plan_type: extraction`

### 2. PR Landing (`land_cmd.py`)

When landing a PR:

```python
# Check if PR should skip extraction
if github.has_pr_label(repo_root, pr_number, ERK_SKIP_EXTRACTION_LABEL):
    # Skip pending-extraction marker
    # Delete worktree immediately
    click.echo("Skipping extraction (extraction-originated PR)")
else:
    # Normal flow: mark for pending extraction
    mark_pending_extraction(worktree)
```

## Adding the GitHub Methods

When this feature was implemented, it required adding new methods to the GitHub integration layer. This follows the standard four-layer pattern:

### ABC (`packages/erk-shared/src/erk_shared/github/abc.py`)

```python
@abstractmethod
def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
    """Add a label to a pull request.

    Args:
        repo_root: Path to repository root
        pr_number: Pull request number
        label: Label name to add
    """
    ...

@abstractmethod
def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
    """Check if a pull request has a specific label.

    Args:
        repo_root: Path to repository root
        pr_number: Pull request number
        label: Label name to check

    Returns:
        True if the PR has the label, False otherwise
    """
    ...
```

### Real (`packages/erk-shared/src/erk_shared/github/real.py`)

```python
def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
    execute_gh_command(
        ["gh", "pr", "edit", str(pr_number), "--add-label", label],
        cwd=repo_root,
    )

def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
    result = execute_gh_command(
        ["gh", "pr", "view", str(pr_number), "--json", "labels", "-q", ".labels[].name"],
        cwd=repo_root,
    )
    labels = result.stdout.strip().split("\n") if result.stdout.strip() else []
    return label in labels
```

### Fake (`packages/erk-shared/src/erk_shared/github/fake.py`)

```python
def __init__(
    self,
    *,
    pr_labels: dict[int, set[str]] | None = None,  # PR number -> label set
    # ... other parameters
) -> None:
    self._pr_labels = pr_labels or {}
    self._added_labels: list[tuple[int, str]] = []

@property
def added_labels(self) -> list[tuple[int, str]]:
    """Labels added via add_label_to_pr (for test assertions)."""
    return list(self._added_labels)

def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
    self._added_labels.append((pr_number, label))
    if pr_number not in self._pr_labels:
        self._pr_labels[pr_number] = set()
    self._pr_labels[pr_number].add(label)

def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
    return label in self._pr_labels.get(pr_number, set())
```

### DryRun (`packages/erk-shared/src/erk_shared/github/dry_run.py`)

```python
def add_label_to_pr(self, repo_root: Path, pr_number: int, label: str) -> None:
    # Write operation - no-op in dry run
    pass

def has_pr_label(self, repo_root: Path, pr_number: int, label: str) -> bool:
    # Read operation - delegate to wrapped implementation
    return self._wrapped.has_pr_label(repo_root, pr_number, label)
```

## Testing

Test the extraction skip behavior with FakeGitHub:

```python
def test_land_skips_extraction_for_labeled_pr() -> None:
    """PRs with erk-skip-extraction label skip pending-extraction."""
    fake_github = FakeGitHub(
        pr_labels={123: {"erk-skip-extraction"}},
    )
    ctx = create_test_context(github=fake_github)

    result = land_pr(ctx, pr_number=123)

    # Verify extraction was skipped
    assert result.extraction_skipped is True
    assert result.worktree_deleted is True


def test_land_marks_extraction_for_normal_pr() -> None:
    """Normal PRs are marked for pending extraction."""
    fake_github = FakeGitHub(
        pr_labels={123: set()},  # No skip label
    )
    ctx = create_test_context(github=fake_github)

    result = land_pr(ctx, pr_number=123)

    # Verify normal extraction flow
    assert result.extraction_skipped is False
    assert result.pending_extraction is True
```

## Related Documentation

- [Glossary: erk-skip-extraction](../glossary.md#erk-skip-extraction)
- [Glossary: Extraction Plan](../glossary.md#extraction-plan)
- [Erk Architecture Patterns](erk-architecture.md) - Four-layer integration pattern
- [Plan Lifecycle](../planning/lifecycle.md) - Full plan workflow
