---
title: Skill-Based Commit Message Generation
read_when:
  - "creating commits for significant changes"
  - "preparing PR submissions"
  - "wondering whether to load erk-diff-analysis skill"
tripwires:
  - action: "writing a commit message manually for multi-file changes"
    warning: "Load the erk-diff-analysis skill first. It produces component-aware, strategically framed messages that become both the commit and PR body."
  - action: "loading erk-diff-analysis skill more than once per session"
    warning: "Skills persist for the entire session. Check conversation history for 'erk-diff-analysis' before reloading."
last_audited: "2026-02-08"
audit_result: clean
---

# Skill-Based Commit Message Generation

Erk uses the `erk-diff-analysis` skill to generate commit messages from staged diffs. This matters because commit messages flow directly into PR titles and bodies — a weak commit message creates a weak PR that reviewers must decode manually.

## Why Not Just Write Messages Manually?

Agent-written commit messages default to describing _what_ changed ("Update documentation", "Fix bug in gateway"). The skill reframes messages around _why_ and _impact_ — which components are affected, what goal the change serves, and what issue it closes. This isn't about saving keystrokes; it's about producing messages that serve as useful PR descriptions without additional editing.

The skill also enforces structural consistency: component-level grouping, 3-5 key changes maximum, relative paths from repo root, and automatic `Closes #N` references when issue context exists. These conventions are defined in the skill's prompt template.

<!-- Source: .claude/skills/erk-diff-analysis/references/commit-message-prompt.md -->

See the output format and analysis principles in `.claude/skills/erk-diff-analysis/references/commit-message-prompt.md`.

## When to Use Skill-Based Messages

| Scenario                                        | Use Skill? | Why                                                      |
| ----------------------------------------------- | ---------- | -------------------------------------------------------- |
| Multi-file feature implementation               | Always     | Many components to identify and frame strategically      |
| Documentation batch (multiple new/updated docs) | Always     | File grouping by area prevents "updated docs" vagueness  |
| Non-trivial bug fix spanning multiple areas     | Always     | Rationale and affected areas matter for reviewers        |
| Single-line typo fix                            | Optional   | Low value — the diff is self-explanatory                 |
| Auto-formatting changes                         | Optional   | No strategic framing needed                              |
| Empty commits, merges, reverts                  | Never      | Git generates these messages; skill would overwrite them |

## Commit-to-PR Body Flow

A key design decision: the commit message's first line becomes the PR title, and the remaining body becomes the PR description. Both `/erk:git-pr-push` and `/erk:pr-submit` implement this pattern.

<!-- Source: .claude/commands/erk/git-pr-push.md, Step 7 -->

This means investing in commit message quality pays off twice — you get a good commit _and_ a good PR without writing separate descriptions. The PR submission commands append a checkout footer and issue closing references automatically.

For details on how the two PR workflows differ (git-only vs. Graphite), see [PR Submission Decision Framework](../cli/pr-submission.md).

## Integration with PR Submission Commands

Both PR submission commands load the skill automatically as part of their workflow:

- **`/erk:git-pr-push`** — Loads `erk-diff-analysis` at Step 3, uses the generated message for both commit and PR body. Pure git + gh workflow.
- **`/erk:pr-submit`** — Same skill-based generation, but delegates to Graphite for stack management and commit squashing.

<!-- Source: .claude/commands/erk/git-pr-push.md, Step 3 -->

When using these commands, you don't need to load the skill separately — they handle it. The skill only needs manual loading when you're committing outside the PR submission workflow (e.g., intermediate commits during development).

## Session Persistence

The `erk-diff-analysis` skill, like all Claude Code skills, persists for the entire session once loaded. If you're making multiple commits in one session, load it once before the first commit. Check conversation history for the skill loading message before reloading.

**Anti-pattern:** Loading the skill before every commit in the same session. This wastes context window tokens for no benefit.

**Anti-pattern:** Forgetting to load the skill when committing manually (outside `/erk:git-pr-push` or `/erk:pr-submit`). The commit message quality drop is significant for multi-file changes.

## See Also

- [PR Submission Decision Framework](../cli/pr-submission.md) — When to use git-pr-push vs. pr-submit
- `.claude/commands/erk/git-pr-push.md` — Full command specification
- `.claude/skills/erk-diff-analysis/SKILL.md` — Skill definition and principles
