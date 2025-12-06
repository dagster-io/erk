---
title: gh CLI Patterns
read_when:
  - "adding new gh CLI commands"
  - "using gh api with placeholders"
  - "filtering gh CLI output with jq"
---

# gh CLI Patterns

## Placeholder Auto-Substitution

The gh CLI automatically substitutes `{owner}` and `{repo}` from the current repository context:

```python
# These are LITERAL strings - gh substitutes them automatically
cmd = ["gh", "api", "repos/{owner}/{repo}/issues/123"]
```

In Python, escape the braces for f-strings:

```python
# Correct: double braces escape in f-string
cmd = ["gh", "api", f"repos/{{owner}}/{{repo}}/issues/{number}"]

# Wrong: would try to use Python variables named owner/repo
cmd = ["gh", "api", f"repos/{owner}/{repo}/issues/{number}"]
```

## REST API Endpoints

Common patterns used in erk:

```python
# Get single issue
f"repos/{{owner}}/{{repo}}/issues/{number}"

# Get issue comments
f"repos/{{owner}}/{{repo}}/issues/{number}/comments"

# Get issue timeline (for PR references)
f"repos/{{owner}}/{{repo}}/issues/{number}/timeline"
```

## Using --jq for Response Filtering

```python
cmd = [
    "gh", "api",
    f"repos/{{owner}}/{{repo}}/issues/{number}/comments",
    "--jq", "[.[].body]",  # Extract just comment bodies as JSON array
]
```
