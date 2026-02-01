---
title: Metadata Block Fallback
read_when:
  - "fetching plan content from GitHub issues"
  - "debugging 'no plan content found' errors"
  - "working with older erk-plan issues"
  - "implementing plan content extraction"
---

# Metadata Block Fallback

When fetching plan content from GitHub issues, use a two-location fallback pattern to handle both current and legacy issue formats.

## The Pattern

**Primary**: Look for plan content in the **first comment** (issue body metadata block)

**Fallback**: Check the **issue body directly**

This handles both:

- **Current format**: Plan content stored in first comment with metadata block markers
- **Legacy format**: Plan content embedded directly in issue body (older issues)

## Implementation

From `.claude/commands/erk/replan.md` Step 4a:

```markdown
Fetch plan content using:
erk exec get-plan-content <issue-number>

This command:

1. First tries to extract plan from metadata block in first comment
2. Falls back to issue body if no metadata block found
3. Returns extracted plan content
```

The `get-plan-content` exec script handles the fallback internally.

## Why Fallback is Needed

### Issue Evolution

Erk's issue format has evolved:

**Early format** (pre-metadata blocks):

```markdown
# Issue Title

## Plan

Implementation plan content here...
```

**Current format** (with metadata blocks):

```markdown
# Issue Title

Summary here...

---

<!-- Comment 1 contains: -->
<!-- erk:metadata-block:plan-body -->

# Plan

Implementation plan content here...

<!-- /erk:metadata-block:plan-body -->
```

### Legacy Issue Support

Older issues like #6431 still use the legacy format. Without fallback, these issues would be inaccessible to replan workflows.

## Agent Pattern

When implementing plan content extraction:

1. **Always try both locations** before reporting "no plan content found"
2. **Primary first**: Check metadata block in first comment (faster, more precise)
3. **Fallback second**: Check issue body (handles legacy issues)
4. **Error only if both fail**: Report "no plan content found" only after both attempts

**Anti-pattern**: Only checking one location and failing immediately

## Metadata Block Format

The metadata block uses HTML comment markers:

```html
<!-- erk:metadata-block:plan-body -->
[plan content here]
<!-- /erk:metadata-block:plan-body -->
```

**Location**: First comment on the issue (not the issue body itself)

**Why comments**: GitHub automatically creates first comment when issue is created, providing a stable location separate from the user-editable issue body.

## Error Handling

### Case 1: Both Locations Empty

```
Error: Issue #<number> has no plan content.
Check that the issue contains either:
1. A metadata block in the first comment, or
2. Plan content in the issue body
```

### Case 2: Malformed Metadata Block

If metadata block markers exist but are incomplete:

```
Warning: Metadata block markers found but content extraction failed.
Falling back to issue body...
```

### Case 3: Successful Fallback

When fallback succeeds, no warning is needed. The agent proceeds normally with the extracted content.

## Verification

Test both paths:

```bash
# Modern issue with metadata block
erk exec get-plan-content 6455

# Legacy issue without metadata block
erk exec get-plan-content 6431
```

Both should succeed without errors.

## Related Documentation

- [Replan Command](.claude/commands/erk/replan.md) - Full workflow using this pattern
- [Plan Content Storage](plan-content-storage.md) - Where plan content lives
