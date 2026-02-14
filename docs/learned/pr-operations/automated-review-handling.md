---
title: Automated Review Handling
read_when:
  - "investigating automated bot complaints on PRs"
  - "handling prettier or linting bot review comments"
  - "deciding whether to fix or dismiss automated review feedback"
tripwires:
  - action: "investigating an automated reviewer complaint"
    warning: "Determine if the tool is the authority for that concern. For formatting, prettier is the authority — if prettier passes, dismiss the bot. For type errors, ty is the authority."
---

# Automated Review Handling

PRs may receive automated review comments from bots (linters, formatters, security scanners). This document provides a workflow for investigating and resolving these comments.

## Investigation Workflow

When a bot flags an issue:

1. **Identify the authority**: Which tool is the definitive source of truth for this concern?
2. **Run the authority locally**: Does the authoritative tool agree with the bot?
3. **Decide**: Fix (if authority agrees) or dismiss (if authority disagrees)

## Authority Hierarchy

| Concern           | Authority Tool           | Action if Authority Passes |
| ----------------- | ------------------------ | -------------------------- |
| Code formatting   | prettier                 | Dismiss bot complaint      |
| Python formatting | ruff format              | Dismiss bot complaint      |
| Python linting    | ruff check               | Dismiss bot complaint      |
| Type errors       | ty                       | Dismiss bot complaint      |
| Security issues   | Investigate individually | Fix or document exception  |

## Common Scenario: Prettier vs Bot

Prettier is the formatting authority for markdown, YAML, JSON, and TypeScript files. If `prettier --check` passes but a bot complains about formatting:

1. Run `prettier --check <file>` locally
2. If prettier passes, the bot is using different rules — dismiss
3. If prettier fails, fix with `prettier --write <file>`

## When to Dismiss vs Fix

**Dismiss** when:

- The authoritative tool passes
- The bot is using outdated or different rules
- The complaint is cosmetic and contradicts project standards

**Fix** when:

- The authoritative tool also flags the issue
- The complaint identifies a genuine bug or security concern
- The fix aligns with project standards

## Related Documentation

- [CI Workflow Patterns](../ci/) — CI check configuration and debugging
