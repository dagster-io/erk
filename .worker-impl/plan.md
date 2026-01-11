# Plan: Clarify Default Parameter Rule in dignified-python Skill

## Overview

Add a scope clarification to the "Default Parameter Values Are Dangerous" section in the dignified-python skill. This prevents false positives where the CI bot incorrectly flags function **calls** like `user_confirm("Close the PR?", default=True)` as violations, when the rule only applies to function **definitions**.

## Background

The rule "avoid default parameter values" applies to:
- ✅ `def foo(bar: bool = False)` - Function DEFINITION with default value (BAD)

The rule does NOT apply to:
- ✅ `click.confirm(default=True)` - Function CALL passing a named argument (OK)

## Implementation Steps

### Step 1: Add scope clarification blockquote

**File:** `.claude/skills/dignified-python/dignified-python-core.md`

Find the section "### Default Parameter Values Are Dangerous" and add a blockquote immediately after the heading:

```markdown
### Default Parameter Values Are Dangerous

> **Scope:** This rule applies to **function definitions** (`def foo(bar: bool = False)`),
> NOT to **function calls** where you pass an argument named `default` (e.g.,
> `click.confirm(default=True)`). Passing `default=True` to a function that accepts
> a `default` parameter is perfectly valid—you're not creating a default parameter value,
> you're explicitly providing a value.

**Avoid default parameter values unless absolutely necessary.** They are a significant source of bugs.
```

## Files to Modify

| File | Change |
|------|--------|
| `.claude/skills/dignified-python/dignified-python-core.md` | Add scope clarification blockquote |

## Verification

1. Read the file to confirm the blockquote is in place
2. Run prettier via devrun: `prettier --check .claude/skills/dignified-python/`
3. Verify the clarification appears after the section heading