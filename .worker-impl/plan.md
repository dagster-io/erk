# Fix help text formatting for `erk init capability remove`

## Problem
Click collapses the indented examples in the docstring into a single line.

## Solution
Add `\b` before the Examples block in the docstring. This is Click's escape marker that tells it to preserve the following paragraph's formatting verbatim.

## File to modify
`src/erk/cli/commands/init/capability/remove_cmd.py:24`

Change the docstring from:
```
    Examples:
        erk init capability remove dignified-python
```
to:
```
    \b
    Examples:
        erk init capability remove dignified-python
```

## Verification
Run `erk init capability remove -h` and confirm examples appear on separate lines.