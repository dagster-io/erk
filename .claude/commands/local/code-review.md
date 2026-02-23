---
description: Run all applicable code reviews locally against the current branch
---

# /local:code-review

Run all applicable code reviews locally, replicating the CI review experience from `.github/workflows/code-reviews.yml`. Discovers changed files, matches review definitions, runs matching reviews in parallel, and presents a unified report.

## Instructions

### Phase 1: Discover Changed Files and Match Reviews

**Get changed files:**

```bash
git diff --name-only $(git merge-base master HEAD)...HEAD
```

If no changed files, report "No changes found relative to master" and stop.

**Read review definitions:**

Read the frontmatter (first `---` block) of each `.erk/reviews/*.md` file. Extract:

- `name`: Review name
- `paths`: List of glob patterns (gitignore-style, e.g., `**/*.py`, `src/**/*.py`)
- `enabled`: Whether the review is active (skip if `false`)
- `model`: Which model to use

**Match reviews to changed files:**

For each enabled review, check if ANY changed file matches ANY of its `paths` glob patterns:

- `**/*.py` matches any `.py` file at any depth
- `src/**/*.py` matches `.py` files under `src/`
- `docs/learned/**/*.md` matches `.md` files under `docs/learned/`
- `.claude/**/*.md` matches `.md` files under `.claude/`

Use Python's `fnmatch` or `pathlib.PurePath.match()` logic — a pattern like `**/*.py` should match `src/erk/cli/main.py`.

**Report:**

```
Changed files: N
Reviews matched: review-a, review-b (N of M enabled reviews)
Reviews skipped (no matching files): review-c, review-d
```

If no reviews matched, report and stop.

### Phase 2: Run Reviews in Parallel

Generate a run ID: `review-<timestamp>` (e.g., `review-20260222-1930`).

For each matching review, launch a Task agent in parallel with:

- `subagent_type`: `general-purpose`
- `model`: Use the `model` field from the review frontmatter. Map values: `claude-haiku-4-5` → `haiku`, `claude-sonnet-4-5` or `claude-sonnet-4-6` → `sonnet`

**Agent prompt template:**

```
You are running a local code review. Your task:

1. Read the review definition file: `.erk/reviews/<review-name>.md`
2. Follow the review instructions, with these adaptations for local execution:
   - Instead of `gh pr diff`, use: `git diff $(git merge-base master HEAD)...HEAD`
   - Skip ALL PR-interaction steps (posting comments, fetching existing comments, summary comments, activity logs)
   - Skip any steps about checking for existing review markers or comments
3. Write your findings to `.erk/scratch/<run-id>/<review-name>.md` using the Write tool

Output format for the scratch file:

# <Review Name> Results

## Violations

For each violation found:
### <file-path>:<line-number>
**Rule**: <rule violated>
**Detail**: <explanation>

If no violations found, write:
## Violations
None found.

## Summary
- Files reviewed: N
- Violations found: N

IMPORTANT:
- You MUST write results to the scratch file using the Write tool
- Do NOT return results inline only — write the file
- Do NOT post PR comments or interact with GitHub
- Do NOT skip any analysis steps — only skip PR-interaction steps
```

Launch ALL matching review agents in a single message (parallel execution).

### Phase 3: Collect and Report

After all agents complete, read each scratch file from `.erk/scratch/<run-id>/`.

**Verify output files exist** before reading. If any are missing, report which review failed.

Present a unified report:

```markdown
## Local Code Review Results

**Run ID**: <run-id>
**Changed files**: N | **Reviews run**: N

### <Review Name>

<violations or "No violations found">

### <Review Name>

<violations or "No violations found">

---

**Summary**: X total violations across Y reviews (Z reviews clean)
```

Group violations by review, then by file within each review.

If all reviews are clean, celebrate briefly:

```
All N reviews passed with no violations.
```
