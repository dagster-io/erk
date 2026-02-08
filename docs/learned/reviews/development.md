---
title: Review Development Guide
last_audited: "2026-02-04 05:48 PT"
audit_result: edited
read_when:
  - creating a new GitHub review workflow
  - adding review automation to CI
  - understanding review creation process
tripwires:
  - action: "creating a new review without checking if existing reviews can be extended"
    warning: "Before creating a new review, check if an existing review type can handle the new checks. Reviews should have distinct, complementary scopes."
---

# Review Development Guide

This document provides a step-by-step guide for creating new GitHub review workflows in erk's CI system.

## When to Create a New Review

Create a new review when:

1. **Distinct scope** - The checks don't fit into any existing review type
2. **Different triggers** - The review needs to run on different events or files than existing reviews
3. **Separate concerns** - The review addresses a different quality dimension (e.g., security vs style vs tests)

**Don't create a new review** if:

- Existing review can be extended with additional checks
- The checks overlap significantly with an existing review
- The review would run on the same files/triggers as an existing review

**Decision framework**: See [Review Types Taxonomy](../ci/review-types-taxonomy.md) for guidance on choosing review types.

## Review Creation Checklist

### Step 1: Define Review Scope

**Questions to answer:**

- What quality dimension does this review check? (code quality, test coverage, documentation, security, etc.)
- What files/changes trigger the review?
- What markers does the review write? (review-approved, review-failed, review-blocked, etc.)
- What tools does the review use? (ruff, prettier, pytest, custom scripts, etc.)

**Document in a design doc** before implementation. Include:

- Review name and purpose
- Trigger conditions
- Check criteria
- Marker behavior
- Tool restrictions

### Step 2: Choose Review Type

Based on [Review Types Taxonomy](../ci/review-types-taxonomy.md):

- **Code Quality Review** - Style, linting, formatting checks
- **Test Coverage Review** - Test execution and coverage metrics
- **Documentation Review** - Doc quality, completeness, accuracy
- **Integration Review** - Cross-system checks (e.g., learned docs, PR formatting)

Choose the type that best matches your scope. This determines naming, organization, and integration patterns.

### Step 3: Implement YAML Workflow

**File location**: `.github/workflows/review-<name>.yml`

**Required structure:**

```yaml
name: <Review Name>
on:
  pull_request:
    paths:
      # Trigger paths (use ** for recursive matching)
      - "src/**/*.py"
      - "tests/**/*.py"

permissions:
  contents: read
  pull-requests: write # Required for marker writing

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Run checks (use existing actions or custom scripts)
      - name: Run <tool>
        run: |
          # Tool invocation
          make check-something

      # Write marker based on result
      - name: Write review marker
        if: always() # Run even if checks fail
        run: |
          if [ ${{ steps.check.outcome }} == "success" ]; then
            erk exec marker create --type review-<name> --content approved
          else
            erk exec marker create --type review-<name> --content failed
          fi
```

**Key patterns:**

1. **Trigger paths** - Be specific to avoid unnecessary review runs
2. **Tool restrictions** - Use existing tools when possible (ruff, prettier, pytest)
3. **Marker naming** - Use `review-<name>` prefix for consistency
4. **Conditional markers** - Always write a marker (success or failure)

### Step 4: Register Marker Type

Register the review's marker type in the marker system. Search the codebase for existing marker registrations to find the current pattern and location (`grep -r "MarkerType\|marker.*schema" src/`).

### Step 5: Integrate with PR Checks

**File location**: `src/erk/cli/commands/pr/check_cmd.py`

Add the new review to the PR check logic. Read the existing `check_cmd.py` to understand the current pattern for integrating review results.

### Step 6: Document the Review

Create review documentation:

**File location**: `docs/learned/reviews/<name>-review.md`

**Required sections:**

1. **Purpose** - What the review checks
2. **Trigger conditions** - When it runs
3. **Pass/fail criteria** - What causes approval vs failure
4. **Marker behavior** - What markers are written and when
5. **Tools used** - Dependencies and versions
6. **Related reviews** - How this review complements others

**Template:**

```markdown
---
title: <Review Name> Review
read_when:
  - creating <type> checks
  - understanding <review> behavior
tripwires:
  - action: "specific action to avoid"
    warning: "specific warning message"
---

# <Review Name> Review

## Purpose

[What quality dimension this review checks]

## Trigger Conditions

[When the review runs - paths, events, conditions]

## Pass/Fail Criteria

[What determines approval vs failure]

## Marker Behavior

[What markers are written and when]

## Tools Used

[Dependencies, versions, configurations]

## Related Reviews

[How this review complements or differs from others]
```

### Step 7: Update Reviews Index

**File location**: `docs/learned/reviews/index.md`

Add entry to index with frontmatter:

```markdown
- **[<name>-review.md](<name>-review.md)** — [Brief description]. Read when [trigger conditions].
```

### Step 8: Test the Review

**Local testing:**

1. Create a test branch with changes that should trigger the review
2. Push the branch and create a draft PR
3. Verify the review workflow runs
4. Check marker is written correctly
5. Verify `erk pr check` reports the review status

**CI testing:**

1. Verify review runs on expected file changes
2. Verify review does NOT run on unrelated file changes
3. Test both pass and fail scenarios
4. Check marker metadata is correct

## YAML Schema Reference

### Trigger Paths

```yaml
on:
  pull_request:
    paths:
      - "src/**/*.py" # All Python files in src/
      - "tests/**/*.py" # All Python files in tests/
      - "!tests/fixtures/**" # Exclude fixtures
      - "docs/**/*.md" # All markdown in docs/
```

### Conditional Markers

```yaml
- name: Write success marker
  if: success()
  run: erk exec marker create --type review-my --content approved

- name: Write failure marker
  if: failure()
  run: erk exec marker create --type review-my --content failed
```

### Tool Invocation Patterns

**Pattern 1: Make target**

```yaml
- name: Run checks
  run: make check-my-review
```

**Pattern 2: Direct tool invocation**

```yaml
- name: Run ruff
  run: ruff check src/ tests/
```

**Pattern 3: Custom script**

```yaml
- name: Run custom check
  run: python scripts/check_my_review.py
```

## Tool Restrictions

### Allowed Tools

- **Python**: ruff, pytest, mypy, coverage
- **Markdown**: prettier
- **Git**: git commands via `erk exec` helpers
- **GitHub CLI**: gh commands for API access
- **Custom scripts**: Python scripts in `scripts/` directory

### Restricted Tools

- ❌ **No external services** - Reviews must be self-contained
- ❌ **No API keys required** - Must work in public CI without secrets
- ❌ **No network calls** - Except for GitHub API via gh CLI
- ❌ **No heavy dependencies** - Keep review fast and lightweight

## Marker Naming Conventions

- **Prefix**: `review-<name>`
- **Content values**: `approved`, `failed`, `blocked`, `skipped`
- **Metadata keys**: Use snake_case

**Examples:**

- `review-learned-docs` - Learned docs review (verbatim code, duplication, accuracy)
- `review-test-coverage` - Test coverage review

## Common Patterns

### Pattern 1: Multiple Checks in One Review

```yaml
- name: Run lint
  id: lint
  run: ruff check src/

- name: Run format check
  id: format
  run: ruff format --check src/

- name: Write marker
  if: always()
  run: |
    if [ ${{ steps.lint.outcome }} == "success" ] && [ ${{ steps.format.outcome }} == "success" ]; then
      erk exec marker create --type review-quality --content approved
    else
      erk exec marker create --type review-quality --content failed
    fi
```

### Pattern 2: Conditional Review Execution

```yaml
- name: Check if review needed
  id: check_needed
  run: |
    if git diff --name-only origin/main | grep -q "^src/"; then
      echo "needed=true" >> $GITHUB_OUTPUT
    fi

- name: Run review
  if: steps.check_needed.outputs.needed == 'true'
  run: make review
```

### Pattern 3: Review with Metadata

```yaml
- name: Run review with output
  id: review
  run: |
    OUTPUT=$(make review-with-output)
    echo "check_count=$(echo $OUTPUT | jq .count)" >> $GITHUB_OUTPUT

- name: Write marker with metadata
  run: |
    erk exec marker create \
      --type review-my \
      --content approved \
      --metadata check_count=${{ steps.review.outputs.check_count }}
```

## Integration with Existing Reviews

### Existing Reviews (as of 2025-01)

1. **learned-docs** - Documentation quality review (verbatim code, duplication, accuracy)
2. (More reviews documented in reviews/index.md)

### Avoiding Overlap

Before creating a new review, check if existing reviews already cover:

- The same file paths
- Similar quality dimensions
- Related tools or checks

**Decision matrix**: See [Review Types Taxonomy](../ci/review-types-taxonomy.md) for guidance on avoiding overlap.

## Related Documentation

- [Review Types Taxonomy](../ci/review-types-taxonomy.md) - Decision framework for choosing review types
- [Learned Docs Review](learned-docs-review.md) - Example documentation quality review
- [Reviews Index](index.md) - Complete list of all reviews

## Code References

- Workflow files: `.github/workflows/code-reviews.yml`
- Review specs: `.github/reviews/`
- PR check integration: `src/erk/cli/commands/pr/check_cmd.py`
