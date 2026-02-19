---
title: Command Availability Documentation Patterns
read_when:
  - "documenting TUI command availability"
  - "updating action-inventory.md"
  - "adding new commands to command registry"
tripwires:
  - action: "listing command counts in prose"
    warning: "Avoid writing 'Six commands require...' - list them and let the count speak for itself. Counts drift as commands are added."
  - action: "copying verbatim predicate code into docs"
    warning: "Use source pointers instead. Predicate implementations change; copied code drifts silently."
  - action: "grouping commands by human intuition rather than actual predicate"
    warning: "Group commands by their is_available predicate, not by conceptual similarity. Commands with same availability predicate go together."
---

# Command Availability Documentation Patterns

## Problem

PR #7473 review revealed 5 documentation drift instances related to command availability tables. Common issues:

- Commands missing from predicate-based tiers
- Commands grouped under wrong predicates
- Command counts that don't match implementation

## Audit Procedure

When updating command availability documentation:

1. **Extract from source:** Grep `registry.py` for all command registrations. See `CommandDef` class in `src/erk/tui/commands/registry.py`
2. **Group by predicate type:** Commands with same availability predicate go together
3. **Verify counts:** Don't write "Six commands" - list them and let the count speak for itself
4. **Use source pointers:** For complex predicates, point to `registry.py` instead of copying code

## Predicate-Based Grouping Rules

Group commands by their `is_available` predicate, not by conceptual similarity:

- "Needs PR" tier: commands with `pr_url is not None` predicate
- "Needs worktree" tier: commands with `worktree_branch is not None` predicate
- Do NOT mix predicates even if commands seem related

## Anti-Patterns

- Listing command counts in prose ("Six commands require...")
- Copying verbatim predicate code into docs (it drifts)
- Grouping by human intuition rather than actual predicate
