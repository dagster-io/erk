# Minor Update to README.md

## Context

This is a minor documentation update to the root `README.md`. The goal is to improve clarity in the Quick Start section by adding a brief note about what `erk doctor` checks, so new users understand the value of running it.

## Changes

### `README.md`

In the Quick Start section, update the inline comment for `erk doctor` from:

```
# Verify setup
erk doctor
```

to:

```
# Verify setup (checks prerequisites and configuration)
erk doctor
```

This is a single-line change that makes the comment more descriptive for new users scanning the quick start instructions.

## Files NOT Changing

- No source code changes
- No test changes
- No configuration changes
- No other documentation files

## Implementation Details

- Edit line 21 of `README.md`
- Change `# Verify setup` to `# Verify setup (checks prerequisites and configuration)`
- This is a cosmetic/documentation-only change

## Verification

1. Confirm the README.md renders correctly (the change is within a fenced code block)
2. No tests to run — this is a documentation-only change