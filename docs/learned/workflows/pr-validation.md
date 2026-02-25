---
title: Post-PR Validation Checklist
read_when:
  - "verifying a PR after implementation"
  - "reviewing documentation synchronization after merging"
  - "distinguishing flaky CI failures from real failures"
tripwires:
  - action: "merging a PR without verifying documentation matches code changes"
    warning: "Check that any new patterns, commands, or architectural decisions are documented in docs/learned/. Run erk docs sync after adding new docs."
    score: 4
---

# Post-PR Validation Checklist

After implementing a plan and before merging, verify these invariants.

## Structural Checks

Run `erk pr check` to validate PR structure:

1. **Checkout footer present** with correct PR number
2. **Issue closing reference** (`Closes #N`) for issue-based plans
3. **Plan-header metadata** at correct position (not legacy top)

With `--stage=impl`, also verify:

4. **`.erk/impl-context/` cleaned up** (no staging artifacts)

## Documentation Synchronization

After code changes land, verify documentation matches:

| Check                                       | How to Verify                          |
| ------------------------------------------- | -------------------------------------- |
| New patterns documented                     | Grep `docs/learned/` for related terms |
| Frontmatter `read_when` conditions accurate | Review each modified doc's frontmatter |
| Tripwires added for dangerous patterns      | Check category `tripwires.md` files    |
| Cross-references valid                      | Run `make fast-ci` for link validation |

## Transient CI Failure Detection

When CI fails, distinguish flaky tests from real failures:

1. **Check if the test failed on this PR's changes** - Does the failing test relate to modified code?
2. **Check CI on master** - Is the same test failing there?
3. **Re-run once** - Transient failures (network timeouts, race conditions) resolve on retry
4. **If still failing** - Investigate as a real regression

Common transient failure sources:

- GitHub API rate limiting
- Network timeouts in integration tests
- Race conditions in async test setup

## Test Coverage Verification

For code changes:

1. Verify new functions have corresponding tests
2. Check that modified behavior has updated test expectations
3. Run the specific test file to confirm passage

## Related Topics

- [PR Validation Rules](../pr-operations/pr-validation-rules.md) - Structural validation details
- [erk exec Commands](../cli/erk-exec-commands.md) - `erk pr check` reference
