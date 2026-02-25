---
title: Post-Refactoring Documentation Audit
read_when:
  - "completing a refactoring that renames or removes commands, classes, or functions"
  - "reviewing a PR that deletes or renames code"
  - "cleaning up after a large rename or deletion"
tripwires:
  - action: "completing a refactoring without searching docs/learned/ for stale references"
    warning: "64% of review violations come from stale documentation after refactoring. Run the 5-step checklist in post-refactor-documentation-audit.md before marking the task complete."
---

# Post-Refactoring Documentation Audit

After any refactoring that renames or removes commands, classes, functions, or concepts, run this 5-step checklist to prevent stale documentation from misleading agents.

## Why This Matters

64% of PR review violations in erk originate from stale documentation. Agents read docs/learned/ before writing code — stale references cause them to use deleted APIs, reference removed commands, or follow obsolete patterns.

## 5-Step Checklist

### Step 1: Grep docs/learned/ for old names

```bash
grep -r "OldClassName\|old_function_name\|old-command-name" docs/learned/
```

Replace or remove every match.

### Step 2: Verify command references

```bash
grep -r "erk old-command" docs/learned/
```

Update to new command paths (e.g., `erk plan submit` → `erk pr dispatch`).

### Step 3: Check tripwire entries

Search tripwire frontmatter for references to renamed/removed items:

```bash
grep -r "OldName" docs/learned/*/tripwires.md
```

Note: tripwires.md files are auto-generated — edit the source doc frontmatter instead.

### Step 4: Update glossary

Check if the old term appears in the glossary:

```bash
grep -r "OldTerm" docs/learned/glossary.md
```

Update or remove the entry.

### Step 5: Run erk docs sync

```bash
erk docs sync
```

This regenerates index files and tripwire aggregations from updated frontmatter.

## When to Apply

Apply this checklist after:

- Deleting a CLI command or command group
- Renaming a class, function, or module
- Removing an ABC or gateway
- Consolidating features (merging two things into one)
- Removing a feature entirely

## Related Documentation

- [Feature Removal Checklist](feature-removal-checklist.md) — Complete feature removal process
- [Systematic Rename Checklist](systematic-rename-checklist.md) — Renaming patterns
