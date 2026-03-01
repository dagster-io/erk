---
title: CI Failure Summarization
read_when:
  - "working with CI failure summaries or ERK-CI-SUMMARY markers"
  - "modifying the ci-summarize workflow job"
  - "understanding how TUI displays CI failure details"
  - "debugging CI summary parsing or matching"
tripwires:
  - action: "changing the ci-summarize job `needs` array"
    warning: "The `needs` array must reference actual job names in ci.yml. Broken references silently skip the job. Verify every name exists."
  - action: "parsing ERK-CI-SUMMARY markers without re.DOTALL"
    warning: "Summary content is multiline. The regex uses re.DOTALL so `.` matches newlines. Without it, multiline summaries won't be captured."
  - action: "matching check names from summaries to GitHub check runs"
    warning: "GitHub prepends 'ci / ' to check names in statusCheckRollup. Use match_summary_to_check() which strips this prefix."
---

# CI Failure Summarization

When CI checks fail on a PR, the `ci-summarize` workflow job generates human-readable summaries using Haiku. These summaries are embedded in the job's logs as structured markers, then parsed and displayed in the TUI.

## Architecture Overview

```
CI job fails
  -> ci-summarize job runs (ci.yml)
  -> erk exec ci-generate-summaries fetches logs + calls Haiku
  -> Outputs ERK-CI-SUMMARY markers to stdout
  -> Markers stored in ci-summarize job logs
  -> erk exec ci-fetch-summaries retrieves + parses markers
  -> TUI check_runs_screen displays summaries as blockquotes
```

## ERK-CI-SUMMARY Marker Format

Summaries are delimited by structured markers in the ci-summarize job's log output:

```
=== ERK-CI-SUMMARY:check-name ===
- First bullet point of summary
- Second bullet point
=== /ERK-CI-SUMMARY:check-name ===
```

The opening and closing markers must use identical check names (enforced by backreference regex).

## Parsing

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/ci_summary_parsing.py -->

`parse_ci_summaries(log_text)` extracts summaries from raw log text into a `dict[str, str]` mapping check name to summary text.

**Regex pattern:** `r"=== ERK-CI-SUMMARY:(.+?) ===\n(.*?)=== /ERK-CI-SUMMARY:\1 ==="`

- Uses `re.DOTALL` so `.` matches newlines in multiline summaries
- Backreference `\1` ensures opening/closing markers match
- Non-greedy quantifiers prevent spanning across multiple summaries

`match_summary_to_check(check_name, summary_keys)` handles GitHub's automatic `ci / ` prefix. GitHub prepends this to check names in `statusCheckRollup`, so `unit-tests (3.12)` becomes `ci / unit-tests (3.12)`. The function strips this prefix when matching.

## 5-Place Gateway Pattern

`get_ci_summary_logs(repo_root, run_id)` fetches the ci-summarize job's raw logs:

| Place    | Behavior                                                          |
| -------- | ----------------------------------------------------------------- |
| ABC      | Abstract method returning `str \| None`                           |
| Real     | Queries GitHub API for job named "ci-summarize", fetches its logs |
| Fake     | Returns pre-configured log text from `_ci_summary_logs` dict      |
| Dry Run  | Delegates to wrapped implementation                               |
| Printing | Delegates with verbose output                                     |

## 3-Place Service Pattern

<!-- Source: packages/erk-shared/src/erk_shared/gateway/plan_data_provider -->

`PlanDataProvider.fetch_ci_summaries(pr_number)` orchestrates retrieval:

1. Gets PR details via `github.get_pr()`
2. Finds CI workflow runs for the PR's head branch
3. Fetches ci-summarize job logs via `get_ci_summary_logs()`
4. Parses with `parse_ci_summaries()`
5. Returns `dict[str, str]` (empty dict on any failure)

## TUI Integration

<!-- Source: src/erk/tui/screens/check_runs_screen.py -->

`CheckRunsScreen` uses two-phase loading for responsive UX:

1. **Phase 1:** Fetch check runs in background, display immediately without summaries
2. **Phase 2:** Fetch summaries in background, re-render check runs with blockquote summaries when available

Summaries are matched to check runs via `match_summary_to_check()` and rendered as markdown blockquotes below each failing check.

## Exec Commands

### `ci-generate-summaries`

<!-- Source: src/erk/cli/commands/exec/scripts/ci_generate_summaries.py -->

Runs in CI as part of the `ci-summarize` job. For each failing job in the workflow run:

1. Fetches job logs via GitHub API
2. Truncates to last 500 lines
3. Builds prompt from `.github/prompts/ci-summarize.md` template
4. Calls `claude-haiku-4-5-20251001` for summarization
5. Outputs ERK-CI-SUMMARY markers to stdout

Individual job failures don't stop processing of other jobs.

### `ci-fetch-summaries`

<!-- Source: src/erk/cli/commands/exec/scripts/ci_fetch_summaries.py -->

Retrieves summaries for a PR. Finds the latest CI workflow run, fetches ci-summarize job logs, parses markers, and outputs JSON to stdout.

## Prompt Template

<!-- Source: .github/prompts/ci-summarize.md -->

The prompt instructs Haiku to produce 2-5 bullet points focusing on:

- What specific check/test failed (file names, test names)
- The error message or root cause
- Which files are affected

Rules: one line per bullet, backticks for paths/commands, no fix suggestions, no timestamps/URLs.

## Workflow Job Configuration

The `ci-summarize` job in `ci.yml`:

- **`needs`**: All CI check jobs (format, lint, markdown-fix, docs-check, ty, unit-tests, integration-tests, etc.)
- **Conditions**: Only on PRs, only when at least one job fails, skips plan review PRs, requires `CLAUDE_ENABLED != 'false'`
- **Uses `always()`**: Runs even when dependency jobs fail (otherwise GitHub skips it)
- **Timeout**: 10 minutes

## Related Documentation

- [Check State Classification](check-state-classification.md) - How check states are counted and displayed
- [GitHub Token Scopes](github-token-scopes.md) - Token requirements for CI operations
