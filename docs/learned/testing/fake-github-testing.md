---
title: FakeGitHubIssues Testing Patterns
category: testing
read_when: Writing tests that use FakeGitHubIssues
---

# FakeGitHubIssues Testing Patterns

## Parameter Confusion: comments vs comments_with_urls

FakeGitHubIssues has two comment-related parameters:

- `comments: dict[int, list[str]]` - Simple comment bodies as strings
- `comments_with_urls: dict[int, list[IssueComment]]` - Full comment objects

### The Pitfall

If you pass string comments to the wrong parameter, tests fail with "no comments found".

```python
# WRONG - passes simple strings to comments_with_urls
fake_gh = FakeGitHubIssues(
    issues={123: issue},
    comments_with_urls={123: ["comment body"]},  # strings won't work!
)

# CORRECT - creates full IssueComment objects
comments = [IssueComment(id=1, url="...", body="...", author="...")]
fake_gh = FakeGitHubIssues(
    issues={123: issue},
    comments_with_urls={123: comments},
)
```

### Prevention

When setting up FakeGitHubIssues for testing:

1. Check which getter method you're calling in your code
2. Use matching parameter name (`comments` for `get_comments`, `comments_with_urls` for `get_issue_comments_with_urls`)
3. Ensure correct types for the parameter

## Reference Test File

See: `tests/unit/fakes/test_fake_github_issues.py` (1023 lines of comprehensive examples)
