---
title: Pre-Existing Test Failure Verification
read_when:
  - test failures appear during refactoring
  - uncertain if current changes broke tests
  - before major refactoring work
tripwires:
  - action: "starting major refactoring on code with existing tests"
    warning: "Verify test status first with `git stash && pytest <path> && git stash pop`"
---

# Pre-Existing Test Failure Verification

Before attributing test failures to current changes, verify the test status on the clean codebase.

## Pattern

```bash
git stash && pytest <test-path> && git stash pop
```

This stashes current changes, runs tests against clean code, then restores changes.

## When to Use

- Test failures appear during refactoring
- Unsure if failure is from your changes or pre-existing
- Before starting major refactoring (baseline verification)

## Example from PR #7135

The implementation session encountered `test_check_version_mismatch_does_not_show_artifacts` failure. The agent used the stash pattern to verify it failed on clean master - the test was pre-existing broken (doesn't patch `get_bundled_*` functions). The agent correctly excluded it from the test run rather than attempting to fix an out-of-scope issue.

## Benefits

- Prevents false blame attribution
- Avoids rabbit-hole fixes for unrelated issues
- Documents baseline test health
