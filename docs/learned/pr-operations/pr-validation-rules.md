---
title: PR Validation Rules
read_when:
  - "implementing PR validation checks"
  - "debugging 'erk pr check' failures"
  - "working with PR body footer validation"
  - "understanding issue closing reference requirements"
---

# PR Validation Rules

The `erk pr check` command validates that PRs follow required structural conventions. These rules ensure PRs are properly linked to issues and contain the necessary checkout command footer.

## Validation Functions

### 1. Checkout Footer Validation

**Function**: `has_checkout_footer_for_pr(body: str, pr_number: int) -> bool`

**Location**: `packages/erk-shared/src/erk_shared/gateway/pr/submit.py:25-38`

**Pattern**: Regex `rf"erk pr checkout {pr_number}\b"`

**Features**:

- Word boundary `\b` ensures exact PR number match (prevents false positives like PR #12 matching in "erk pr checkout 123")
- Case-sensitive matching (must be lowercase "erk pr checkout")
- More strict than `has_body_footer()` which only checks for presence, not PR number correctness

**Example valid footer**:

```
erk pr checkout 1234
```

### 2. Issue Closing Reference Validation

**Function**: `has_issue_closing_reference(body: str, issue_number: int, plans_repo: str | None) -> bool`

**Location**: `packages/erk-shared/src/erk_shared/gateway/pr/submit.py:41-60`

**Patterns**:

- **Same-repo**: `rf"Closes\s+#{issue_number}\b"` (when `plans_repo is None`)
- **Cross-repo**: `rf"Closes\s+{escaped_repo}#{issue_number}\b"` (when `plans_repo` is set)

**Features**:

- Case-insensitive matching via `re.IGNORECASE` flag
- Word boundary `\b` ensures exact issue number match
- Whitespace flexibility: `\s+` allows any amount of whitespace between "Closes" and the issue reference
- Cross-repo support: `plans_repo` is escaped to handle special regex characters in repo names

**Example valid references**:

Same-repo:

```
Closes #1234
```

Cross-repo:

```
Closes owner/repo#1234
```

## Validation Orchestration

The `pr_check()` command orchestrates these validations:

**Location**: `src/erk/cli/commands/pr/check_cmd.py`

**Workflow**:

1. Get current branch name
2. Look up PR for branch via GitHub API
3. Extract `pr_number` and `pr_body`
4. If `.impl/issue.json` exists:
   - Read issue number and plans repo from issue linkage
   - Validate issue closing reference is present
5. Validate checkout footer is present and correct
6. Report all validation results

## Common Validation Failures

### Missing Checkout Footer

**Error**: "PR body does not contain checkout command for PR #1234"

**Fix**: Add to end of PR body:

```
erk pr checkout 1234
```

### Missing Issue Closing Reference

**Error**: "PR body does not contain issue closing reference for #5678"

**Fix**: Add to PR body (typically near the top):

```
Closes #5678
```

For cross-repo issues:

```
Closes schrocknteam/erk-plans#5678
```

### Wrong PR Number in Footer

**Error**: PR body contains "erk pr checkout 999" but PR is #1234

**Fix**: This usually indicates copy-paste error. Update footer to match actual PR number.

## Common Mistakes

### PR Number vs Issue Number Confusion

**The Problem**: Agents sometimes confuse issue numbers with PR numbers when generating checkout footers.

**Why It Happens**: During plan-save workflow, `.impl/issue.json` contains the plan's issue number, which is easily accessible. However, the checkout footer requires the **PR number** (from `gh pr create` output), not the issue number.

**Example of Wrong Pattern**:

```python
# WRONG: Using issue number from .impl/issue.json
issue_data = json.loads(Path(".impl/issue.json").read_text())
checkout_footer = f"erk pr checkout {issue_data['issue_number']}"  # ❌
```

**Correct Pattern**:

```python
# RIGHT: Using PR number from gh pr create output
result = subprocess.run(["gh", "pr", "create", "--fill"], capture_output=True, text=True)
pr_url = result.stdout.strip()
pr_number = pr_url.split("/")[-1]
checkout_footer = f"erk pr checkout {pr_number}"  # ✅
```

**Key Distinction**:

| Source                | Usage                     | Valid For                     |
| --------------------- | ------------------------- | ----------------------------- |
| `.impl/issue.json`    | Issue number (plan issue) | `Closes #<issue>` reference   |
| `gh pr create` output | PR number                 | `erk pr checkout <pr>` footer |

**Why It Matters**: `gh pr checkout` only accepts PR numbers. Using an issue number will fail validation and prevent users from checking out the PR.

**See Also**: [Checkout Footer Syntax](checkout-footer-syntax.md) for detailed examples

## Resolution Pattern

When validation fails, use the grep-based resolution pattern documented in [Debugging Patterns](../planning/debugging-patterns.md):

1. Grep the codebase for the validation function name
2. Read the function implementation to understand the exact regex pattern
3. Test the regex against your PR body to identify the mismatch
4. Update the PR body to match the expected pattern

This pattern was discovered during the investigation of PR #6456 and demonstrates how to debug validation rules by understanding the underlying implementation.

## Related Documentation

- [PR Body Formatting](../architecture/pr-body-formatting.md) - Overall PR body structure
- [Plan Embedding in PR](plan-embedding-in-pr.md) - How plans are embedded in PR bodies
- [Debugging Patterns](../planning/debugging-patterns.md) - Grep-based validation debugging workflow
