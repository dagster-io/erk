---
title: Adding Review Capabilities
read_when:
  - "adding review capabilities"
  - "creating code review definitions"
  - "understanding ReviewCapability pattern"
tripwires:
  - action: "creating a review capability"
    warning: "Review definition MUST exist at .erk/reviews/{review_name}.md in erk repo root. At runtime, get_bundled_erk_dir() resolves this location (src/erk/artifacts/paths.py). Missing source file causes install failure."
  - action: "review capability installation fails"
    warning: "ReviewCapability has automatic preflight check for code-reviews-system workflow. Install will fail if .github/workflows/code-reviews.yml doesn't exist in target repo. Install code-reviews-system capability first."
last_audited: "2026-02-16 04:53 PT"
audit_result: clean
---

# Adding Review Capabilities

Review capabilities install code review definition files to `.erk/reviews/` in target projects. They are the thinnest capability type—only two properties required—because `ReviewCapability` base class handles all installation logic.

## Why ReviewCapability Exists

<!-- Source: src/erk/core/capabilities/review_capability.py, ReviewCapability -->

Review definitions follow an identical pattern: install a single `.md` file from bundled artifacts, check for the `code-reviews-system` dependency, track installation state. Without a base class, every review capability would duplicate this boilerplate.

**Key design decision:** ReviewCapability is project-scoped because reviews require GitHub Actions context. Global-scope reviews would be meaningless—there's no repository to review.

## The Two-Property Contract

<!-- Source: src/erk/capabilities/reviews/dignified_python.py, DignifiedPythonReviewDefCapability -->

Subclasses implement:

1. **`review_name`**: Filename without `.md` extension (e.g., `"dignified-python"`)
2. **`description`**: Human-readable CLI description

**Why just two properties?** The base class derives everything else:

- CLI name: `f"review-{review_name}"` (e.g., `review-dignified-python`)
- Artifact path: `.erk/reviews/{review_name}.md`
- Installation check: file existence test
- Preflight check: `code-reviews-system` workflow detection

See `DignifiedPythonReviewDefCapability` for the canonical minimal implementation—20 lines total, 2 properties, zero methods.

## Bundled Source Location Trade-off

<!-- Source: src/erk/artifacts/paths.py, get_bundled_erk_dir -->

Review definitions are sourced from `.erk/reviews/` in the erk repository. This placement matches the customer layout — reviews are installed to `.erk/reviews/` in target repos, and erk itself stores them in the same location for dogfooding.

At runtime, `get_bundled_erk_dir()` resolves this location — handles both editable installs (erk repo root) and wheel installs (bundled at `erk/data/erk/`).

## Automatic Dependency Enforcement

<!-- Source: src/erk/core/capabilities/review_capability.py, ReviewCapability.preflight -->

ReviewCapability implements `preflight()` to check for `.github/workflows/code-reviews.yml` in the target repo. This prevents the broken state where review definitions exist but no workflow runs them.

**Why automatic preflight instead of documenting the dependency?** Prior attempts at "just document it" failed—agents and users would install reviews without the workflow, then report bugs when reviews never ran. Preflight checks shift the error from runtime to install-time.

## Registration Pattern

<!-- Source: src/erk/core/capabilities/registry.py, _all_capabilities -->

Registration requires **both** import and instantiation in `registry.py`:

```python
from erk.capabilities.reviews.my_review import MyReviewCapability

@cache
def _all_capabilities() -> tuple[Capability, ...]:
    return (
        # ... other capabilities ...
        MyReviewCapability(),  # Must instantiate
    )
```

**Why both steps?** See [Adding New Capabilities](adding-new-capabilities.md)—the `@cache` decorator and registry pattern require explicit instantiation for discovery. Import alone is insufficient.

## State Tracking: Installation vs Managed Artifacts

<!-- Source: src/erk/core/capabilities/review_capability.py, ReviewCapability.managed_artifacts -->

ReviewCapability declares `managed_artifacts` to enable `erk doctor` detection:

- `ManagedArtifact(name=review_name, artifact_type="review")` tells the system this capability owns the review file
- Installation state is tracked separately via `add_installed_capability()` in `.erk/state.toml`

**Why separate tracking?** Managed artifacts answer "who owns this file?" Installation state answers "is this capability enabled?" A review file might exist (user-created) without the capability being installed.

## Anti-Pattern: Installing Reviews Without Workflow

**DON'T:**

```bash
erk init capability add review-dignified-python  # Fails preflight
```

**DO:**

```bash
erk init capability add code-reviews-system      # Install workflow first
erk init capability add review-dignified-python  # Then install review
```

The preflight check prevents this, but understanding WHY clarifies the dependency chain: workflows consume reviews, so workflows must exist first.

## Decision Table: Review vs Skill vs Workflow

| If you're creating...                              | Capability Type     | Target Directory     |
| -------------------------------------------------- | ------------------- | -------------------- |
| Code review guidance for Claude                    | `ReviewCapability`  | `.erk/reviews/`      |
| Agent instruction manual (loaded into context)     | `SkillCapability`   | `.claude/skills/`    |
| GitHub Actions workflow (with actions/scripts)     | Direct `Capability` | `.github/workflows/` |
| Multi-file system (e.g., hooks + reminders + docs) | Direct `Capability` | Multiple directories |

Use `ReviewCapability` only for single `.md` files that define review criteria. Skills and workflows have different base classes.

## Related Topics

- [Adding New Capabilities](adding-new-capabilities.md) - General capability pattern and registration
- [Capability System Architecture](../architecture/capability-system.md) - Complete system design
- [Bundled Artifacts System](../architecture/bundled-artifacts.md) - How review definitions are sourced
