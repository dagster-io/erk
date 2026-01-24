---
title: Exec Script Flag Discovery
read_when:
  - "using erk exec commands"
  - "unsure what flags an exec command accepts"
---

# Exec Script Flag Discovery

## The Pattern

Always check available flags before assuming support:

```bash
erk exec <command> -h
```

## Why This Matters

Different exec commands have varied option sets:
- Not all support `--format json`
- Not all support `--verbose` or `--dry-run`
- Some have unique flags specific to their function

## Example

```bash
# Check what get-learn-sessions accepts
$ erk exec get-learn-sessions -h
Usage: erk exec get-learn-sessions [OPTIONS] ISSUE_NUMBER

Options:
  --format [json|text]  Output format
  -h, --help            Show this message and exit.
```

## Common Patterns

| Flag | Purpose | Availability |
|------|---------|--------------|
| `--format json` | Machine-readable output | Most commands |
| `-h, --help` | Show options | All commands |
| `--dry-run` | Preview without action | Mutation commands only |
| `--session-id` | Session tracking | Workflow commands |
