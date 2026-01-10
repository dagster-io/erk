# Replan: Install-Test Guide Documentation

## Original Plan (#4517)

Create `docs/learned/testing/install-test.md` documenting the `erk-dev install-test` command.

## Current State

- **Already exists**: Comprehensive README at `dev/install-test/README.md` (165 lines)
- **Not created**: `docs/learned/testing/install-test.md` (the original plan target)
- **Issue status**: #4517 is open, implementation was started but appears incomplete

The existing README covers:
- Quick start guide
- Test scenarios (fresh, upgrade, repo-specific)
- Interactive shell helper functions
- Architecture diagram
- Adding test fixtures

## Recommendation: Lightweight Reference Doc

Rather than duplicating the README content, create a minimal learned-doc that:
1. Provides discoverability via frontmatter `read_when` conditions
2. Links to the authoritative README
3. Stays in sync automatically (single source of truth)

## Implementation Plan

### Step 1: Create `docs/learned/testing/install-test.md`

```markdown
---
title: "Install-Test Guide"
read_when:
  - "testing erk installation"
  - "testing upgrade scenarios"
  - "adding install-test fixtures"
  - "debugging installation issues"
  - "erk-dev install-test"
---

# Install-Test Guide

Docker-based testing for erk installation and upgrade scenarios.

**Full documentation**: [dev/install-test/README.md](../../../dev/install-test/README.md)

## Quick Reference

```bash
# Build image (one-time)
erk-dev install-test build

# Fresh install test
erk-dev install-test fresh

# Interactive shell
erk-dev install-test shell

# Test with repo fixture
erk-dev install-test repo dagster-compass
```

## When to Use

- Testing fresh erk installation on repos with existing `.erk/` config
- Testing upgrade paths from older versions
- Validating repo-specific configurations

See the [full README](../../../dev/install-test/README.md) for detailed workflows and fixture management.
```

### Step 2: Run `erk docs sync`

Regenerate the index to include the new document.

### Step 3: Close old issue #4517

Close with comment noting the simplified approach.

## Files to Modify

- `docs/learned/testing/install-test.md` (create)

## Verification

1. `erk docs validate` - check frontmatter
2. `erk docs sync` - regenerate index
3. Verify `install-test.md` appears in `docs/learned/testing/index.md`

## Cleanup

Close issue #4517 with comment:
> "Resolved with simplified approach: lightweight reference doc linking to existing README rather than duplicating content."