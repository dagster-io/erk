---
title: Review Types Taxonomy
last_audited: "2026-02-04 05:48 PT"
audit_result: clean
read_when:
  - creating a new review workflow
  - deciding whether to extend an existing review or create a new one
  - understanding review scope boundaries
tripwires:
  - action: "creating a new review without checking taxonomy"
    warning: "Consult this taxonomy first. Creating overlapping reviews wastes CI resources and confuses PR status checks."
---

# Review Types Taxonomy

This document provides a decision framework for choosing review types and determining whether to create a new review or extend an existing one.

## Core Principle

**Reviews should have distinct, complementary scopes.** Overlapping reviews waste CI resources and create confusion about which review is responsible for which checks.

## Review Dimensions

Reviews differ along three dimensions:

1. **Quality Dimension** - What aspect of code quality does it check?
2. **Scope** - What files/changes does it examine?
3. **Tools** - What tools or checks does it use?

### Quality Dimensions

| Dimension     | Checks                                   | Example Reviews                 |
| ------------- | ---------------------------------------- | ------------------------------- |
| Code Quality  | Style, linting, formatting, conventions  | ruff-check, prettier            |
| Test Coverage | Test execution, coverage metrics, fails  | pytest-unit, pytest-integration |
| Documentation | Doc quality, completeness, accuracy      | doc-audit, learned-docs         |
| Security      | Vulnerabilities, secrets, permissions    | bandit, secret-scan             |
| Integration   | Cross-system checks, PR format, metadata | pr-format, changelog            |

## Decision Tree

### Question 1: Does an existing review check this quality dimension?

**YES** → Go to Question 2

**NO** → Consider creating a new review (proceed to Question 3)

### Question 2: Can the existing review be extended?

**Ask:**

- Does the existing review already run on the same files?
- Would the new check fit naturally with the existing checks?
- Would the combined review still have a clear, single responsibility?

**If YES** → **Extend the existing review**

- Add new checks to the existing workflow
- Update review documentation
- Verify marker behavior handles new check failures

**If NO** → Proceed to Question 3

### Question 3: Is the new review complementary to existing reviews?

**Complementary reviews** have:

- **Different scopes** - Check different files or triggers
- **Different quality dimensions** - Address different aspects of quality
- **Different tools** - Use distinct tool chains

**Overlapping reviews** have:

- **Same scope** - Run on same files/triggers
- **Similar checks** - Address same quality dimension
- **Redundant tools** - Use same or equivalent tools

**If COMPLEMENTARY** → **Create new review**

**If OVERLAPPING** → **Extend existing review instead**

## Examples

### Example 1: Code Quality vs Test Coverage

**Scenario**: Want to add test coverage checks to a project that already has ruff linting.

**Analysis:**

- Different quality dimensions (style vs tests)
- Different tools (ruff vs pytest)
- Different scopes (source code vs test execution)

**Decision**: **Create separate reviews** (ruff-check, pytest-coverage)

**Rationale**: These are complementary checks that can run independently and fail independently.

### Example 2: Linting Python vs Linting Markdown

**Scenario**: Project has ruff for Python, want to add prettier for Markdown.

**Analysis:**

- Same quality dimension (code quality/formatting)
- Different tools (ruff vs prettier)
- Different scopes (_.py vs _.md)

**Decision**: **Create separate reviews** (python-quality, markdown-format)

**Rationale**: Different file types and tools justify separation, even though both are "formatting."

### Example 3: Doc Duplication vs Doc Completeness

**Scenario**: Project has doc-audit (duplication), want to add doc-completeness (coverage).

**Analysis:**

- Same quality dimension (documentation)
- Same scope (docs/learned/\*.md)
- Different aspects (duplication vs completeness)

**Decision**: **Extend doc-audit review**

**Rationale**: Both check documentation quality on the same files. Combining avoids duplicate file scans.

### Example 4: Unit Tests vs Integration Tests

**Scenario**: Project has pytest-unit, want to add integration test checks.

**Analysis:**

- Same quality dimension (test coverage)
- Different scopes (unit vs integration)
- Same tool (pytest) but different markers/options

**Decision**: **Create separate reviews** (pytest-unit, pytest-integration)

**Rationale**: Different test scopes often have different performance profiles and failure modes. Separation allows:

- Running unit tests on every PR (fast)
- Running integration tests only on specific triggers (slow)
- Independent failure reporting

## Scope Overlaps to Avoid

### Anti-Pattern 1: Duplicate Tool Invocations

❌ **Bad**: Two reviews both run ruff on src/\*_/_.py

✅ **Good**: One review runs all ruff checks (lint + format)

### Anti-Pattern 2: Same Files, Similar Checks

❌ **Bad**: One review checks doc structure, another checks doc links, both scan docs/\*_/_.md

✅ **Good**: One doc-audit review checks structure, links, and quality together

### Anti-Pattern 3: Quality Dimension Split Without Justification

❌ **Bad**: Separate reviews for "ruff lint" and "ruff format" that both run on every PR

✅ **Good**: One python-quality review that runs both ruff lint and ruff format

## When to Create a New Review

Create a new review when:

1. ✅ **New quality dimension** - No existing review checks this aspect (e.g., first security review)
2. ✅ **New file scope** - Review targets files not covered by existing reviews (e.g., .github/workflows/\*.yml)
3. ✅ **Performance isolation** - Check is slow and should run independently (e.g., integration tests)
4. ✅ **Different triggers** - Check needs different event triggers than existing reviews (e.g., release-only checks)
5. ✅ **Independent failure modes** - Failure doesn't correlate with other review failures

## When to Extend an Existing Review

Extend an existing review when:

1. ✅ **Same quality dimension** - Check addresses same aspect of quality
2. ✅ **Same file scope** - Check examines same files/paths
3. ✅ **Related tools** - Check uses same or compatible tool chain
4. ✅ **Correlated failures** - If one check fails, the other often fails too
5. ✅ **Shared setup** - Checks require same environment or dependencies

## Complementary vs Overlapping

### Complementary Reviews (Good)

| Review A       | Review B              | Why Complementary                            |
| -------------- | --------------------- | -------------------------------------------- |
| ruff-check     | pytest-unit           | Different dimensions (style vs tests)        |
| doc-audit      | learned-docs-verbatim | Different aspects (duplication vs code sync) |
| python-quality | markdown-format       | Different scopes (_.py vs _.md)              |
| pr-format      | changelog-check       | Different triggers (every PR vs release)     |

### Overlapping Reviews (Bad)

| Review A       | Review B           | Why Overlapping                               |
| -------------- | ------------------ | --------------------------------------------- |
| ruff-lint      | ruff-format        | Same tool, same files, same quality dimension |
| doc-structure  | doc-links          | Same scope, same dimension, could combine     |
| test-unit-fast | test-unit-slow     | Artificial split, no real distinction         |
| python-style   | python-conventions | Unclear boundary, likely redundant            |

## Review Naming Conventions

Name reviews after their primary quality dimension and scope:

- `<dimension>-<scope>` - e.g., `doc-audit`, `test-unit`, `security-scan`
- `<tool>-<scope>` - e.g., `ruff-check`, `prettier-format`, `pytest-unit`

**Avoid:**

- ❌ Ambiguous names like `quality-check` (what quality dimension?)
- ❌ Tool-only names like `ruff` (what does it check?)
- ❌ Scope-only names like `python` (what aspect of Python?)

## CI Resource Optimization

### Review Triggers

Configure reviews to run only when needed:

```yaml
on:
  pull_request:
    paths:
      - "src/**/*.py" # Only run on Python changes
```

**Pattern**: Narrow triggers to avoid unnecessary CI runs.

### Review Performance

**Fast reviews** (< 30s) can run on every PR:

- Linting (ruff, prettier)
- Format checks
- Type checking (mypy)

**Slow reviews** (> 1 min) should run selectively:

- Integration tests
- Coverage reports
- Large-scale analysis

**Pattern**: Use conditional triggers or manual workflow dispatch for slow reviews.

## Related Documentation

- [Review Development Guide](../reviews/development.md) - Step-by-step guide for creating reviews
- [Doc Audit Review](../reviews/doc-audit-review.md) - Example documentation review
- [Learned Docs Review](../reviews/learned-docs-review.md) - Example code duplication review
- [Reviews Index](../reviews/index.md) - Complete list of all reviews

## Code References

- Workflow files: `.github/workflows/code-reviews.yml`
- PR check integration: `src/erk/cli/commands/pr/check_cmd.py`
