---
title: Agent Coordination via Files
read_when:
  - "coordinating multiple agents through file handoffs"
  - "implementing parallel agent workflows"
  - "understanding learn workflow agent architecture"
  - "designing stateless agent pipelines"
---

# Agent Coordination via Files

Pattern for coordinating stateless agents through file-based handoffs, enabling parallel execution and composable workflows.

## Core Principle

Agents are **stateless**. They receive input via files, produce output to files, and have no shared memory. Coordination happens through the filesystem.

```
Agent A writes → file.md → Agent B reads
```

## Scratch Storage Structure

Agent workflows use session-scoped scratch directories:

```
.erk/scratch/sessions/<session-id>/learn/
├── planning-abc123.xml       # Preprocessed session (input)
├── impl-def456.xml           # Preprocessed session (input)
├── session-abc123.md         # Session analyzer output
├── session-def456.md         # Session analyzer output
├── diff-analysis.md          # Code diff analyzer output
├── existing-docs-check.md    # Existing docs checker output
├── gap-analysis.md           # Gap identifier output
└── learn-plan.md             # Final synthesized plan
```

## Tiered Agent Architecture

Complex workflows use tiers to manage dependencies:

### Parallel Tier (Independent Analysis)

Agents that can run simultaneously with no dependencies:

```markdown
### Launch Parallel Agents

Task(
  subagent_type: "session-analyzer",
  run_in_background: true,
  prompt: "Analyze session at {path}. Write to {output_path}."
)

Task(
  subagent_type: "code-diff-analyzer",
  run_in_background: true,
  prompt: "Analyze PR diff. Write to diff-analysis.md."
)

Task(
  subagent_type: "existing-docs-checker",
  run_in_background: true,
  prompt: "Check existing docs. Write to existing-docs-check.md."
)
```

### Sequential Tier (Dependent Synthesis)

Agents that require outputs from parallel tier:

```markdown
### Wait for Parallel Agents

TaskOutput(task_id="session-analyzer-1", block=true)
TaskOutput(task_id="code-diff-analyzer", block=true)
TaskOutput(task_id="existing-docs-checker", block=true)

### Launch Synthesis Agent

Task(
  subagent_type: "gap-identifier",
  prompt: "Read session-*.md, diff-analysis.md, existing-docs-check.md.
           Synthesize into gap-analysis.md."
)
```

## File Handoff Pattern

### Producer Agent

Writes structured output to known path:

```markdown
## Output Format

Write your analysis to: `.erk/scratch/sessions/{session_id}/learn/session-{id}.md`

Structure:
- ## Decisions Made
- ## Patterns Discovered
- ## Potential Documentation
```

### Consumer Agent

Reads from expected paths:

```markdown
## Input Files

Read these files before analysis:
- `.erk/scratch/sessions/{session_id}/learn/session-*.md`
- `.erk/scratch/sessions/{session_id}/learn/diff-analysis.md`

Synthesize insights from all inputs.
```

## Model Selection by Tier

Different tiers use different models based on task complexity:

| Tier | Model | Task Type |
|------|-------|-----------|
| Parallel extraction | haiku | Mechanical pattern matching |
| Sequential dedup | haiku | Rule-based filtering |
| Creative synthesis | opus | Quality-critical authoring |

```markdown
Task(
  subagent_type: "session-analyzer",
  model: "haiku",  # Cheap, fast extraction
  ...
)

Task(
  subagent_type: "plan-synthesizer",
  model: "opus",  # High-quality synthesis
  ...
)
```

## Chunking Large Inputs

For large sessions, preprocess into chunks:

```bash
erk exec preprocess-session --session-id abc123 --chunk-size 50000
```

This creates:

```
learn/
├── impl-abc123.xml
├── impl-abc123-part2.xml
└── impl-abc123-part3.xml
```

Each chunk gets its own analyzer agent instance.

## Benefits

1. **Parallelism** - Independent agents run simultaneously
2. **Debuggability** - Intermediate outputs visible in files
3. **Resumability** - Can restart from any tier
4. **Testability** - Feed test inputs, verify file outputs
5. **Composability** - Reuse agents across workflows

## Design Guidelines

### Clear File Contracts

Document exact paths and formats:

```markdown
**Input:** `.erk/scratch/sessions/{session_id}/learn/session-*.md`
**Output:** `.erk/scratch/sessions/{session_id}/learn/gap-analysis.md`
```

### Atomic Writes

Agents should write complete files, not append:

```python
# GOOD - atomic write
output_path.write_text(complete_content)

# BAD - incremental append
with open(output_path, "a") as f:
    f.write(partial_content)
```

### Deterministic Naming

Use consistent naming patterns:

```
session-{session_id}.md      # Session analysis
diff-analysis.md             # Single file, no ID needed
gap-analysis.md              # Single synthesized output
```

## Example: Learn Workflow

The learn workflow demonstrates this pattern:

```
┌─────────────────────────────────────────────────────────┐
│                    PARALLEL TIER                        │
│   (haiku - mechanical extraction)                       │
├─────────────────────────────────────────────────────────┤
│ SessionAnalyzer  CodeDiffAnalyzer  ExistingDocsChecker │
│       ↓                 ↓                  ↓            │
│ session-*.md      diff-analysis.md  existing-docs.md   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 SEQUENTIAL TIER 1                       │
│   (haiku - rule-based deduplication)                    │
├─────────────────────────────────────────────────────────┤
│              DocumentationGapIdentifier                 │
│                         ↓                               │
│                  gap-analysis.md                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│                 SEQUENTIAL TIER 2                       │
│   (opus - creative authoring)                           │
├─────────────────────────────────────────────────────────┤
│                   PlanSynthesizer                       │
│                         ↓                               │
│                   learn-plan.md                         │
└─────────────────────────────────────────────────────────┘
```

See `.claude/commands/erk/learn.md` for the complete implementation.

## Related Topics

- [Scratch Storage](scratch-storage.md) - Session-scoped storage API
- [Learn Workflow](learn-workflow.md) - Complete learn workflow
- [Skill-Based CLI Pattern](../architecture/skill-based-cli.md) - CLI-to-skill delegation
