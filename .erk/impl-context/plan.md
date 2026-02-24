# Plan: Strengthen ternary acceptance in coding standards

## Context

The dignified-code-simplifier review bot flagged `main_repo_root = repo.main_repo_root if repo.main_repo_root else repo.root` suggesting it be replaced with `.or_else` pattern. This is wrong:
- `.or_else()` isn't a Python method (it's Rust/Kotlin)
- Simple one-line ternaries are idiomatic Python and often preferable to avoid unnecessary variable assignment
- The skill already says simple ternaries are acceptable (line 32), but it's not emphatic enough

## Changes

### 1. `.claude/skills/dignified-code-simplifier/SKILL.md`

Strengthen the ternary guidance in the "Enhance Clarity" section (lines 31-32). Replace:

```
- IMPORTANT: Avoid **nested** ternary operators (ternaries inside ternaries) - prefer if/else chains for multiple conditions
- Simple single-level ternaries are idiomatic and acceptable: `slug = branch_slug if branch_slug else fallback()`, `x = a if condition else b`
```

With:

```
- IMPORTANT: Avoid **nested** ternary operators (ternaries inside ternaries) - prefer if/else chains for multiple conditions
- Simple single-level ternaries are idiomatic, acceptable, and often **preferable** to avoid unnecessary variable assignment or multi-line if/else blocks. Do NOT suggest replacing them. Examples: `slug = branch_slug if branch_slug else fallback()`, `x = a if condition else b`, `root = obj.primary if obj.primary else obj.fallback`
- NEVER suggest `.or_else()` or similar non-Python patterns as alternatives to ternaries
```

### 2. `.claude/skills/dignified-python/dignified-python-core.md`

Add a new subsection after "Don't Destructure Objects Into Single-Use Locals" (after line 323):

```markdown
### Simple Ternaries Are Preferred

Simple one-line ternary expressions are idiomatic and often preferable to multi-line if/else:

```python
# CORRECT: Simple ternary - clear and concise
root = repo.main_root if repo.main_root else repo.root
label = name if name else "unknown"

# ALSO CORRECT: `or` for falsy fallback (when semantics match)
root = repo.main_root or repo.root

# WRONG: Unnecessary multi-line expansion of a simple conditional
if repo.main_root:
    root = repo.main_root
else:
    root = repo.root
```

Only avoid ternaries when they are **nested** (ternary inside ternary) or span multiple lines.
```

## Verification

- Read both files after editing to confirm changes are correct
- Run `/local:py-fast-ci` to check nothing is broken
