---
title: Command Rename Pattern
read_when:
  - "renaming a slash command"
  - "migrating command invocations"
  - "ensuring complete command name updates"
last_audited: "2026-02-05 20:38 PT"
audit_result: clean
---

# Command Rename Pattern

This document describes the systematic workflow for renaming slash commands in Claude Code, ensuring all references are updated and no stale invocations remain.

## Workflow

### 1. Read Old Command

Before making any changes, read the old command file to understand:

- Command purpose and behavior
- Parameter structure
- External dependencies (skills, docs)
- Related commands

```bash
# Example
cat .claude/commands/erk-pr-address-remote.md
```

### 2. Create New Command

Create the new command file with the updated name:

- Copy content from old command
- Update the command name in frontmatter and body text
- Adjust invocation examples to use new name
- Update any self-referential documentation

```bash
# Example
cp .claude/commands/erk-pr-address-remote.md .claude/commands/erk-pr-address.md
# Edit .claude/commands/erk-pr-address.md to update references
```

### 3. Delete Old Command

Remove the old command file after verifying the new one is complete:

```bash
rm .claude/commands/erk-pr-address-remote.md
```

### 4. Verify References

Use grep to find all references to the old command name across the codebase:

```bash
# Check for slash command invocations
grep -r "/erk:pr-address-remote" .

# Check for command mentions in documentation
grep -r "erk:pr-address-remote" docs/

# Check for related terminology
grep -r "pr-address-remote" .
```

### 5. Update All References

Update found references in three categories:

#### A. Command Invocations

Update all actual uses of the command:

```markdown
<!-- OLD -->

/erk:pr-address-remote

<!-- NEW -->

/erk:pr-address
```

#### B. Body Text and Documentation

Update descriptive text that mentions the command:

```markdown
<!-- OLD -->

The `/erk:pr-address-remote` command triggers...

<!-- NEW -->

The `/erk:pr-address` command triggers...
```

#### C. External References

Update references in:

- Other command files that reference this command
- Documentation files in `docs/learned/`
- README and AGENTS.md files
- Hook configurations

### 6. Run CI

Verify the rename doesn't break tests or documentation builds:

```bash
# Run tests
pytest tests/

# Verify command loads
erk --help

# Check for broken links in docs
erk docs sync
```

## Quality Checklist

Use this checklist to ensure complete migration:

- [ ] Old command file deleted
- [ ] New command file created with correct name
- [ ] All slash command invocations updated (`/command-name`)
- [ ] All command mentions in documentation updated
- [ ] Cross-references from other commands updated
- [ ] Hook configurations updated if command is hooked
- [ ] CLI help text updated if command is exposed
- [ ] No grep results for old command name (excluding CHANGELOG)
- [ ] CI passes
- [ ] Documentation index regenerated (`erk docs sync`)

## Anti-Pattern: Mechanical Rename Without Terminology Update

**Problem:** Issue #6410 renamed `/local:todos-clear` to `/local:tasks-clear` but only updated the command invocation, not the terminology throughout the body text and documentation.

**Symptoms:**

- Command file renamed
- Invocations updated
- Body text still references "todos" instead of "tasks"
- User-facing messages inconsistent
- Conceptual confusion between "todos" and "tasks"

**Correct approach:**

When renaming a command that represents a terminology shift (like "todos" → "tasks"):

1. Update command name
2. Update all body text to use new terminology
3. Update user-facing messages and output
4. Update related documentation
5. Update variable names in implementation if applicable
6. Create a terminology mapping in glossary if needed

**Example from #6412:**

```diff
- /local:todos-clear - Clear all todos from the current session
+ /local:tasks-clear - Clear all tasks from the current session

- This command clears the todo list for the current session.
+ This command clears the task list for the current session.

- When would you use this? Todos might become stale...
+ When would you use this? Tasks might become stale...
```

## Grep Verification Patterns

Use these patterns to verify completeness:

```bash
# Command invocations (with colon)
grep -r "/old-command-name" .

# Command references (without slash)
grep -r "old-command-name" docs/

# Kebab and snake variants
grep -r "old_command_name\|old-command-name" .

# Exclude false positives
grep -r "old-command-name" . | grep -v CHANGELOG | grep -v ".git/"
```

## Related Documentation

- [Command Development](command-development.md) - Creating new commands
- [Slash Command Best Practices](slash-command-best-practices.md) - Command design patterns
- [Documentation Maintenance](../documentation/maintenance.md) - Keeping docs in sync
