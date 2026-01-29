---
title: Testing Tripwires
read_when:
  - "working on testing code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from testing/*.md frontmatter -->

# Testing Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before accessing FakeGit properties in tests** → Read [Erk Test Reference](testing.md) first. Access properties via subgateway (e.g., `git.commit_ops.staged_files`), not top-level.

**CRITICAL: Before asking devrun agent to fix errors or make tests pass** → Read [Devrun Agent - Read-Only Design](devrun-agent.md) first. Devrun is READ-ONLY. It runs commands and reports results. The parent agent must handle all fixes.

**CRITICAL: Before implementing interactive prompts with ctx.console.confirm()** → Read [Erk Test Reference](testing.md) first. Ensure FakeConsole in test fixture is configured with `confirm_responses` parameter. See tests/commands/submit/test_existing_branch_detection.py for examples.

**CRITICAL: Before modifying business logic in src/ without adding a test** → Read [Erk Test Reference](testing.md) first. Bug fixes require regression tests (fails before, passes after). Features require behavior tests.

**CRITICAL: Before testing code that reads from Path.home() or ~/.claude/ or ~/.erk/** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Tests that run in parallel must use monkeypatch to isolate from real filesystem state. Functions like extract_slugs_from_session() cause flakiness when they read from the user's home directory.

**CRITICAL: Before using Path.home() directly in production code** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use gateway abstractions instead. For ~/.claude/ paths use ClaudeInstallation, for ~/.erk/ paths use ErkInstallation. Direct Path.home() access bypasses testability (fakes) and creates parallel test flakiness.

**CRITICAL: Before using monkeypatch.chdir() in exec script tests** → Read [Exec Script Testing Patterns](exec-script-testing.md) first. Use obj=ErkContext.for_test(cwd=tmp_path) instead. monkeypatch.chdir() doesn't inject context, causing 'Context not initialized' errors.
