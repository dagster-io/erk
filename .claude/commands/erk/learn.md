---
description: Extract insights from plan-associated sessions
argument-hint: "[issue-number]"
---

# /erk:learn

Create a documentation plan from Claude Code sessions associated with a plan implementation. The verb "learn" means: analyze what happened, extract insights, and create an actionable plan to document those learnings.

## Usage

```
/erk:learn                              # Infers issue from current branch (P{issue}-...)
/erk:learn 4655                          # Explicit issue number
/erk:learn 4655 gist_url=https://...    # With preprocessed materials gist
```

## Agent Instructions

First, load the learn skill:

```
Skill(skill: "learn")
```

Tell the user:

```
Learn pipeline for plan #<issue-number>:
  1. Read local session logs from ~/.claude/projects/
  2. Preprocess sessions (compress JSONL → XML, deduplicate, truncate)
  3. Upload preprocessed XML + PR comments to a secret GitHub gist
  4. Launch analysis agents (session, diff, docs check, PR comments)
  5. Synthesize findings into a documentation plan
  6. Save plan as a new GitHub issue
```

### Step 1: Validate Plan Type

**Learn plans cannot generate additional learn plans** — this would create documentation cycles.

```bash
erk exec get-issue-body <issue-number>
```

Parse the JSON output and check the `labels` array. If `erk-learn` is present, stop with:

```
Error: Issue #<issue-number> is a learn plan (has erk-learn label).
Cannot learn from a learn plan - this would create documentation cycles.
```

### Step 2: Check for Preprocessed Materials

Check if a `gist_url` parameter was provided in the command arguments (format: `gist_url=https://...`).

**If `gist_url` is provided:**

1. Create the learn directory:

   ```bash
   mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn
   ```

2. Download and extract the gist:

   ```bash
   result=$(erk exec download-learn-materials \
       --gist-url "<gist_url>" \
       --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn)

   if echo "$result" | jq -e '.success == false' > /dev/null 2>&1; then
       echo "ERROR: Failed to download learn materials: $(echo "$result" | jq -r '.error')"
       exit 1
   fi

   file_count=$(echo "$result" | jq -r '.file_count')
   echo "Downloaded $file_count file(s) from gist"
   ```

3. Tell the user, then **skip to Step 4** (the preprocessed sessions and PR comments are already downloaded).

**If no `gist_url` is provided:** Proceed to Step 3.

### Step 3: Get Session Information

```bash
erk exec get-learn-sessions <issue-number>
```

Parse the JSON output to get `session_sources`, `planning_session_id`, `implementation_session_ids`.

If no sessions are found, inform the user and stop.

Tell the user how many local and remote sessions were found.

### Step 4: Gather and Analyze Sessions

Get the PR information:

```bash
erk exec get-pr-for-plan <issue-number>
```

Save the PR number for agent launches.

**If gist was provided in Step 2**, skip preprocessing and upload — jump to "Launch Parallel Analysis Agents".

#### Analyze Current Conversation

**You have direct access to this session.** Examine what happened:

1. **User corrections**: Did the user correct any assumptions or approaches?
2. **External lookups**: What did you WebFetch or WebSearch?
3. **Unexpected discoveries**: What surprised you during implementation?
4. **Repeated patterns**: Did you do something multiple times that could be streamlined?

#### Preprocess Sessions

For each session source from Step 3:

- If `source_type == "local"` and `path` is set: Process directly
- If `source_type == "remote"`: Download first via `erk exec download-remote-session --gist-url "<gist_url>" --session-id "<session_id>"`, then process

```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn

# For planning session (source.session_id == planning_session_id):
erk exec preprocess-session "<source.path>" \
    --max-tokens 20000 \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --prefix planning

# For implementation sessions:
erk exec preprocess-session "<source.path>" \
    --max-tokens 20000 \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --prefix impl
```

#### Save PR Comments

If a PR exists:

```bash
erk exec get-pr-review-comments --pr <pr-number> --include-resolved \
    > .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/pr-review-comments.json

erk exec get-pr-discussion-comments --pr <pr-number> \
    > .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/pr-discussion-comments.json
```

#### Upload to Gist

```bash
result=$(erk exec upload-learn-materials \
    --learn-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --issue <issue-number>)

if echo "$result" | jq -e '.success == false' > /dev/null 2>&1; then
    echo "ERROR: Failed to upload learn materials: $(echo "$result" | jq -r '.error')"
    exit 1
fi

gist_url=$(echo "$result" | jq -r '.gist_url')
echo "Gist created: $gist_url"
```

#### Launch Parallel Analysis Agents

Follow the shared reference: `.claude/skills/learn/references/launch-analysis-agents.md`

All 4 agents are applicable for plan-based learning:

- SessionAnalyzer: Launch for each preprocessed XML file
- CodeDiffAnalyzer: Launch if PR exists
- ExistingDocsChecker: Always launch
- PRCommentAnalyzer: Launch if PR exists

#### Collect Agent Results

Follow the shared reference: `.claude/skills/learn/references/collect-results.md`

#### Synthesis Pipeline

Follow the shared reference: `.claude/skills/learn/references/synthesis-pipeline.md`

Pass the `gist_url` and `pr_number` to the PlanSynthesizer.

#### Deep Analysis (Manual Fallback)

If agents were not launched or failed, fall back to manual analysis. Read all preprocessed XML files and mine them for patterns, errors, decisions, and external lookups.

### Step 5: Review Synthesized Plan

Follow the shared reference: `.claude/skills/learn/references/review-plan.md`

### Step 6: Present Findings

Present the synthesized plan to the user.

**CI Detection**:

```bash
[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"
```

- **CI mode**: Skip user confirmation. Auto-proceed to Step 7.
- **Interactive mode**: Confirm with the user before saving. If the user decides to skip, proceed to Step 9.

### Step 7: Validate and Save Learn Plan

Follow the shared reference: `.claude/skills/learn/references/save-learn-plan.md`

Add the `--learned-from-issue <parent-issue-number>` flag when calling `plan-save-to-issue`.

If running in CI with `$WORKFLOW_RUN_URL` set, also add `--created-from-workflow-run-url "$WORKFLOW_RUN_URL"`.

Display the result:

```
Learn plan saved to GitHub issue #<issue_number>

Raw materials: <gist-url>
```

### Step 8: Track Learn Result on Parent Plan

**If plan was valid and saved:**

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_with_plan \
    --plan-issue <new-learn-plan-issue-number>
```

**If plan validation failed:**

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_no_plan
```

### Step 9: Post-Learn Decision Menu

**CI Detection**: If CI_MODE, auto-select option 1 (submit) and proceed to Step 10.

**Check for other open learn plans:**

```bash
OTHER_LEARN_COUNT=$(erk exec list-plans --label erk-learn --state open --format json 2>/dev/null | jq '.plans | length')
```

**Interactive mode**: Present the menu:

If other learn plans exist (count > 1):

```
Post-learn actions:
  1. Submit for implementation (Recommended) — Queue for remote implementation
  2. Review in browser — Open issue in web browser for review/editing
  3. Consolidate with other learn plans — Merge overlapping learn plans
  4. Done — Finish learn workflow
```

If no other learn plans (count <= 1):

```
Post-learn actions:
  1. Submit for implementation (Recommended) — Queue for remote implementation
  2. Review in browser — Open issue in web browser for review/editing
  3. Done — Finish learn workflow
```

**Execute the selected action:**

- **Submit**: Run `/erk:plan-submit`
- **Review**: Run `gh issue view <issue_number> --web`, then inform the user they can run `/erk:plan-submit` when ready
- **Consolidate**: Run `/local:replan-learn-plans`
- **Done**: Proceed directly to Step 10

### Step 10: Track Evaluation

**CRITICAL: Always run this step**, regardless of which option was selected:

```bash
erk exec track-learn-evaluation <issue-number> --session-id="${CLAUDE_SESSION_ID}"
```

### Tips

- Preprocessed sessions use XML: `<user>`, `<assistant>`, `<tool_use>`, `<tool_result>`
- `<tool_result>` elements with errors often reveal the most useful insights
- The more context you include in the issue, the faster the implementing agent can work
