---
title: Adding Review Capabilities
read_when:
  - "adding review capabilities"
  - "creating code review definitions"
  - "understanding ReviewCapability pattern"
---

# Adding Review Capabilities

Reviews are capabilities that install code review definition files. They follow the `ReviewCapability` template pattern and require the `code-reviews-system` capability as a dependency.

## Overview

Review capabilities:

- Install `.claude/reviews/<name>.md` files
- Are project-level (require repo context)
- Use the `ReviewCapability` base class
- Require only 2 property implementations
- Have preflight checks for `code-reviews-system` dependency

## File Location

```
src/erk/capabilities/reviews/<review_name>.py
```

## Implementation

### Step 1: Create the Capability File

Create `src/erk/capabilities/reviews/my_review.py`:

```python
"""MyReviewCapability - description of what this review checks."""

from erk.core.capabilities.review_capability import ReviewCapability


class MyReviewCapability(ReviewCapability):
    """Brief description of the code review.

    Reviews code for specific patterns or standards.
    Requires: code-reviews-system capability
    """

    @property
    def review_name(self) -> str:
        return "my-review"

    @property
    def description(self) -> str:
        return "Human-readable description for CLI output"
```

### Step 2: Register in Registry

In `src/erk/core/capabilities/registry.py`:

1. Add import at top:

```python
from erk.capabilities.reviews.my_review import MyReviewCapability
```

2. Add instance to `_all_capabilities()` tuple:

```python
@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        # ... existing capabilities ...
        MyReviewCapability(),
    )
```

### Step 3: Create the Review Definition

The review definition must exist in bundled artifacts:

```
src/erk/bundled/.github/reviews/my-review.md
```

The review definition file contains instructions for Claude on how to review code for this specific standard.

## What ReviewCapability Provides

The base class handles:

- `name` property (returns `"review-{review_name}"`)
- `scope` property (returns `"project"`)
- `artifacts` property (tracks the review file)
- `managed_artifacts` property (declares as managed)
- `is_installed()` (checks if file exists)
- `preflight()` (verifies code-reviews-system is installed)
- `install()` (copies from bundled artifacts)
- `uninstall()` (removes the file)

You only implement:

- `review_name` - The filename (without .md extension)
- `description` - Human-readable description

## Preflight Check

ReviewCapability automatically checks that `code-reviews-system` capability is installed before allowing installation. This ensures the GitHub Actions workflow exists to run reviews.

```python
def preflight(self, repo_root: Path | None) -> CapabilityResult:
    """Check that code-reviews-system capability is installed."""
    workflow_path = repo_root / ".github" / "workflows" / "code-reviews.yml"
    if not workflow_path.exists():
        return CapabilityResult(
            success=False,
            message="Requires 'code-reviews-system' capability to be installed first",
        )
    return CapabilityResult(success=True, message="")
```

## Example: DignifiedPythonReviewDefCapability

```python
"""DignifiedPythonReviewDefCapability - dignified Python code review."""

from erk.core.capabilities.review_capability import ReviewCapability


class DignifiedPythonReviewDefCapability(ReviewCapability):
    """Dignified Python code review definition.

    Reviews Python code for adherence to dignified-python standards.
    Requires: code-reviews-system capability
    """

    @property
    def review_name(self) -> str:
        return "dignified-python"

    @property
    def description(self) -> str:
        return "Dignified Python style code review"
```

This installs:

- `.claude/reviews/dignified-python.md` file
- CLI name: `review-dignified-python`

## Testing

```bash
# First install the dependency
erk init capability install code-reviews-system

# List capabilities to verify registration
erk init capability list

# Check if installed
erk init capability status review-my-review

# Install
erk init capability install review-my-review

# Uninstall
erk init capability uninstall review-my-review
```

## Checklist

- [ ] File created at `src/erk/capabilities/reviews/<name>.py`
- [ ] Class extends `ReviewCapability`
- [ ] `review_name` property returns the review filename (no .md)
- [ ] `description` property returns human-readable text
- [ ] Import added to `registry.py`
- [ ] Instance added to `_all_capabilities()` tuple
- [ ] Review definition exists at `src/erk/bundled/.github/reviews/<name>.md`
- [ ] `code-reviews-system` capability is documented as a dependency

## Related Documentation

- [Folder Structure](folder-structure.md) - Where capability files go
- [Adding New Capabilities](adding-new-capabilities.md) - General capability pattern
