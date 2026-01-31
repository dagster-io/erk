---
title: Slash Command to Exec Migration
read_when:
  - "migrating slash commands to use erk exec"
  - "extracting manual logic from commands into exec scripts"
  - "understanding the exec command extraction pattern"
tripwires:
  - action: "adding inline shell logic to a slash command instead of using erk exec"
    warning: "Extract reusable logic to an erk exec command. Slash commands should orchestrate exec calls, not contain business logic."
---

# Slash Command to Exec Migration

A 3-phase pattern for migrating inline logic from slash commands (`.claude/commands/`) into reusable `erk exec` scripts.

## Why Migrate

Slash commands run in Claude's context and contain raw shell logic. Extracting to `erk exec`:

- Makes logic testable (Python with proper error handling)
- Enables reuse across multiple commands
- Provides structured JSON output for programmatic consumption
- Follows the gateway pattern (exec scripts use gateways, not raw subprocess)

## The 3-Phase Pattern

### Phase 1: Identify Manual Logic

Find inline shell commands in `.claude/commands/` that:

- Call `gh` or `git` directly
- Parse JSON with `jq`
- Contain conditional logic based on command output
- Duplicate logic already in exec scripts

### Phase 2: Extract to Exec Script

Create a new script in `src/erk/cli/commands/exec/scripts/`:

1. Define frozen dataclass success/error types
2. Implement the logic using gateway abstractions
3. Register the command with Click
4. Add `--format json` support if callers need structured output

### Phase 3: Migrate Command

Replace the inline shell logic with `erk exec` calls:

```markdown
<!-- Before -->

Run: gh issue view 123 --json body -q .body

<!-- After -->

Run: erk exec get-issue-body 123
```

## Reference: PR #6328

PR #6328 (commit `b81e71d5e`) migrated slash commands to use roadmap exec commands:

- Replaced inline `gh api` calls with `erk exec objective-roadmap-check`
- Replaced manual JSON parsing with structured exec output
- Preserved command behavior while improving testability

## Related Documentation

- [erk exec Commands](erk-exec-commands.md) — Available exec commands and their syntax
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — Exec command error patterns
