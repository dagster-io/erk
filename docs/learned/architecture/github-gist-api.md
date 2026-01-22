---
title: GitHub Gist URL Patterns
read_when:
  - "constructing gist raw URLs"
  - "downloading gist content programmatically"
  - "working with single-file gists"
tripwires:
  - action: "constructing gist raw URLs with hardcoded filenames"
    warning: "Use /raw/ without filename - GitHub redirects to first file."
---

# GitHub Gist URL Patterns

URL construction patterns for accessing GitHub Gist content.

## Raw Content Access

GitHub Gist provides multiple URL patterns for accessing raw file content.

### URL Patterns

| Endpoint Pattern                                                | Behavior                                           |
| --------------------------------------------------------------- | -------------------------------------------------- |
| `gist.githubusercontent.com/{user}/{gist_id}/raw/`              | Redirects (302) to first file in single-file gists |
| `gist.githubusercontent.com/{user}/{gist_id}/raw/{filename}`    | Returns 404 if filename doesn't match exactly      |
| `gist.githubusercontent.com/{user}/{gist_id}/raw/{rev}/{fname}` | Version-specific raw content                       |

### Recommended Pattern

For single-file gists where the filename may vary, use `/raw/` without specifying the filename:

```python
# Robust: GitHub redirects to first (and only) file
raw_url = f"https://gist.githubusercontent.com/{user}/{gist_id}/raw/"

# Brittle: 404 if filename doesn't match exactly
raw_url = f"https://gist.githubusercontent.com/{user}/{gist_id}/raw/session.jsonl"
```

### Why Use /raw/ Without Filename?

1. **Resilient to upload variations**: If gist creation produces unexpected filenames (e.g., temp file prefixes), download still works
2. **Simpler code**: No need to track or store the exact filename used during upload
3. **GitHub handles redirect**: 302 redirect to actual file is transparent to most HTTP clients

### Multi-File Gists

For gists with multiple files, you must specify the filename:

- List files first via GitHub API: `gh api gists/{gist_id} --jq '.files | keys'`
- Then access specific file by exact name

## Related Topics

- [GitHub CLI Quirks](github-cli-quirks.md) - gh gist create --filename behavior
- [GitHub API Rate Limits](github-api-rate-limits.md) - Rate limiting considerations
