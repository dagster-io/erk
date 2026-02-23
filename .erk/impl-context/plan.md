# Plan: Local Code Review Command

## Context

CI runs 5 code reviews in parallel on every PR via `.github/workflows/code-reviews.yml`. Each review is defined as a markdown file in `.erk/reviews/` with frontmatter (paths, model, etc.) and step-by-step instructions. The existing `erk exec run-review --name <name> --local` can run a single review locally, but there's no easy way to run all applicable reviews at once. The user wants a `/local:review` slash command to replicate the CI review experience locally.

## Approach

Create a single file: `.claude/commands/local/review.md`

The command will:
1. Discover changed files via `git diff --name-only` against trunk
2. Read all `.erk/reviews/*.md` files and match against changed files using frontmatter `paths` patterns
3. Launch parallel Task agents (one per matching review) that each apply the review instructions to the local diff
4. Collect results and present a unified report

Each Task agent directly applies the review logic (reads the review definition, gets the diff, follows the instructions, writes violations to a scratch file). This avoids spawning nested Claude sessions via `erk exec run-review --local`.

## Implementation

### File: `.claude/commands/local/review.md`

**Phase 1: Discover**
- Run `git diff --name-only $(git merge-base master HEAD)...HEAD` to get changed files
- If no changes, report and exit
- Read each `.erk/reviews/*.md` file (just frontmatter) to get `name`, `paths`, `enabled`
- Skip disabled reviews
- Match: a review applies if any changed file matches any of its `paths` glob patterns (gitignore-style, supports `**`)
- Report which reviews matched and which were skipped

**Phase 2: Run Reviews in Parallel**
- Generate a run ID: `review-<timestamp>`
- For each matching review, launch a Task agent (`subagent_type=general-purpose`) that:
  1. Reads the full review definition file (`.erk/reviews/<name>.md`)
  2. Gets the diff: `git diff $(git merge-base master HEAD)...HEAD`
  3. Follows the review-specific instructions (Step 1 through the analysis steps)
  4. Writes structured violations to `.erk/scratch/<run-id>/<review-name>.md`
  5. Ignores PR-specific steps (posting comments, fetching existing comments, summary comment)

The agent prompt will include:
- The review definition path to read
- The git diff commands to run
- Instructions to write results to the scratch file
- Explicit instruction to skip PR-interaction steps

**Phase 3: Collect and Report**
- Read all scratch files
- Present a unified report grouping violations by review, then by file
- Show summary counts

## Key Patterns from Existing Commands

- From `audit-scan.md`: parallel Task agents writing to `.erk/scratch/` files, then main agent collecting results
- From `fast-ci.md`: iterative check workflow with clear phase structure
- Review definitions reference skill files and docs — agents need Read tool access

## Review Definitions (for reference)

| Review | Paths | Model |
|--------|-------|-------|
| dignified-python | `**/*.py` | haiku |
| dignified-code-simplifier | `**/*.py` | haiku |
| test-coverage | `src/**/*.py`, `packages/**/*.py`, `tests/**/*.py` | haiku |
| tripwires | `**/*.py`, `**/*.sh`, `.claude/**/*.md` | sonnet |
| audit-pr-docs | `docs/learned/**/*.md` | sonnet |

## Verification

1. Create a test branch with a Python change, run `/local:review`, confirm dignified-python, dignified-code-simplifier, test-coverage, and tripwires all run
2. Create a branch with only docs changes, confirm only audit-pr-docs runs
3. Run on a branch with no changes, confirm clean exit
