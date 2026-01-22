# Documentation Plan: Update /erk:learn to Orchestrate All 5 Agents (Step 1B.4)

## Context

This implementation transformed the `/erk:learn` workflow from a simpler structure into a full 5-agent orchestration system. The key architectural insight is the three-tier dependency model: three analysis agents (SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker) run in parallel to gather raw materials, then DocumentationGapIdentifier synthesizes their outputs sequentially, followed by PlanSynthesizer which transforms the gap analysis into an actionable learn plan.

A significant discovery during implementation was that the prerequisite step (1B.3 - PlanSynthesizer agent) hadn't actually been completed. PR #5577 existed but only contained `.worker-impl/` plan files, not the actual agent implementation. This led to creating the PlanSynthesizer agent as part of this PR, demonstrating the importance of verifying prerequisite completions by examining actual PR content rather than just PR state.

The documentation opportunities from this implementation focus on tripwires (common pitfalls around gh CLI field validation, objective roadmap parsing, and plan metadata verification) and updates to existing docs (parallel agent pattern now uses 5 agents instead of 2, worker-impl detection pattern). The marker pattern for workflow state persistence is the only net-new documentation opportunity.

## Raw Materials

https://gist.github.com/schrockn/d164ed8a945326d9484d97c26bf2e819

## Summary

| Metric                    | Count |
| ------------------------- | ----- |
| Documentation items       | 3     |
| Contradictions to resolve | 0     |
| Tripwires to add          | 4     |

## Documentation Items

### MEDIUM Priority

#### 1. Update parallel-agent-pattern with learn example

**Location:** `docs/learned/architecture/parallel-agent-pattern.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Learn Workflow Example

The `/erk:learn` workflow demonstrates a three-tier agent orchestration:

### Tier 1: Parallel Analysis
- **SessionAnalyzer**: Processes session JSONL to extract patterns, errors, corrections
- **CodeDiffAnalyzer**: Analyzes PR diff for new files, functions, gateway methods
- **ExistingDocsChecker**: Scans docs/learned/ for potential conflicts/updates

### Tier 2: Sequential Synthesis
- **DocumentationGapIdentifier**: Combines all tier 1 outputs, cross-references against existing docs, produces prioritized gap analysis

### Tier 3: Final Synthesis
- **PlanSynthesizer**: Transforms gap analysis into executable learn plan with draft content starters
```

---

#### 2. Worker-impl detection for queued plans

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the "Plan States" or similar section:

```markdown
## Detecting Queued vs Implemented Plans

A PR associated with a plan may exist but not contain the actual implementation:

- **Queued Plan**: PR contains only `.worker-impl/` folder with plan files
- **Implemented Plan**: PR contains actual source code changes

To verify implementation status:
1. Check if PR diff includes changes outside `.worker-impl/`
2. Use `gh pr diff <number>` and look for actual implementation files
3. Don't rely solely on PR state (OPEN/MERGED) - a PR can be open with only plan files

This pattern was discovered when verifying prerequisite PR #5577: the PR existed and was open, but only contained `.worker-impl/` plan files, not the actual PlanSynthesizer agent.
```

---

### LOW Priority

#### 1. Marker pattern for workflow state

**Location:** `docs/learned/planning/workflow-markers.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
title: Workflow Markers
category: planning
read_when:
  - Building multi-step workflows that need state persistence
  - Using erk exec marker commands
  - Implementing objective-to-plan workflows
---

# Workflow Markers

Markers persist state across workflow steps when a single session needs to pass information between distinct phases.

## Commands

- `erk exec marker create --name <name> --value <value>` - Create/update a marker
- `erk exec marker read --name <name>` - Read marker value (empty if not set)

## Use Cases

### Objective Context

When creating a plan from an objective step, markers track the objective for later hooks:

```bash
erk exec marker create --name objective-context --value "5503"
erk exec marker create --name roadmap-step --value "1B.4"
```

The `exit-plan-mode` hook reads `objective-context` to update the objective issue when the plan is saved.

### Workflow State

For multi-phase workflows where information from step N is needed in step N+2:

1. Early step writes marker with computed value
2. Later step reads marker to continue workflow

## Design Principles

- Markers are session-scoped (tied to `CLAUDE_SESSION_ID`)
- Use descriptive names: `objective-context`, `roadmap-step`, `selected-branch`
- Markers survive hook boundaries but not session restarts
```

---

## Contradiction Resolutions

No contradictions detected. The existing documentation in `docs/learned/architecture/parallel-agent-pattern.md` references learn as using "two agents concurrently" which is now outdated (3 parallel + 2 sequential = 5 total), but this is a factual update rather than a conflicting recommendation.

## Tripwire Additions

Add these to the frontmatter of relevant documents:

### For `docs/learned/tripwires.md`

```yaml
tripwires:
  - action: "parsing objective roadmap PR column status"
    warning: "PR column format is non-standard: empty=pending, #XXXX=done (merged PR), `plan #XXXX`=plan in progress. This is erk-specific, not GitHub convention."
```

```yaml
tripwires:
  - action: "using gh pr view --json merged"
    warning: "The `merged` field doesn't exist. Use `mergedAt` instead. Run `gh pr view --help` or check error output for valid field names."
```

```yaml
tripwires:
  - action: "saving a plan with --objective-issue flag"
    warning: "Always verify the link was saved correctly with `erk exec get-plan-metadata <issue> objective_issue`. Silent failures can leave plans unlinked from their objectives."
```

### For `docs/learned/planning/scratch-storage.md`

```yaml
tripwires:
  - action: "analyzing sessions larger than 100k characters"
    warning: "Use `erk exec preprocess-session` first. Achieves ~99% token reduction (e.g., 6.2M -> 67k chars). Critical for fitting large sessions in agent context windows."
```