# Plan: Update learn command confirmation prompt

## Change

Update the confirmation prompt in `src/erk/cli/commands/learn/learn_cmd.py` line 227:

**From:**
```
Launch Claude to extract insights from these sessions?
```

**To:**
```
Use Claude to learn from these sessions and produce documentation in docs/learned?
```

(Note: Fixed typo "documention" → "documentation", capitalized "Claude")

## Verification

Run `erk learn <issue>` and confirm the new prompt appears.