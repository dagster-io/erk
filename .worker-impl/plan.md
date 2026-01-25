# Fix Keyword-Only Parameter False Positives in Code Review

## Problem

The dignified-python code review outputs "informational" entries for functions that **already correctly use keyword-only parameters**. For example:

```
│ 1 │ Review │ impl_folder.py:122 │ Keyword-only parameter marker review - confirms current signature is correct │ Informational │ No action │
```

The function at line 122 has the `*` marker correctly:

```python
def save_issue_reference(
    impl_dir: Path,
    issue_number: int,
    issue_url: str,
    *,                           # ← line 122 - marker IS present
    issue_title: str | None,
    ...
) -> None:
```

The review correctly identifies the code is compliant but **still outputs an entry for it**. This creates noise in the review output.

## Root Cause

The review definition (`.github/reviews/dignified-python.md`) and prompt template (`src/erk/review/prompt_assembly.py`) don't explicitly tell Claude to **only output entries for violations** and skip compliant code.

The detection instructions say:
> Only flag as violation if there are 5+ parameters AND no `*` or `*,` line exists in the signature.

But there's no instruction saying "Do NOT mention code that passes this check."

## Solution

Update the review definition to explicitly instruct Claude to:
1. Only post inline comments for **violations**
2. Only include specific file:line references for **violations**
3. For compliant patterns, use aggregate language like "All functions compliant" without listing each file

## Files to Modify

1. **`.github/reviews/dignified-python.md`** - Add explicit instruction to skip compliant code

## Implementation

Add this clarification after line 70 (after the detection instructions):

```markdown
**IMPORTANT: Only output entries for VIOLATIONS.** Do NOT:
- Post inline comments for compliant code
- Include file:line references in the summary for compliant code
- Create "informational" or "review confirmed correct" entries

For compliant patterns, simply use "✅ [pattern] - All compliant" in the Patterns Checked section.
If a function has 5+ parameters AND has the `*` marker, skip it entirely - do not mention it.
```

## Verification

1. Run review on a PR with functions that have correct keyword-only parameters
2. Verify no "informational" entries appear for compliant functions
3. Verify actual violations are still detected and reported