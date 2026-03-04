# Fix PR body section order and "Files Changed" header

## Context

PR review feedback: "Key Changes" should come before "Files Changed", and "Files Changed" should be the toggle list without the header (i.e., no `## Files Changed` heading — just the `<details>` element directly).

Currently the prompt template produces:
1. Summary
2. `## Files Changed` header + `<details>` toggle (duplicate header)
3. `## Key Changes`

Desired output:
1. Summary
2. `## Key Changes`
3. `<details>` toggle (no `## Files Changed` heading above it)

## Change

**File:** `packages/erk-shared/src/erk_shared/gateway/gt/commit_message_prompt.md`

In the `## Output Format` block:
1. Move `## Key Changes` section **before** the Files Changed block
2. Remove the `## Files Changed` heading, keeping only the `<details>...</details>` block

Result:

```
[Clear one-line PR title describing the change]

[2-3 sentence summary explaining what changed and why.]

## Key Changes

- [3-5 high-level component/architectural changes]
- ...

<details>
<summary>Files Changed</summary>

### Added (N files)
...

### Modified (N files)
...

### Deleted (N files)
...

</details>

## User Experience
...

## Critical Notes
...
```

## Verification

Generate a new PR description (via `erk pr submit` or `erk pr rewrite` on a branch with changes) and confirm:
- "Key Changes" section appears above the Files Changed toggle
- No `## Files Changed` heading above the `<details>` element
- Toggle still works and shows file lists correctly
