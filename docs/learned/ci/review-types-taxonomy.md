---
title: Review Types Taxonomy
last_audited: "2026-02-08 16:45 PT"
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

When adding a new quality check to CI, the core question is: **extend an existing review or create a new one?** This document provides the decision framework.

## Why This Matters

Overlapping reviews create three problems:

1. **CI waste** — multiple reviews scanning the same files, running the same tool invocations
2. **Confusing status checks** — unclear which review owns which failure
3. **Maintenance burden** — changes to scope require updating multiple workflows

The goal: **distinct, complementary scopes** where each review has a clear single responsibility.

<!-- Source: .github/workflows/code-reviews.yml, discover job -->

## The Three-Dimensional Framework

Reviews differ along three orthogonal dimensions. Use these to identify overlaps:

### 1. Quality Dimension (What aspect)

| Dimension     | Checks                                   |
| ------------- | ---------------------------------------- |
| Code Quality  | Style, linting, formatting, conventions  |
| Test Coverage | Test execution, coverage metrics, fails  |
| Documentation | Doc quality, completeness, accuracy      |
| Security      | Vulnerabilities, secrets, permissions    |
| Integration   | Cross-system checks, PR format, metadata |

**Key insight:** Reviews checking different quality dimensions can run on the same files without overlap (e.g., `ruff-check` for style and `pytest-unit` for tests both run on `src/**/*.py`).

### 2. Scope (What files)

- File patterns (`src/**/*.py` vs `docs/**/*.md`)
- Event triggers (every PR vs release-only)
- Change types (additions only vs all modifications)

**Key insight:** Identical file patterns don't always mean overlap if quality dimensions differ.

### 3. Tools (What runs)

- Same tool invocation = likely overlap (both running `ruff check`)
- Different tools = likely complementary (ruff vs pytest)
- Same tool, different flags = evaluate carefully (pytest with different markers)

**Key insight:** Duplicate tool invocations are the strongest signal of overlap.

## Decision Tree

### Question 1: Does an existing review check this quality dimension?

**NO** → Strong signal to create a new review (proceed to Question 3 for confirmation)

**YES** → Proceed to Question 2

### Question 2: Can the existing review be extended?

Check all three:

1. **Same files?** Does the existing review already run on these paths?
2. **Natural fit?** Would combining checks feel coherent or forced?
3. **Clear responsibility?** Would the combined review still have a single, understandable purpose?

**All YES** → **Extend the existing review**

**Any NO** → Proceed to Question 3

### Question 3: Is the new review complementary?

**Complementary** means:

- Different quality dimensions (style vs tests)
- OR different file scopes (`.py` vs `.md`)
- OR different tools (ruff vs pytest)
- OR different performance profiles (fast lints vs slow integration tests)

**Overlapping** means:

- Same quality dimension AND same scope AND similar tools
- Duplicate tool invocations on same files
- Unclear which review owns which failures

**If COMPLEMENTARY** → **Create new review**

**If OVERLAPPING** → **Extend existing review instead**

## Anti-Patterns (What Not to Do)

### Anti-Pattern 1: Duplicate Tool Invocations

❌ **BAD**: Two reviews both run `ruff check src/**/*.py`

✅ **GOOD**: One review runs all ruff checks together (lint + format)

**Why wrong:** Scans the same files twice, doubles CI time, no benefit

### Anti-Pattern 2: Quality Dimension Split Without Justification

❌ **BAD**: Separate reviews for "ruff lint" and "ruff format" both triggered on every PR

✅ **GOOD**: One python-quality review runs both

**Why wrong:** Same dimension, same files, same tool — splitting creates artificial boundaries

**Exception:** If one check is fast and one is slow, separation for performance isolation is justified.

### Anti-Pattern 3: Unclear Ownership

❌ **BAD**: One review checks doc structure, another checks doc links, both scan `docs/**/*.md`

✅ **GOOD**: One learned-docs review checks structure, links, and quality together

**Why wrong:** When a doc fails, which review is responsible? Overlap creates confusion.

## Decision Examples (Learn from History)

### Example 1: Code Quality vs Test Coverage

**Scenario:** Project has ruff linting, want to add test coverage checks.

**Analysis:**

- Different quality dimensions (style vs test execution)
- Different tools (ruff vs pytest)
- Different scopes (static analysis vs runtime)

**Decision:** **Create separate reviews** (ruff-check, pytest-unit)

**Rationale:** These are independent concerns that can fail independently. A style violation doesn't imply test failures.

### Example 2: Unit Tests vs Integration Tests

**Scenario:** Project has pytest-unit, want to add integration test checks.

**Analysis:**

- Same quality dimension (test coverage)
- Same tool (pytest)
- Different performance profiles (fast vs slow)
- Different markers (`-m unit` vs `-m integration`)

**Decision:** **Create separate reviews** (pytest-unit, pytest-integration)

**Rationale:** Performance isolation matters. Unit tests run on every PR (< 30s), integration tests run selectively (> 2 min). Independent failure modes justify separation.

<!-- Source: .erk/reviews/test-coverage.md, early exit conditions -->

### Example 3: Doc Duplication vs Doc Completeness

**Scenario:** Project has learned-docs review (verbatim code, duplication, accuracy), want to add doc-completeness (coverage metrics).

**Analysis:**

- Same quality dimension (documentation)
- Same scope (`docs/learned/**/*.md`)
- Different aspects but related (quality vs completeness)

**Decision:** **Extend learned-docs review**

**Rationale:** Both check documentation quality on the same files. Combining avoids duplicate file scans and keeps all doc quality checks in one place.

<!-- Source: .erk/reviews/audit-pr-docs.md, full file audit pattern -->

### Example 4: Python Linting vs Markdown Formatting

**Scenario:** Project has ruff for Python, want to add prettier for Markdown.

**Analysis:**

- Same quality dimension (formatting)
- Different tools (ruff vs prettier)
- Different scopes (`**/*.py` vs `**/*.md`)

**Decision:** **Create separate reviews** (python-quality, markdown-format)

**Rationale:** Different file types and tools justify separation even within the same quality dimension.

## When to Create vs Extend (Quick Reference)

### Create New Review When:

1. ✅ **New quality dimension** — First security review, first doc quality check
2. ✅ **New file scope** — First check targeting `.github/workflows/*.yml`
3. ✅ **Performance isolation** — Slow integration tests separate from fast unit tests
4. ✅ **Different triggers** — Release-only checks separate from PR checks
5. ✅ **Independent failure modes** — Failures don't correlate with other reviews

### Extend Existing Review When:

1. ✅ **Same quality dimension** — Adding another style check to existing style review
2. ✅ **Same file scope** — Check examines files already covered
3. ✅ **Related tools** — Same tool, different flags (e.g., `ruff` with different rules)
4. ✅ **Correlated failures** — If one check fails, the other often fails too
5. ✅ **Shared setup** — Checks require same environment or dependencies

## Complementary vs Overlapping (Concrete Patterns)

### Complementary (Good — these can coexist)

| Review A       | Review B           | Why Complementary                        |
| -------------- | ------------------ | ---------------------------------------- |
| ruff-check     | pytest-unit        | Different dimensions (style vs tests)    |
| learned-docs   | pytest-unit        | Different dimensions (docs vs tests)     |
| python-quality | markdown-format    | Different scopes (`.py` vs `.md`)        |
| pr-format      | changelog-check    | Different triggers (every PR vs release) |
| pytest-unit    | pytest-integration | Performance isolation (fast vs slow)     |

### Overlapping (Bad — merge these)

| Review A       | Review B           | Why Overlapping                               |
| -------------- | ------------------ | --------------------------------------------- |
| ruff-lint      | ruff-format        | Same tool, same files, same quality dimension |
| doc-structure  | doc-links          | Same scope, same dimension, could combine     |
| test-unit-fast | test-unit-slow     | Artificial split, no real distinction         |
| python-style   | python-conventions | Unclear boundary, likely redundant            |

## Naming Conventions

Name reviews after their primary quality dimension and scope:

**Good patterns:**

- `<dimension>-<scope>` → `learned-docs`, `test-unit`, `security-scan`
- `<tool>-<scope>` → `ruff-check`, `prettier-format`, `pytest-integration`

**Avoid:**

- ❌ `quality-check` — which quality dimension?
- ❌ `ruff` — what does it check?
- ❌ `python` — what aspect of Python?

**Why naming matters:** Clear names make scope boundaries obvious and prevent accidental overlap.

## Performance Optimization Patterns

### Pattern 1: Path-Based Triggers

Configure reviews to skip when irrelevant files change:

```yaml
on:
  pull_request:
    paths:
      - "src/**/*.py" # Only run on Python changes
```

**When to use:** Reviews with clear file type boundaries (Python-only, docs-only).

**Why it works:** GitHub Actions skips the job entirely if paths don't match, saving CI time.

<!-- Source: .github/workflows/code-reviews.yml, paths filtering -->

### Pattern 2: Performance Tiering

**Fast reviews** run on every PR: linting (ruff, prettier), format checks, type checking.

**Slow reviews** run selectively: integration tests (manual trigger or specific labels), coverage reports, large-scale analysis.

**Why it works:** Developers get fast feedback from lints, slow checks don't block iteration.

### Pattern 3: Early Exit for Empty Diffs

Reviews should detect when there's nothing relevant to check and exit early with code 0.

<!-- Source: .erk/reviews/test-coverage.md, Step 2 early exit -->

**When to use:** Reviews that only care about certain change types (e.g., test coverage only matters if source changed). See the early exit pattern in `.erk/reviews/test-coverage.md`.

**Why it works:** Avoids posting empty or meaningless review comments.

## Review Configuration Format

All reviews live in `.erk/reviews/*.md` and share this frontmatter structure:

```yaml
---
name: Review Display Name
paths:
  - "glob/pattern/**/*.ext"
marker: "<!-- unique-marker -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---
```

**Key fields:**

- `paths` — triggers review only when these files change
- `marker` — HTML comment for PR comment identification/updates
- `model` — usually Haiku for cost efficiency
- `allowed_tools` — security boundary for Claude Code remote sessions

<!-- Source: .github/workflows/code-reviews.yml, matrix strategy -->

## Related Documentation

- `.erk/reviews/audit-pr-docs.md` — Example documentation quality review
- `.erk/reviews/dignified-python.md` — Example code quality review
- `.erk/reviews/test-coverage.md` — Example coverage review with early exit
- `docs/learned/ci/review-spec-format.md` — Complete review specification reference
