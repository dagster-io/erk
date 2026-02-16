---
title: Stub PR Workflow Link
read_when:
  - "understanding the PR body lifecycle in one-shot workflows"
  - "working with stub PR creation or workflow run links"
  - "debugging missing workflow run links in PR descriptions"
tripwires:
  - action: "silently catching exceptions in PR body updates"
    warning: "Use best-effort pattern: try/except with logger.warning(), not silent pass. See one_shot_dispatch.py for the canonical example."
last_audited: "2026-02-16 14:25 PT"
audit_result: clean
---

# Stub PR Workflow Link

PR bodies in one-shot workflows go through a three-tier lifecycle: stub creation, workflow link injection, and AI-generated summary replacement.

## Three-Tier PR Body Lifecycle

| Stage            | Content                        | When                 | Who                      |
| ---------------- | ------------------------------ | -------------------- | ------------------------ |
| 1. Stub          | Minimal placeholder            | PR creation          | `gt create` / GitHub API |
| 2. Workflow link | Instruction + workflow run URL | After dispatch       | `one_shot_dispatch.py`   |
| 3. AI summary    | Full description with context  | After implementation | `erk pr submit`          |

## Workflow Link Implementation

<!-- Source: src/erk/cli/commands/one_shot_dispatch.py:236-247 -->

After dispatching a one-shot workflow, `one_shot_dispatch.py` updates the stub PR body with:

- The original instruction text
- A link to the GitHub Actions workflow run

This uses the best-effort pattern: the update is wrapped in try/except with `logger.warning()`, not a silent pass. If the GitHub API call fails, the workflow continues — the link is informational, not critical.

## construct_workflow_run_url()

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/parsing.py:268-283 -->

Simple URL construction: `https://github.com/{owner}/{repo}/actions/runs/{run_id}`

Located in `erk_shared.gateway.github.parsing` alongside other URL construction helpers.

## FakeGitHub Assertion Pattern

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/fake.py:150,200,290 -->

`FakeGitHub` tracks PR body updates in `updated_pr_bodies: list[tuple[int, str]]`. Tests assert against this:

```python
assert len(github.updated_pr_bodies) == 1
_pr_num, updated_body = github.updated_pr_bodies[0]
assert "**Workflow run:**" in updated_body
```

The tuple unpacking pattern `(pr_number, body)` is used consistently for PR body mutation assertions.

## Related Documentation

- [PR Submit Phases](pr-submit-phases.md) — Full PR submission pipeline including body generation
