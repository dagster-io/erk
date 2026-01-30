---
title: Inline Comment Deduplication
read_when:
  - "working with PR inline review comments"
  - "understanding how duplicate comments are prevented"
  - "modifying review prompt assembly"
tripwires:
  - action: "posting inline review comments without deduplication"
    warning: "Always deduplicate before posting. Use (path, line, body_prefix) key with 80-char prefix and 2-line proximity tolerance."
---

# Inline Comment Deduplication

When posting inline review comments to a PR, the system deduplicates to prevent posting the same comment multiple times across review iterations.

## Algorithm

### Deduplication Key

Each comment is uniquely identified by a tuple:

```
(file_path, line_number, body_prefix)
```

Where `body_prefix` is the first **80 characters** of the comment body.

### Proximity Tolerance

Line numbers are matched with a **2-line tolerance** to account for diff shifts between review iterations. A comment at line 42 is considered a duplicate of an existing comment at lines 40–44 with the same path and body prefix.

### Process

1. Fetch existing review comments on the PR
2. Build a set of `(path, line, body_prefix)` keys from existing comments
3. For each new comment to post:
   - Compute its key
   - Check for matches within the 2-line proximity window
   - Skip posting if a match exists

## Why 80 Characters

The 80-character prefix balances two concerns:

- **Too short**: Different comments with the same opening would be incorrectly deduplicated
- **Too long**: Minor rephrasing would cause duplicates to be posted

80 characters captures enough of the comment's intent to reliably detect duplicates while tolerating minor wording changes.

## Reference Implementation

The deduplication logic is embedded in the review prompt template at `src/erk/review/prompt_assembly.py` (Step 4 in the template instructions).

## Related Documentation

- [Prompt Assembly](prompt-assembly.md) — Two-mode prompt system that includes deduplication instructions
- [PR Operations Skill](../../.claude/skills/pr-operations/SKILL.md) — Commands for posting and resolving review comments
