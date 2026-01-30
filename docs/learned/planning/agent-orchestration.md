---
title: Agent Orchestration for Learn Workflow
read_when:
  - "implementing multi-tier agent workflows"
  - "understanding erk learn parallel analysis pattern"
  - "designing agent dependency graphs"
  - "working with Tier 1/Tier 2 agent patterns"
tripwires:
  - action: "running sequential analysis that could be parallelized"
    warning: "Use Tier 1 parallel agents for independent analysis (code-diff, existing-docs, session). Only use Tier 2 sequential synthesis when results must be combined."
---

# Agent Orchestration for Learn Workflow

The erk learn workflow uses a 2-tier agent orchestration pattern: parallel analysis (Tier 1) feeds sequential synthesis (Tier 2).

## Workflow Architecture

```
                    ┌─────────────────────────┐
                    │   Parent Agent          │
                    │   (erk learn)           │
                    └───────────┬─────────────┘
                                │
                    ┌───────────┴────────────┐
                    │   Tier 1: Parallel     │
                    │   Analysis Agents      │
                    │   (concurrent)         │
                    └───────────┬────────────┘
                    ┌───────────┴────────────┐
              ┌─────┴─────┐  ┌────┴─────┐  ┌────┴─────┐
              │ code-diff │  │ existing │  │ session  │
              │ analyzer  │  │   docs   │  │ analyzer │
              │           │  │ checker  │  │          │
              └─────┬─────┘  └────┬─────┘  └────┬─────┘
                    │             │             │
                    └─────────────┼─────────────┘
                                  │
                    ┌─────────────┴────────────┐
                    │   Tier 2: Sequential     │
                    │   Synthesis Agents       │
                    │   (dependent ordering)   │
                    └─────────────┬────────────┘
              ┌─────────────────┬─┴──┬─────────────────┐
       ┌──────┴─────┐  ┌────────┴────┴───┐  ┌──────────┴────────┐
       │ gap        │  │ plan             │  │ learn             │
       │ identifier │──│ synthesizer      │──│ plan              │
       │            │  │                  │  │ generator         │
       └────────────┘  └──────────────────┘  └───────────────────┘
```

## Tier 1: Parallel Analysis Agents

Tier 1 agents run **concurrently** and perform independent analysis.

### code-diff-analyzer

**Purpose**: Analyze PR diff to identify new features, patterns, and code changes requiring documentation.

**Input**: PR diff, file list

**Output**: List of documentation-worthy items:
- New gateway methods
- New CLI commands
- Architectural patterns
- API changes

**Independence**: Does not depend on other agents.

### existing-docs-checker

**Purpose**: Search existing documentation to identify duplicates and contradictions.

**Input**: Documentation directory, search keywords

**Output**: List of existing docs related to changes, potential duplicates, conflicts

**Independence**: Does not depend on other agents.

### session-analyzer

**Purpose**: Extract patterns, decisions, and insights from preprocessed session XML.

**Input**: Session log (preprocessed from JSONL)

**Output**: Key decisions, implementation patterns, pitfalls discovered, context from conversation

**Independence**: Does not depend on other agents.

### Why Parallel?

These agents analyze different data sources (diff vs docs vs session) with no interdependencies. Running them in parallel reduces total workflow time.

## Tier 2: Sequential Synthesis Agents

Tier 2 agents run **sequentially** and combine Tier 1 outputs.

### gap-identifier

**Purpose**: Synthesize Tier 1 outputs to identify documentation gaps.

**Input**: Outputs from all 3 Tier 1 agents

**Output**: Prioritized list of documentation gaps (HIGH/MEDIUM/LOW)

**Dependency**: **Requires** Tier 1 agents to complete first (code-diff + existing-docs + session).

### plan-synthesizer

**Purpose**: Transform gap analysis into actionable implementation plan markdown.

**Input**: Gap identifier output

**Output**: Learn plan markdown with implementation steps

**Dependency**: **Requires** gap-identifier to complete first.

### learn-plan-generator (if applicable)

**Purpose**: Generate GitHub issue from plan markdown.

**Input**: Plan synthesizer output

**Output**: GitHub issue creation metadata

**Dependency**: **Requires** plan-synthesizer to complete first.

### Why Sequential?

Each Tier 2 agent depends on the previous agent's output. gap-identifier needs all Tier 1 results. plan-synthesizer needs gap analysis. These must run in order.

## Implementation Pattern

### Launching Tier 1 Agents (Parallel)

```python
# Launch all Tier 1 agents concurrently in a single message
Task(
    subagent_type="code-diff-analyzer",
    prompt="Analyze PR diff for documentation needs...",
    run_in_background=True
)
Task(
    subagent_type="existing-docs-checker",
    prompt="Search existing docs for related content...",
    run_in_background=True
)
Task(
    subagent_type="session-analyzer",
    prompt="Extract patterns from session...",
    run_in_background=True
)

# Wait for all to complete
tier1_outputs = [
    TaskOutput(task_id="code-diff-id", block=True),
    TaskOutput(task_id="existing-docs-id", block=True),
    TaskOutput(task_id="session-id", block=True),
]
```

**Key Points**:
- All Tier 1 agents launched in **one message** with `run_in_background=True`
- `TaskOutput(block=True)` waits for each to finish
- Agents run concurrently (not sequentially)

### Launching Tier 2 Agents (Sequential)

```python
# Tier 2.1: Gap Identifier (needs Tier 1 outputs)
gap_output = Task(
    subagent_type="gap-identifier",
    prompt=f"Synthesize gaps from: {tier1_outputs}",
    run_in_background=False  # Wait for completion
)

# Tier 2.2: Plan Synthesizer (needs gap identifier output)
plan_output = Task(
    subagent_type="plan-synthesizer",
    prompt=f"Create plan from gaps: {gap_output}",
    run_in_background=False  # Wait for completion
)

# Tier 2.3: Learn Plan Generator (needs plan output)
final_output = Task(
    subagent_type="learn-plan-generator",
    prompt=f"Generate issue from plan: {plan_output}",
    run_in_background=False
)
```

**Key Points**:
- Each Tier 2 agent waits for previous agent to complete
- `run_in_background=False` makes execution sequential
- Each agent receives output from previous agent

## Benefits of 2-Tier Pattern

### Performance

- **Tier 1 parallelism**: 3 agents finish in ~max(agent_time), not ~sum(agent_time)
- **Example**: If each Tier 1 agent takes 2 minutes, total Tier 1 time is ~2 minutes (not 6)

### Correctness

- **Tier 2 dependencies**: Each synthesis step has all required inputs
- **No race conditions**: Tier 1 completes before Tier 2 starts

### Modularity

- **Agent independence**: Tier 1 agents don't know about each other
- **Reusable**: code-diff-analyzer can be used in other workflows

## When to Use This Pattern

Use 2-tier orchestration when:

1. Multiple independent data sources need analysis (parallel-friendly)
2. Final output requires synthesizing all analysis results (needs sequential combination)
3. Analysis steps are expensive (benefit from parallelism)
4. Synthesis steps are fast relative to analysis (sequential overhead acceptable)

**Counter-examples** (don't use 2-tier):

- Single data source (no parallelism benefit)
- Simple linear pipeline (A → B → C with no fan-out)
- Fast analysis, expensive synthesis (sequential might be simpler)

## Related Documentation

- [Learn Workflow](../erk/learn-workflow.md) - Complete learn workflow documentation (if exists)
- [Task Tool Usage](../claude-code/task-tool.md) - Task tool mechanics (if exists)
- [Agent Patterns](../claude-code/agent-patterns.md) - General agent patterns (if exists)
