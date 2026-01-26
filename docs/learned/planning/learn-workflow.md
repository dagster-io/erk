---
title: Learn Workflow
read_when:
  - "using /erk:learn skill"
  - "understanding learn status tracking"
  - "auto-updating parent plans when learn plans land"
tripwires:
  - action: "modifying learn command to add/remove/reorder agents"
    warning: "Verify tier placement before assigning model. Parallel extraction uses haiku, sequential synthesis may need opus for quality-critical output."
  - action: "adding new agents to learn workflow"
    warning: "Document input/output format and test file passing. Learn workflow uses stateless agents with file-based composition."
---

# Learn Workflow

This guide explains the learn workflow in erk: how `/erk:learn` creates documentation plans, tracks status on parent plans, and enables automatic updates when learn plans are landed.

## Overview

The learn workflow extracts insights from implementation sessions and creates documentation plans. It's part of erk's knowledge capture system.

**Key change**: Learn no longer writes documentation directly. Instead, it creates a plan issue for human review, which is then implemented through the standard `plan-implement` workflow. This gives humans control over documentation quality while maintaining the unified implementation pattern.

```
┌─────────────────┐     /erk:learn      ┌─────────────────┐
│  Parent Plan    │ ─────────────────→  │  Learn Plan     │
│  (erk-plan)     │                     │  (erk-learn)    │
│                 │                     │                 │
│ learn_status:   │                     │ learned_from:   │
│ completed_with_ │ ←─────────────────  │ <parent-issue>  │
│ plan            │      backlink       │                 │
│ learn_plan_     │                     │                 │
│ issue: <N>      │                     │                 │
└─────────────────┘                     └─────────────────┘
         │                                      │
         │                                      │
         │         erk land                     │
         │     ←───────────────────────         │
         │      auto-update on land             │
         ▼                                      ▼
┌─────────────────┐                     ┌─────────────────┐
│ learn_status:   │                     │  PR merged      │
│ plan_completed  │                     │                 │
│ learn_plan_pr:  │                     │                 │
│ <PR-number>     │                     │                 │
└─────────────────┘                     └─────────────────┘
```

## Key Concepts

### Parent Plan

The original implementation plan that `/erk:learn` is invoked on. After learn completes, the parent plan's metadata is updated with:

- `learn_status`: Status of the learning workflow
- `learn_plan_issue`: Issue number of the created learn plan (if any)
- `learn_plan_pr`: PR number that implemented the learn plan (after landing)

### Learn Plan

A documentation plan created by `/erk:learn`. It has the `erk-learn` label and contains:

- `learned_from_issue`: Backlink to the parent plan issue number

This backlink enables automatic status updates when the learn plan is landed.

### Learn Status Values

| Status                | Description                                 |
| --------------------- | ------------------------------------------- |
| `completed_no_plan`   | Learn completed, no documentation needed    |
| `completed_with_plan` | Learn completed, documentation plan created |
| `plan_completed`      | Learn plan was implemented and PR landed    |

## Agent Tier Architecture

The learn workflow orchestrates 5 agents across 3 tiers:

### Parallel Tier (Haiku)

Run simultaneously via `run_in_background: true`:

- **SessionAnalyzer** - Extracts patterns from preprocessed session XML
- **CodeDiffAnalyzer** - Inventories PR changes
- **ExistingDocsChecker** - Searches for duplicates/contradictions

### Sequential Tier 1 (Haiku)

Depends on parallel tier outputs:

- **DocumentationGapIdentifier** - Synthesizes and deduplicates candidates

### Sequential Tier 2 (Opus)

Depends on Sequential Tier 1:

- **PlanSynthesizer** - Creates narrative context and draft content

### Model Selection Rationale

| Tier         | Model | Rationale                                                      |
| ------------ | ----- | -------------------------------------------------------------- |
| Parallel     | Haiku | Mechanical extraction tasks - pattern matching, classification |
| Sequential 1 | Haiku | Rule-based deduplication and prioritization                    |
| Sequential 2 | Opus  | Creative authoring, narrative generation, quality-critical     |

See [Agent Delegation](agent-delegation.md#model-selection) for general model selection guidance.

### Tier Layering Note

The tier structure follows a funnel pattern:

1. **Parallel tier** - Fan-out: multiple agents extract different aspects simultaneously
2. **Sequential tier 1** - Synthesis: combine and deduplicate parallel outputs
3. **Sequential tier 2** - Quality: high-quality narrative generation from synthesized data

Each tier's output feeds into the next. Modifying tier order or moving agents between tiers affects the data flow and model costs.

### Session Preprocessing Validation

Before running learn, sessions are preprocessed via `erk exec preprocess-session`:

1. **Size check**: Sessions larger than 100k characters MUST be preprocessed first
2. **Token reduction**: Preprocessing achieves ~99% reduction (e.g., 6.2M → 67k chars)
3. **Validation**: The learn command validates preprocessed output exists before spawning analysis agents

If preprocessing fails or produces malformed output, learn agents will fail to extract meaningful data.

## The Learn Flow

### Step 1: Run /erk:learn on Parent Plan

```bash
/erk:learn <parent-issue-number>
```

The skill:

1. Analyzes sessions associated with the parent plan
2. Identifies documentation gaps via multi-agent analysis
3. Creates a learn plan issue (if documentation needed)
4. The plan issue is queued for human review before implementation

**Note**: Learn runs inline during the `plan-implement` workflow after successful implementation. It does NOT write documentation directly - it creates a plan issue for later review and implementation.

### Step 2: Track Learn Result

After creating the learn plan, the skill calls:

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_with_plan \
    --plan-issue <learn-plan-issue-number>
```

This sets `learn_status` and `learn_plan_issue` on the parent plan.

If no documentation was needed:

```bash
erk exec track-learn-result \
    --issue <parent-issue-number> \
    --status completed_no_plan
```

### Step 3: Learn Plan Links Back

When creating the learn plan, the `--learned-from-issue` flag is passed:

```bash
erk exec plan-save-to-issue \
    --plan-type learn \
    --learned-from-issue <parent-issue-number> \
    ...
```

This sets `learned_from_issue` in the learn plan's metadata, creating a bidirectional link.

### Step 4: Human Review and Submit

After the learn plan issue is created, a human reviews it and decides whether to implement:

1. Review the plan issue - it contains draft content starters and documentation suggestions
2. Optionally edit the plan to adjust priorities or content
3. Submit via `erk plan submit` to queue for implementation

### Step 5: Implement and Land Learn Plan

The learn plan is implemented via the normal `plan-implement` workflow (same as any other plan).

When the PR is landed via `erk land`:

1. The land command detects `learned_from_issue` in the plan header
2. It calls `_update_parent_plan_on_learn_plan_land()`
3. The parent plan's status is updated:
   - `learn_status` → `plan_completed`
   - `learn_plan_pr` → PR number

## TUI Integration

The TUI shows learn status in the "lrn" column:

| Display | Meaning                     |
| ------- | --------------------------- |
| (empty) | Not learned yet             |
| `#N`    | Learn created plan issue #N |
| `✓ #PR` | Learn plan landed in PR #PR |

Clicking the cell opens the learn plan issue or PR.

## Related Commands

- `/erk:learn` - Run learn workflow on a plan
- `erk exec track-learn-result` - Update parent plan's learn status
- `erk exec track-learn-evaluation` - Track that learn was invoked
- `erk land` - Land PR with automatic parent plan updates

## Metadata Fields

### On Parent Plans

```yaml
learn_status: completed_with_plan # or completed_no_plan, plan_completed
learn_plan_issue: 123 # Issue number of learn plan
learn_plan_pr: 456 # PR number (after landing)
last_learn_at: 2025-01-21T... # Timestamp of last learn invocation
last_learn_session: abc123 # Session ID that ran learn
```

### On Learn Plans

```yaml
learned_from_issue: 100 # Parent plan issue number
```

## Learn Plan Parent Branch Stacking

When a learn plan is submitted via `erk plan submit`, it automatically stacks on its parent plan's branch rather than trunk.

### Auto-Detection

The submit command calls `get_learn_plan_parent_branch()` which:

1. Extracts `learned_from_issue` from the learn plan's metadata
2. Fetches the parent plan issue
3. Returns the parent plan's `branch_name` from its plan-header

### How It Works

```
trunk (main)
    └── P123-feature-branch (parent plan)
            └── P456-docs-for-feature (learn plan)
```

This stacking ensures learn plan PRs can be reviewed and merged after their parent features land.

### Fallback Behavior

If the parent branch lookup fails (parent issue missing, no branch recorded, etc.), the learn plan falls back to being based on trunk. This is graceful degradation - the plan can still be implemented, just not stacked.

### Implementation Reference

See `get_learn_plan_parent_branch()` in `src/erk/cli/commands/submit.py`.

## CI Environment Behavior

The learn workflow detects CI environments to skip interactive prompts:

```bash
# CI detection
[ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ] && echo "CI_MODE" || echo "INTERACTIVE"
```

**In CI mode:**

- User confirmations are skipped
- Auto-proceeds to save learn plan issue
- No blocking prompts that would hang the workflow

**In interactive mode:**

- User confirms before saving the learn plan
- Can choose to skip if no valuable insights

See [CI-Aware Commands](../cli/ci-aware-commands.md) for the general CI detection pattern.

## Agent Input/Output Formats

The learn workflow uses stateless agents with file-based composition. Each agent reads from scratch storage and writes structured output.

### SessionAnalyzer

**Input:**

- `session_xml_path`: Path to preprocessed session XML
- `context`: Brief description from plan title

**Output:** Structured markdown with:

- Key discoveries (files read, patterns found)
- Error resolutions
- Design decisions
- External documentation fetched

### CodeDiffAnalyzer

**Input:**

- `pr_number`: Pull request number
- `issue_number`: Plan issue number

**Output:** Inventory markdown with:

- New files created
- New functions/classes added
- New CLI commands
- Config changes

### ExistingDocsChecker

**Input:**

- `plan_title`: Title from plan issue
- `pr_title`: PR title (if available)
- `search_hints`: Key terms for searching

**Output:** Report with:

- Existing docs found
- Potential duplicates
- Contradiction candidates

### DocumentationGapIdentifier

**Input:**

- `session_analysis_paths`: List of session analysis file paths
- `diff_analysis_path`: Path to diff analysis (or null)
- `existing_docs_path`: Path to existing docs check
- `plan_title`: Title from plan issue

**Output:** Enumerated table with:

- Classification (NEW_DOC, UPDATE_EXISTING, TRIPWIRE, SKIP)
- Priority (HIGH, MEDIUM, LOW)
- Deduplication status (ALREADY_DOCUMENTED, PARTIAL_OVERLAP, NEW_TOPIC)

### PlanSynthesizer

**Input:**

- `gap_analysis_path`: Path to gap analysis
- `session_analysis_paths`: Session analysis file paths
- `diff_analysis_path`: Diff analysis path (or null)
- `plan_title`: Title from plan issue
- `gist_url`: Gist URL with raw materials
- `pr_number`: PR number (or null)

**Output:** Complete learn plan markdown with:

- Context section
- Summary statistics
- Documentation items with draft content starters
- Tripwire additions formatted for copy-paste

## Stateless File-Based Composition

The learn workflow uses a **stateless file-based composition** pattern:

### Why Stateless?

1. **Parallelism**: Agents run in background with no shared state
2. **Resumability**: If one agent fails, others' outputs are preserved
3. **Debuggability**: Intermediate outputs saved to scratch storage for inspection
4. **Token efficiency**: Each agent gets only the context it needs

### File Flow

```
Session preprocessing
    └── .erk/scratch/sessions/{session-id}/learn/*.xml

Parallel agents
    └── .erk/scratch/sessions/{session-id}/learn-agents/
            ├── session-*.md      (SessionAnalyzer outputs)
            ├── diff-analysis.md  (CodeDiffAnalyzer output)
            └── existing-docs-check.md (ExistingDocsChecker output)

Sequential agents
    └── .erk/scratch/sessions/{session-id}/learn-agents/
            ├── gap-analysis.md   (DocumentationGapIdentifier output)
            └── learn-plan.md     (PlanSynthesizer output)
```

### Composition Guarantees

- Each agent receives explicit file paths as input
- Write tool (not bash heredoc) ensures reliable large content writes
- File existence verified before launching dependent agents
