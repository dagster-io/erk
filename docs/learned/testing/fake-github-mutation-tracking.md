---
title: FakeGitHub Mutation Tracking
read_when:
  - "asserting against FakeGitHub mutations in tests"
  - "adding a new mutation tracking list to FakeGitHub or FakeGitHubIssues"
  - "understanding tuple formats in fake gateway tracking lists"
tripwires:
  - action: "adding a tracking list without documenting the tuple field order"
    warning: "Every tracking list must have a property docstring specifying the tuple format (e.g., 'Returns list of (pr_number, label) tuples'). Without it, test authors guess field positions wrong."
---

# FakeGitHub Mutation Tracking

The `FakeGitHub` and `FakeGitHubIssues` classes track all mutations as lists of tuples. Tests assert against these lists to verify correct API call sequences without hitting real GitHub.

## Tuple Format Convention

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py:145-171 -->

Every tracking list uses a typed tuple with a specific field order. The convention is `list[tuple[field1_type, field2_type, ...]]` with the field order documented in the property docstring.

## FakeGitHub Tracking Lists

| List                       | Tuple Format                                      | Example                                          |
| -------------------------- | ------------------------------------------------- | ------------------------------------------------ |
| `_downloaded_artifacts`    | `(run_id, artifact_name, destination)`            | `("123", "results", Path("/tmp/out"))`           |
| `_created_gists`           | `(filename, content, description, public)`        | `("log.txt", "data", "desc", False)`             |
| `_updated_pr_bases`        | `(pr_number, new_base)`                           | `(42, "main")`                                   |
| `_updated_pr_bodies`       | `(pr_number, body)`                               | `(42, "new body")`                               |
| `_updated_pr_titles`       | `(pr_number, title)`                              | `(42, "new title")`                              |
| `_triggered_workflows`     | `(workflow, inputs)`                              | `("ci.yml", {"ref": "main"})`                    |
| `_poll_attempts`           | `(workflow, branch_name, timeout, poll_interval)` | `("ci.yml", "feat", 300, 10)`                    |
| `_created_prs`             | `(branch, title, body, base, draft)`              | `("feat", "Add X", "body", None, False)`         |
| `_added_labels`            | `(pr_number, label)`                              | `(42, "erk-plan-review")`                        |
| `_thread_replies`          | `(thread_id, body)`                               | `("T_123", "reply")`                             |
| `_pr_review_comments`      | `(pr_number, body, commit_sha, path, line)`       | `(42, "fix", "abc123", "src/foo.py", 10)`        |
| `_pr_comments`             | `(pr_number, body)`                               | `(42, "comment")`                                |
| `_pr_comment_updates`      | `(comment_id, body)`                              | `(100, "updated")`                               |
| `_created_commit_statuses` | `(repo, sha, state, context, description)`        | `("org/repo", "abc", "success", "ci", "passed")` |
| `_operation_log`           | `(Any, ...)`                                      | Ordered log for testing operation sequences      |

## FakeGitHubIssues Tracking Lists

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/issues/fake.py -->

| List                | Tuple Format                       | Example                           |
| ------------------- | ---------------------------------- | --------------------------------- |
| `_created_issues`   | `(title, body, labels)`            | `("Fix bug", "body", ["bug"])`    |
| `_added_comments`   | `(issue_number, body, comment_id)` | `(42, "comment", 100)`            |
| `_created_labels`   | `(label, description, color)`      | `("bug", "Bug report", "ff0000")` |
| `_closed_issues`    | `int` (issue_number)               | `42`                              |
| `_added_reactions`  | `(issue_number, reaction)`         | `(42, "+1")`                      |
| `_updated_bodies`   | `(issue_number, body)`             | `(42, "new body")`                |
| `_updated_titles`   | `(issue_number, title)`            | `(42, "new title")`               |
| `_updated_comments` | `(comment_id, body)`               | `(100, "updated")`                |

## Test Assertion Pattern

Access tracking lists via properties (not directly via `_` attributes):

```python
# Assert a PR was created with expected args
assert fake_github.created_prs == [
    ("feat-branch", "Add feature", "PR body", None, False),
]

# Assert label was added
assert fake_github.added_labels == [(42, "erk-plan-review")]
```

## Related Documentation

- [Testing Reference](testing.md) — Test infrastructure overview
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) — How fakes implement gateway interfaces
