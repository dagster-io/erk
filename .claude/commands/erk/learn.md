---
description: Extract insights from plan-associated sessions
argument-hint: "[issue-number]"
---

# /erk:learn

Create a documentation plan from Claude Code sessions associated with a plan implementation. The verb "learn" means: analyze what happened, extract insights, and create an actionable plan to document those learnings.

## Usage

```
/erk:learn           # Infers issue from current branch (P{issue}-...)
/erk:learn 4655      # Explicit issue number
```

## Purpose

**Audience**: All documentation produced by this command is for AI agents, not human users.

These docs are "token caches" - preserved reasoning and research so future agents don't have to recompute it. When you research something, discover a pattern, or figure out how something works, that knowledge should be captured so the next agent doesn't burn tokens rediscovering it.

**Document reality**: Capture the world as it is, not as we wish it to be. "This is non-ideal but here's the current state" is valuable documentation. Tech debt, workarounds, quirks - document them. Future agents need to know how things actually work.

**Bias toward capturing**: When uncertain whether something is worth documenting, include it. Over-documentation is better than losing insights.

**Reject dismissiveness**: If you find yourself thinking "this doesn't need documentation," pause. That instinct is often wrong. New features, patterns, and capabilities almost always benefit from documentation, even when the code is "clear."

## Agent Instructions

### Step 1: Get Session Information

Run the exec script to get session details:

```bash
erk exec get-learn-sessions <issue-number>
```

Parse the JSON output to get:

- `session_sources`: List of session source objects, each containing:
  - `source_type`: Either "local" (from ~/.claude) or "remote" (from GitHub Actions)
  - `session_id`: The Claude Code session ID
  - `run_id`: GitHub Actions run ID (legacy, may be null)
  - `path`: File path to the session (for local sessions only)
  - `gist_url`: Raw gist URL for downloading session (for remote sessions)
- `planning_session_id`: Session ID that created the plan
- `implementation_session_ids`: Session IDs that executed the plan
- `local_session_ids`: Fallback sessions found locally (when no tracked sessions exist)
- `last_remote_impl_at`: Timestamp if implemented via GitHub Actions (remote)
- `last_remote_impl_run_id`: GitHub Actions run ID for remote implementation
- `last_remote_impl_session_id`: Claude Code session ID from remote implementation

If no sessions are found, inform the user and stop.

**Note on remote sessions:** Remote sessions appear in `session_sources` with `source_type: "remote"` and `path: null`. These sessions must be downloaded before processing (see Step 3).

### Step 2: Analyze Implementation

Before analyzing sessions, understand what code actually changed. A smooth implementation with no errors can still add major new capabilities that need documentation.

Get the PR information for this plan:

```bash
erk exec get-pr-for-plan <issue-number>
```

This returns JSON with PR details (`number`, `title`, `state`, `url`, `head_ref_name`, `base_ref_name`) or an error if no PR exists.

Analyze the changes:

```bash
gh pr view <pr-number> --json files,additions,deletions
gh pr diff <pr-number>
```

**Create an inventory of what was built:**

- **New files**: What files were created?
- **New functions/classes**: What new APIs were added?
- **New CLI commands**: Any new `@click.command` decorators?
- **New patterns**: Any new architectural patterns established?
- **Config changes**: New settings, capabilities, or options?
- **External integrations**: New API calls, dependencies, or tools?

**Save this inventory** - you will reference it in Step 4 to ensure everything new gets documented.

#### Fetch PR Comments

If a PR was found for this plan, fetch review comments for analysis:

```bash
# Get inline review comments (code-level feedback)
erk exec get-pr-review-comments --pr <pr-number> --include-resolved

# Get discussion comments (main PR thread)
erk exec get-pr-discussion-comments --pr <pr-number>
```

**Save these for analysis** - PR comments often reveal:

- Edge cases reviewers identified
- Clarifications about non-obvious behavior
- Alternative approaches discussed
- False positives or misunderstandings to prevent

### Step 3: Gather and Analyze Sessions

#### Check Existing Documentation

**Note:** This manual check provides a quick overview. The **existing-docs-checker agent** (launched in parallel below) performs a thorough search across all documentation directories.

Quick scan for existing documentation:

```bash
ls -la docs/learned/ 2>/dev/null || echo "No docs/learned/ directory"
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"
```

#### Analyze Current Conversation

Before preprocessing session files, analyze the current conversation context:

**You have direct access to this session.** No preprocessing needed - examine what happened:

1. **User corrections**: Did the user correct any assumptions or approaches?
2. **External lookups**: What did you WebFetch or WebSearch? Why wasn't it already documented?
3. **Unexpected discoveries**: What surprised you during implementation?
4. **Repeated patterns**: Did you do something multiple times that could be streamlined?

**Key question**: "What would have made this session faster if I'd known it beforehand?"

These insights are often the most valuable because they represent real friction encountered during implementation.

#### Preprocess Sessions

For each session source from Step 1, preprocess to compressed XML format:

**IMPORTANT:** Check `source_type` before processing:

- If `source_type == "local"` and `path` is set: Process the session using the path
- If `source_type == "remote"`: Download the session first, then process:
  1. Check if `gist_url` is set (not null). If null, the session cannot be downloaded (legacy artifact-based session).
  2. Run: `erk exec download-remote-session --gist-url "<gist_url>" --session-id "<session_id>"`
  3. Parse the JSON output to get the `path` field
  4. If `success: true`, use the returned `path` for preprocessing
  5. If `success: false` (gist not accessible, etc.), inform the user and skip this session

```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn

# For each local session source with a valid path:
# Compare source.session_id to planning_session_id to determine prefix

# For the planning session (source.session_id == planning_session_id):
erk exec preprocess-session "<source.path>" \
    --max-tokens 20000 \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --prefix planning

# For implementation sessions (source.session_id in implementation_session_ids):
erk exec preprocess-session "<source.path>" \
    --max-tokens 20000 \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --prefix impl
```

Note: The preprocessor applies deduplication, truncation, and pruning optimizations automatically. Files are auto-chunked if they exceed the token limit (20000 tokens safely under Claude's 25000 read limit). Output files include session IDs in filenames (e.g., `planning-{session-id}.xml` or `impl-{session-id}-part{N}.xml` for chunked files).

#### Save PR Comments

If PR comments were fetched in Step 2, save them for the gist:

```bash
erk exec get-pr-review-comments --pr <pr-number> --include-resolved \
    > .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/pr-review-comments.json

erk exec get-pr-discussion-comments --pr <pr-number> \
    > .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/pr-discussion-comments.json
```

#### Upload to Gist

Upload preprocessed session files and PR comments to a secret gist:

```bash
result=$(erk exec upload-learn-materials \
    --learn-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --issue <issue-number>)

# Check for failure
if echo "$result" | jq -e '.success == false' > /dev/null 2>&1; then
    echo "ERROR: Failed to upload learn materials: $(echo "$result" | jq -r '.error')"
    exit 1
fi

gist_url=$(echo "$result" | jq -r '.gist_url')
echo "Gist created: $gist_url"
```

Display the gist URL to the user and save it for the plan issue.

#### Launch Parallel Analysis Agents

After preprocessing, launch analysis agents in parallel to extract insights concurrently.

**Agent 1: Session Analysis** (for each preprocessed session)

For each XML file in `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/`:

<!-- Model: haiku - Mechanical extraction from XML; deterministic pattern matching -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze session <session-id>",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/session-analyzer.md`

    Input:
    - session_xml_path: .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/<filename>.xml
    - context: <brief description from plan title>
)
```

**Agent 2: Code Diff Analysis** (if PR exists)

<!-- Model: haiku - Structured inventory of changes; no creative reasoning needed -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze PR diff",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/code-diff-analyzer.md`

    Input:
    - pr_number: <pr-number>
    - issue_number: <issue-number>
)
```

**Agent 3: Existing Documentation Check**

Proactively search for existing documentation to prevent duplicates and detect contradictions:

<!-- Model: haiku - Search and classification task; fast iteration preferred -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Check existing docs",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/existing-docs-checker.md`

    Input:
    - plan_title: <title from plan issue>
    - pr_title: <PR title if available, or empty string>
    - search_hints: <key terms extracted from plan title, comma-separated>
)
```

Extract search hints by:

1. Taking significant nouns/concepts from the plan title
2. Removing common words (the, a, an, to, for, with, add, update, fix, etc.)
3. Example: "Add parallel agent orchestration" → "parallel, agent, orchestration"

#### Collect Agent Results

Use TaskOutput to retrieve findings from each agent:

```
TaskOutput(task_id: <agent-task-id>, block: true)
```

Collect all results before proceeding to the next step.

#### Write Agent Results to Scratch Storage

**CRITICAL:** Use the Write tool to save each agent's output. Do NOT use bash heredoc syntax - it fails with large outputs.

First, create the directory:

```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

Then use the Write tool for each agent output:

1. **Session analysis results** - Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/session-<session-id>.md`
2. **Diff analysis results** - Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md`
3. **Existing docs check results** - Write to `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/existing-docs-check.md`

**Example:**

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md",
  content: <full agent output from TaskOutput>
)
```

**Why Write tool instead of heredoc?**

- Agent outputs can be 10KB+ of markdown
- Bash heredoc fails silently with special characters
- Write tool guarantees the file is created with exact content

#### Verify Files Exist

**Verify files exist before launching gap-identifier:**

```bash
ls -la .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

Confirm you see the expected files (session-\*.md, diff-analysis.md, existing-docs-check.md) before proceeding. If any files are missing, the Write tool call failed and must be retried.

#### Synthesize Agent Findings (Agent 4)

Launch the DocumentationGapIdentifier agent to synthesize outputs from the parallel agents:

<!-- Model: haiku - Rule-based deduplication; explicit criteria, no creativity -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Identify documentation gaps",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/documentation-gap-identifier.md`

    Input:
    - session_analysis_paths: [".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/session-<id>.md", ...]
    - diff_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md" (or null if no PR)
    - existing_docs_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/existing-docs-check.md"
    - plan_title: <title from plan issue>
)
```

**Note:** This agent runs AFTER the parallel agents complete (sequential dependency).

The DocumentationGapIdentifier agent will:

- Collect all candidates from session-analyzer, code-diff-analyzer, and existing-docs-checker
- Deduplicate against existing documentation (ALREADY_DOCUMENTED, PARTIAL_OVERLAP, NEW_TOPIC)
- Cross-reference against the diff inventory to ensure completeness
- Classify items: NEW_DOC | UPDATE_EXISTING | TRIPWIRE | SKIP
- Prioritize by impact: HIGH (gateway methods, contradictions) > MEDIUM (patterns) > LOW (helpers)
- Produce the MANDATORY enumerated table required by Step 4

Write the DocumentationGapIdentifier output to scratch storage using the Write tool:

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md",
  content: <full agent output from TaskOutput>
)
```

#### Synthesize Learn Plan (Agent 5)

Launch the PlanSynthesizer agent to transform the gap analysis into a complete learn plan:

<!-- Model: opus - Creative authoring of narrative context and draft content; quality-critical final output -->

```
Task(
  subagent_type: "general-purpose",
  model: "opus",
  description: "Synthesize learn plan",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/plan-synthesizer.md`

    Input:
    - gap_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md"
    - session_analysis_paths: [".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/session-<id>.md", ...]
    - diff_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md" (or null if no PR)
    - plan_title: <title from plan issue>
    - gist_url: <gist URL from Step 3>
    - pr_number: <PR number if available, else null>
)
```

**Note:** This agent runs AFTER DocumentationGapIdentifier completes (sequential dependency).

Write the synthesized output to scratch storage using the Write tool:

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md",
  content: <full agent output from TaskOutput>
)
```

#### Extract Tripwire Candidates (Agent 6)

Launch the TripwireExtractor agent to pull structured tripwire data from the plan:

<!-- Model: haiku - Mechanical extraction of structured data from prose; no creativity needed -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Extract tripwire candidates",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/tripwire-extractor.md`

    Input:
    - learn_plan_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md"
    - gap_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md"
)
```

**Note:** This agent runs AFTER PlanSynthesizer completes (sequential dependency).

Write the output to scratch storage using the Write tool:

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json",
  content: <full agent output from TaskOutput>
)
```

#### Agent Dependency Graph

```
Parallel Tier (can run simultaneously):
  ├─ SessionAnalyzer (per session XML)
  ├─ CodeDiffAnalyzer (if PR exists)
  └─ ExistingDocsChecker

Sequential Tier 1 (depends on Parallel Tier):
  └─ DocumentationGapIdentifier

Sequential Tier 2 (depends on Sequential Tier 1):
  └─ PlanSynthesizer

Sequential Tier 3 (depends on Sequential Tier 2):
  └─ TripwireExtractor
```

#### Deep Analysis (Manual Fallback)

If agents were not launched or failed, fall back to manual analysis.

Read all preprocessed session files in the learn directory:

```bash
# Use Glob to find all XML files (they include session IDs and may be chunked)
ls .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/*.xml
```

Files are named: `{prefix}-{session_id}.xml` or `{prefix}-{session_id}-part{N}.xml` for chunked files.

Read each file and mine them thoroughly.

**Compaction Awareness:** Long sessions may have been "compacted" (earlier messages summarized), but pre-compaction content still contains valuable research.

**Subagent Mining:**

1. Identify all Task tool invocations (`<invoke name="Task">`)
2. Read subagent outputs - each returns a detailed report
3. Mine Explore agents for codebase findings
4. Mine Plan agents for design decisions
5. Extract specific insights, not just summaries

**What to capture:**

- Files read and what was learned from them
- Patterns discovered in the codebase
- Design decisions and reasoning
- External documentation fetched (WebFetch, WebSearch)
- Error messages and how they were resolved

### Step 4: Review Synthesized Plan

Read the PlanSynthesizer output:

```bash
cat .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md
```

The PlanSynthesizer has already:

- Collected all candidates from the parallel agents via DocumentationGapIdentifier
- Created a narrative context explaining what was built
- Generated documentation items with draft content starters
- Described tripwire insights naturally in prose

The TripwireExtractor has:

- Extracted structured tripwire candidate data from the plan into `tripwire-candidates.json`

#### Validate the Synthesized Plan

Review the synthesized plan:

1. **Context section**: Does it accurately describe what was built?
2. **Contradiction resolutions**: Do they make sense?
3. **HIGH priority items**: Are they appropriate?
4. **Draft content starters**: Are they actionable (not just "document this")?
5. **Skip reasons**: Are they valid (not "self-documenting code")?

#### PR Comment Analysis (Additional)

If PR comments were fetched in Step 2, mine them for additional documentation opportunities not captured by the agents:

**Review Comments (Inline)**

| Thread | Path | Key Insight | Documentation Opportunity |
| ------ | ---- | ----------- | ------------------------- |
| ...    | ...  | ...         | ...                       |

Look for:

- **False positives**: Reviewer misunderstood something → document to prevent future confusion
- **Clarification requests**: "Why does this..." → document the reasoning
- **Suggested alternatives**: Discussed but rejected → document the decision
- **Edge case questions**: "What happens if..." → document the behavior

**Discussion Comments (Main Thread)**

| Author | Key Point | Documentation Opportunity |
| ------ | --------- | ------------------------- |
| ...    | ...       | ...                       |

Look for:

- Design discussions that led to choices
- Trade-off conversations
- Implementation details explained in prose

Add any additional items from PR comments to the documentation plan.

#### Reference: Common Documentation Locations

| What was built            | Documentation needed                                       |
| ------------------------- | ---------------------------------------------------------- |
| New CLI command           | Document in `docs/learned/cli/` - usage, flags, examples   |
| New gateway method        | Add tripwire about ABC implementation (5 places to update) |
| New capability            | Update capability system docs, add to glossary             |
| New config option         | Add to `docs/learned/glossary.md`                          |
| New exec script           | Document purpose, inputs, outputs                          |
| New architectural pattern | Create architecture doc or add tripwire                    |
| External API integration  | Document quirks, rate limits, auth patterns discovered     |

#### Validation Checkpoint

**⚠️ CHECKPOINT: Before proceeding to Step 5**

Verify the PlanSynthesizer output:

- [ ] Context section accurately describes what was built
- [ ] Documentation items have actionable draft content (not just "document this")
- [ ] Every SKIP has an explicit, valid reason (not "self-documenting")
- [ ] HIGH priority contradictions have resolution plans
- [ ] All PR comment insights are captured

**If no documentation needed:**

If the synthesized plan shows NO documentation items:

1. Re-read the agent's skip reasons
2. Ask: "Would a future agent benefit from this?"
3. If still no documentation needed, state: "After explicit review of N inventory items, no documentation is needed because [specific reasons for top 3 items]"

Only proceed to Step 7 (skipping Step 5-6) after this explicit justification.

#### Outdated Documentation Check (MANDATORY)

**Removals and behavior changes require doc audits.** When the PR removes features or changes behavior, existing documentation may become incorrect.

**Search for documentation that references changed features:**

```bash
# Search docs for terms related to removed/changed features
grep -r "<removed-feature>" docs/learned/ .claude/commands/ .claude/skills/
```

**Categorize findings:**

| Finding                           | File | Status        | Action Needed          |
| --------------------------------- | ---- | ------------- | ---------------------- |
| Reference to removed feature      | ...  | Outdated      | Remove/update section  |
| Describes old behavior            | ...  | Incorrect     | Update to new behavior |
| Conflicts with new implementation | ...  | Contradictory | Reconcile              |

**Common patterns to check:**

- **Removed CLI flags**: Search for `--flag-name` in docs
- **Removed files/modules**: Search for import paths, file references
- **Changed behavior**: Search for behavioral descriptions that no longer apply
- **Removed modes**: Search for "three modes", "fallback", etc.

**Include outdated doc updates in the documentation plan** alongside new documentation needs.

### Step 5: Present Findings

Present the synthesized plan to the user. The PlanSynthesizer output already includes:

1. **Context section** - What was built and why docs matter
2. **Summary statistics** - Documentation items, contradictions, tripwires
3. **Documentation items** - Prioritized with draft content starters and source attribution ([Plan], [Impl], [PR #N])

**CI Detection**: Check if running in CI/streaming mode by running:

```bash
[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"
```

**If CI mode (CI_MODE)**: Skip user confirmation. Auto-proceed to Step 6 to save the learn plan. This is expected behavior - CI runs should complete without user interaction.

**If interactive mode (INTERACTIVE)**: Confirm with the user before saving the learn plan. If the user decides to skip (no valuable insights), proceed to Step 7.

### Step 6: Validate and Save Learn Plan to GitHub Issue

First validate the synthesized plan has actionable content:

```bash
cat .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md | erk exec validate-plan-content
```

Parse the JSON output:

- If `valid: false` → Skip saving, proceed to Step 6a with `completed_no_plan`
- If `valid: true` → Continue with save below

**If plan is valid**, save it as a GitHub issue:

```bash
# Build command with optional workflow run URL for backlink
CMD="erk exec plan-save-to-issue \
    --plan-type learn \
    --plan-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md \
    --session-id=\"${CLAUDE_SESSION_ID}\" \
    --learned-from-issue <parent-issue-number> \
    --format json"

# Add workflow run URL if set (enables backlink to GitHub Actions run)
if [ -n "$WORKFLOW_RUN_URL" ]; then
    CMD="$CMD --created-from-workflow-run-url \"$WORKFLOW_RUN_URL\""
fi

eval "$CMD"
```

Parse the JSON output to get `issue_number` (the new learn plan issue).

Display the result:

```
Learn plan saved to GitHub issue #<issue_number>

Raw materials: <gist-url>
```

### Step 6b: Store Tripwire Candidates on Learn Plan Issue

**If plan was valid and saved**, store structured tripwire candidates as a metadata comment:

```bash
erk exec store-tripwire-candidates \
    --issue <new-learn-plan-issue-number> \
    --candidates-file .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json
```

This stores the tripwire candidates as a machine-readable metadata block comment on the learn plan issue, enabling `erk land` to read them directly without regex parsing.

Parse the JSON output. If `count` is 0, no comment was added (no candidates found by the extractor). This is normal and not an error.

### Step 6a: Track Learn Result on Parent Plan

**If plan was valid and saved**, update the parent plan's status to link the two issues:

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_with_plan \
    --plan-issue <new-learn-plan-issue-number>
```

This sets `learn_status: completed_with_plan` and `learn_plan_issue: <N>` on the parent plan,
enabling the TUI to show the linked learn plan issue.

**If plan validation failed (no actionable documentation):**

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_no_plan
```

### Step 7: Track Evaluation

**CRITICAL: Always run this step**, regardless of whether you created a plan or skipped.

This ensures `erk land` won't warn about unlearned plans:

```bash
erk exec track-learn-evaluation <issue-number> --session-id="${CLAUDE_SESSION_ID}"
```

### Tips

- Preprocessed sessions use XML: `<user>`, `<assistant>`, `<tool_use>`, `<tool_result>`
- `<tool_result>` elements with errors often reveal the most useful insights
- The more context you include in the issue, the faster the implementing agent can work
