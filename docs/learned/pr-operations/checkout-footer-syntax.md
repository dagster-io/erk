---
title: Checkout Footer Syntax
read_when:
  - writing PR body checkout footer, implementing plan-save workflow, debugging PR validation failures
tripwires:
  - action: "writing checkout footer with issue number from .impl/issue.json"
    warning: "Use PR number (from gh pr create), NOT issue number (from .impl/issue.json). Checkout command expects PR number format: 'gh pr checkout <pr-number>'. Issue numbers in checkout footers cause validation errors."
---

# Checkout Footer Syntax

Erk PR bodies include a checkout footer for easy local testing:

```markdown
---

_Checkout this PR:_ `gh pr checkout 123`
```

## Critical Distinction: PR Number vs Issue Number

**MUST use PR number**, not issue number:

| Source                | Correct Usage                    | Why                                 |
| --------------------- | -------------------------------- | ----------------------------------- |
| `gh pr create` output | ✅ Extract PR number from URL    | `gh pr checkout` requires PR number |
| `.impl/issue.json`    | ❌ Never use for checkout footer | Issue number ≠ PR number            |

## Common Mistake Pattern

During plan-save workflow, agents sometimes confuse the two:

```python
# WRONG: Using issue number from .impl/issue.json
issue_data = json.loads(Path(".impl/issue.json").read_text())
footer = f"gh pr checkout {issue_data['issue_number']}"

# RIGHT: Using PR number from gh pr create
pr_url = subprocess.check_output(["gh", "pr", "create", ...])
pr_number = pr_url.strip().split("/")[-1]
footer = f"gh pr checkout {pr_number}"
```

## Why This Matters

`gh pr checkout` accepts only PR numbers:

- ✅ `gh pr checkout 6500` — works (PR number)
- ❌ `gh pr checkout 6491` — fails if 6491 is an issue, not a PR
- ❌ `gh pr checkout #6500` — fails (no `#` prefix)

## Validation Rule

The `erk pr check` command validates checkout footer syntax:

- Regex: `gh pr checkout (\d+)`
- Extracts number from footer
- Verifies it matches actual PR number from `gh pr view`

## Related Documentation

- [PR Validation Rules](pr-validation-rules.md) — Complete validation ruleset
