---
title: FakeGitHubIssues Dual-Comment Parameters
read_when:
  - "setting up FakeGitHubIssues in a test"
  - "test fails with empty comments from FakeGitHubIssues"
  - "choosing between comments and comments_with_urls parameters"
tripwires:
  - action: "passing string values to comments_with_urls parameter of FakeGitHubIssues"
    warning: "comments_with_urls requires IssueComment objects, not strings. Strings cause silent empty-list returns. Match the parameter to the ABC getter method your code calls."
---

# FakeGitHubIssues Dual-Comment Parameters

## Why Two Comment Parameters Exist

<!-- Source: erk_shared/gateway/github/issues/abc.py, GitHubIssues.get_issue_comments -->
<!-- Source: erk_shared/gateway/github/issues/abc.py, GitHubIssues.get_issue_comments_with_urls -->

The `GitHubIssues` ABC exposes two distinct comment-retrieval methods: `get_issue_comments()` returns plain body strings, while `get_issue_comments_with_urls()` returns full `IssueComment` objects (with id, url, body, and author). These serve different use cases — simple body inspection vs. operations that need comment identity (reactions, updates, URL linking).

<!-- Source: erk_shared/gateway/github/issues/fake.py, FakeGitHubIssues.__init__ -->

`FakeGitHubIssues` mirrors this split with two constructor parameters: `comments` (for body strings) and `comments_with_urls` (for `IssueComment` objects). Each parameter feeds exactly one getter method. They are completely independent stores — populating one does not affect the other.

## The Pitfall: Silent Type Mismatch

Because both parameters are dicts keyed by issue number, it's easy to pass the wrong type to the wrong parameter. The failure mode is silent: the getter returns an empty list rather than raising a type error, because it's querying the unpopulated store.

```python
# WRONG - passes strings where IssueComment objects are required
# get_issue_comments_with_urls() will return [] even though data exists in the wrong store
fake_gh = FakeGitHubIssues(
    comments_with_urls={123: ["comment body"]},
)
```

## Decision Rule: Match Parameter to Getter

| Code under test calls...         | Configure this parameter | With this type                  |
| -------------------------------- | ------------------------ | ------------------------------- |
| `get_issue_comments()`           | `comments`               | `dict[int, list[str]]`          |
| `get_issue_comments_with_urls()` | `comments_with_urls`     | `dict[int, list[IssueComment]]` |
| `get_comment_by_id()`            | `comments_with_urls`     | `dict[int, list[IssueComment]]` |

`get_comment_by_id()` searches `comments_with_urls` first, then falls back to dynamically-added comments (from `add_comment()` calls). It never reads the `comments` store.

## Instance of a Broader Pattern

This dual-store design appears elsewhere in erk's fakes. FakeGitHub has an analogous pitfall with `prs` vs `pr_details` for branch lookups — both must be configured for `get_pr_for_branch()` to work. See the FakeGitHub section in [testing.md](testing.md) for that variant.

The general lesson: when a fake has multiple parameters that sound related, check which ABC method your code calls, then trace backward to the specific constructor parameter that feeds it.
