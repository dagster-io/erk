---
title: PR Body Section Ordering
category: pr-operations
read_when:
  - "modifying PR body format"
  - "commit message template"
  - "section ordering in PR descriptions"
last_audited: "2026-03-05 00:00 PT"
audit_result: clean
---

# PR Body Section Ordering

PR descriptions follow a fixed section order designed to present strategic impact before implementation details.

## Current Section Order

1. **One-line title**
2. **Summary** (2-3 sentences)
3. **Key Changes** (3-5 bullet items)
4. **Files Changed** (collapsible `<details>` block with Added/Modified/Deleted subsections)
5. **User Experience** (optional — for UI/CLI changes)
6. **Critical Notes** (optional — for breaking changes)

The rationale: reviewers see strategic impact (Key Changes) before implementation details (Files Changed). The collapsible `<details>` block keeps the file list from dominating the PR view.

## Template Locations

Two files define this format and must stay synchronized:

<!-- Source: .claude/skills/erk-diff-analysis/references/commit-message-prompt.md -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md -->

- `.claude/skills/erk-diff-analysis/references/commit-message-prompt.md` — used by Claude Code diff analysis skill
- `packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md` — used by the Graphite commit message generator

Both files are identical. Changes to one must be mirrored to the other. See [Template Synchronization](../architecture/template-synchronization.md) for the synchronization pattern.

## Rendering Note

The `<details>` HTML tag renders as a collapsible section on GitHub but appears as raw HTML in git commit messages (e.g., `git log`). This is acceptable — the primary audience for the full PR body is GitHub reviewers.

## Related Topics

- [PR Submit Phases](pr-submit-phases.md) - PR creation workflow
- [Resubmission Workflows](resubmission-workflows.md) - How PR bodies are updated on resubmission
