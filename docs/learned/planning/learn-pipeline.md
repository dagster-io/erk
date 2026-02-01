---
title: Learn Pipeline Architecture
read_when:
  - "implementing learn workflow changes"
  - "adding new learn agents"
  - "debugging learn failures"
  - "understanding parallel agent orchestration"
tripwires:
  - action: "launching learn agents without writing outputs to scratch storage"
    warning: "Agent outputs MUST be written to .erk/scratch/sessions/{session_id}/learn-agents/ using Write tool before launching dependent agents. Bash heredoc fails with large outputs."
  - action: "using sequential agent launches when parallel is possible"
    warning: "SessionAnalyzer, CodeDiffAnalyzer, and ExistingDocsChecker can run in parallel. Use run_in_background=true and collect with TaskOutput."
---

# Learn Pipeline Architecture

Complete architecture for erk's automated documentation learning pipeline. This pipeline analyzes implementation sessions to extract insights and create actionable documentation plans.

## Overview

The learn pipeline transforms raw Claude Code session logs into structured documentation plans through a multi-stage analysis process:

1. **Session preprocessing** — Compress JSONL to XML, deduplicate, truncate
2. **Parallel analysis** — Multiple agents extract insights concurrently
3. **Sequential synthesis** — Gap identification and plan generation
4. **Tripwire extraction** — Extract structured tripwire data for automation

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│ INPUT: Plan implementation sessions                                       │
│  - Local: ~/.claude/projects/<project>/sessions/<session-id>.jsonl       │
│  - Remote: GitHub Actions gist uploads (session XML + PR comments)        │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Preprocessing                                                    │
│  - Compress JSONL → XML (dedupe, truncate, prune)                        │
│  - Chunk large sessions (20k token limit per file)                        │
│  - Output: .erk/scratch/sessions/{session_id}/learn/*.xml                │
│  - Upload to secret gist with PR comments                                 │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Parallel Analysis (run_in_background=true)                      │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Agent 1: SessionAnalyzer (per session XML)                         │  │
│  │  Model: haiku                                                      │  │
│  │  Input: session-{id}.xml or session-{id}-part{N}.xml              │  │
│  │  Output: Friction points, patterns, API quirks, design decisions  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Agent 2: CodeDiffAnalyzer (if PR exists)                           │  │
│  │  Model: haiku                                                      │  │
│  │  Input: gh pr diff <pr-number>                                     │  │
│  │  Output: New files, functions, patterns, CLI commands              │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Agent 3: ExistingDocsChecker                                       │  │
│  │  Model: haiku                                                      │  │
│  │  Input: Search hints from plan title                               │  │
│  │  Output: Existing docs, duplicates, contradictions                 │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
│  Note: Outputs written to .erk/scratch/sessions/{id}/learn-agents/       │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Sequential Synthesis                                             │
│                                                                            │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Agent 4: DocumentationGapIdentifier                                │  │
│  │  Model: haiku                                                      │  │
│  │  Depends on: SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker│  │
│  │  Input: All parallel agent outputs                                 │  │
│  │  Output: Deduplicated, prioritized documentation items             │  │
│  │  Writes: gap-analysis.md                                           │  │
│  └─────────────────────┬──────────────────────────────────────────────┘  │
│                        │                                                   │
│                        ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Agent 5: PlanSynthesizer                                           │  │
│  │  Model: opus (creative authoring)                                  │  │
│  │  Depends on: DocumentationGapIdentifier                            │  │
│  │  Input: gap-analysis.md + all session/diff/docs outputs            │  │
│  │  Output: Complete learn plan markdown with narrative context       │  │
│  │  Writes: learn-plan.md                                             │  │
│  └─────────────────────┬──────────────────────────────────────────────┘  │
│                        │                                                   │
│                        ▼                                                   │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ Agent 6: TripwireExtractor                                         │  │
│  │  Model: haiku                                                      │  │
│  │  Depends on: PlanSynthesizer                                       │  │
│  │  Input: learn-plan.md + gap-analysis.md                            │  │
│  │  Output: Structured JSON tripwire candidates                       │  │
│  │  Writes: tripwire-candidates.json                                  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
│                                                                            │
└─────────────────────┬────────────────────────────────────────────────────┘
                      │
                      ▼
┌──────────────────────────────────────────────────────────────────────────┐
│ OUTPUT: Learn plan saved to GitHub                                        │
│  - Issue with erk-plan + erk-learn labels                                │
│  - Tripwire candidates stored as metadata comment                         │
│  - Gist URL linked for raw materials                                      │
│  - Parent plan updated with learn_status                                  │
└──────────────────────────────────────────────────────────────────────────┘
```

## Agent Dependency Graph

The pipeline has strict dependencies to ensure data flows correctly:

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

### Why This Structure?

- **Parallel first**: SessionAnalyzer, CodeDiffAnalyzer, and ExistingDocsChecker extract independent data. Running in parallel saves time.
- **Sequential synthesis**: DocumentationGapIdentifier needs all parallel outputs for deduplication. PlanSynthesizer needs gap analysis for narrative context. TripwireExtractor needs the complete plan for structured extraction.

## Data Flow

### Input: Session Sources

Sessions come from two sources:

1. **Local sessions**: `~/.claude/projects/<project>/sessions/<session-id>.jsonl`
   - Discovered via `erk exec get-learn-sessions`
   - Preprocessed with `erk exec preprocess-session`

2. **Remote sessions**: Uploaded to GitHub gist during remote implementation
   - Discovered via `session_sources` with `source_type: "remote"`
   - Downloaded with `erk exec download-remote-session --gist-url <url>`
   - Then preprocessed like local sessions

### Processing: Compression and Chunking

Session preprocessing (`erk exec preprocess-session`):

- **Compression**: JSONL → XML (deduplicate, truncate, prune)
- **Token limit**: 20k tokens per file (safely under Claude's 25k read limit)
- **Chunking**: Large sessions split into `{prefix}-{session-id}-part{N}.xml`
- **Output naming**: `planning-{session-id}.xml` or `impl-{session-id}.xml`

### Intermediate: Agent Outputs

All agent outputs are written to `.erk/scratch/sessions/{session_id}/learn-agents/`:

- `session-{session-id}.md` — Per-session friction analysis
- `diff-analysis.md` — Code change inventory
- `existing-docs-check.md` — Duplicate/contradiction findings
- `gap-analysis.md` — Deduplicated documentation items
- `learn-plan.md` — Complete learn plan markdown
- `tripwire-candidates.json` — Structured tripwire data

**Critical**: Use the Write tool to save agent outputs. Bash heredoc fails with large outputs (10KB+).

### Output: GitHub Issue

The final learn plan is saved as a GitHub issue with:

- **Labels**: `erk-plan`, `erk-learn`
- **Body**: Complete learn plan markdown from PlanSynthesizer
- **Metadata comment**: Tripwire candidates JSON for automation
- **Gist link**: Raw materials (session XML, PR comments)
- **Parent link**: Learned-from issue number

## Agent Responsibilities

### SessionAnalyzer (Agent 1)

**Purpose**: Extract friction points and patterns from individual sessions

**Input**: Single preprocessed session XML file

**Output**: Markdown report with:

- Friction points (user corrections, repeated searches)
- Patterns discovered in codebase
- Design decisions and reasoning
- External documentation fetched
- Error messages and resolutions

**Model**: haiku (mechanical extraction, pattern matching)

**Why per-session?** Each session may reveal different insights. Parallel processing enables independent analysis.

### CodeDiffAnalyzer (Agent 2)

**Purpose**: Inventory what code actually changed

**Input**: PR diff via `gh pr diff <pr-number>`

**Output**: Markdown report with:

- New files created
- New functions/classes added
- New CLI commands
- New architectural patterns
- Config changes
- External integrations

**Model**: haiku (structured inventory, deterministic)

**Why separate from SessionAnalyzer?** Sessions show how it was built, diffs show what was built. Both perspectives needed.

### ExistingDocsChecker (Agent 3)

**Purpose**: Prevent duplicates and detect contradictions

**Input**: Search hints from plan title (significant nouns/concepts)

**Output**: Markdown report with:

- Existing documentation found
- Duplicate candidates
- Contradictions with existing docs
- Partial overlaps

**Model**: haiku (search and classification)

**Why upfront?** Knowing what already exists prevents duplicate work and ensures consistency.

### DocumentationGapIdentifier (Agent 4)

**Purpose**: Deduplicate and prioritize documentation candidates

**Input**: All parallel agent outputs (session-\*.md, diff-analysis.md, existing-docs-check.md)

**Output**: Markdown report with:

- Deduplicated documentation items
- Prioritization (HIGH/MEDIUM/LOW)
- Classification (NEW_DOC, UPDATE_EXISTING, TRIPWIRE, SKIP)
- Cross-referenced against diff inventory for completeness

**Model**: haiku (rule-based deduplication, explicit criteria)

**Why sequential?** Deduplication requires all parallel inputs to be complete.

### PlanSynthesizer (Agent 5)

**Purpose**: Transform gap analysis into complete learn plan

**Input**: gap-analysis.md + all session/diff/docs outputs

**Output**: Complete learn plan markdown with:

- Narrative context (what was built, why docs matter)
- Documentation items with draft content starters
- Contradiction resolutions
- Prevention insights
- Tripwire candidates (prose)

**Model**: opus (creative authoring, quality-critical final output)

**Why opus?** Plan synthesis requires narrative context and draft content starters. Quality matters for this final user-facing artifact.

### TripwireExtractor (Agent 6)

**Purpose**: Extract structured tripwire data from plan

**Input**: learn-plan.md + gap-analysis.md

**Output**: JSON with structured tripwire candidates:

```json
[
  {
    "title": "Wrong SSH Method Selection",
    "score": 5,
    "trigger": "Before calling run_ssh_command() for an interactive process",
    "warning": "Interactive processes require TTY allocation. Use exec_ssh_interactive()...",
    "recommendation": "TRIPWIRE"
  }
]
```

**Model**: haiku (mechanical extraction, structured data)

**Why separate?** Enables `erk land` to read structured data without regex parsing the plan markdown.

## Critical Implementation Details

### Writing Agent Outputs

**ALWAYS use the Write tool**, not bash heredoc:

```python
# CORRECT
Write(
  file_path: ".erk/scratch/sessions/{session_id}/learn-agents/diff-analysis.md",
  content: <full agent output from TaskOutput>
)

# WRONG - Fails with large outputs
cat > .erk/scratch/sessions/{session_id}/learn-agents/diff-analysis.md <<'EOF'
<agent output>
EOF
```

**Why?** Agent outputs can be 10KB+ of markdown. Bash heredoc fails silently with special characters. Write tool guarantees exact content.

### Verifying Files Exist

**Before launching dependent agents**, verify files were written:

```bash
ls -la .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

If files are missing, the Write tool call failed and must be retried.

### Parallel vs Sequential Execution

**Parallel agents** use `run_in_background=true`:

```python
Task(
  subagent_type: "general-purpose",
  run_in_background: true,  # Run in parallel
  description: "Analyze session <session-id>",
  prompt: "Load and follow .claude/agents/learn/session-analyzer.md"
)
```

**Sequential agents** block until previous agent completes:

```python
# Wait for DocumentationGapIdentifier before launching PlanSynthesizer
Task(
  subagent_type: "general-purpose",
  description: "Synthesize learn plan",
  prompt: "Load and follow .claude/agents/learn/plan-synthesizer.md"
)
```

### Session ID Interpolation

All paths use `${CLAUDE_SESSION_ID}` to isolate per-session scratch storage:

```bash
.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/
.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

## Model Selection Rationale

| Agent                      | Model | Why                                         |
| -------------------------- | ----- | ------------------------------------------- |
| SessionAnalyzer            | haiku | Mechanical extraction, pattern matching     |
| CodeDiffAnalyzer           | haiku | Structured inventory, deterministic         |
| ExistingDocsChecker        | haiku | Search and classification, fast iteration   |
| DocumentationGapIdentifier | haiku | Rule-based deduplication, explicit criteria |
| PlanSynthesizer            | opus  | Creative authoring, quality-critical output |
| TripwireExtractor          | haiku | Mechanical extraction, structured data      |

**Cost optimization**: Use haiku for mechanical tasks (5 of 6 agents). Reserve opus for the single agent that requires creative narrative synthesis.

## CI Integration

The learn pipeline supports both interactive and CI modes:

**Interactive mode** (local):

- User confirms before saving plan
- Post-learn decision menu (submit, review, consolidate, done)

**CI mode** (GitHub Actions):

- Auto-proceeds without user confirmation
- Auto-selects "submit for implementation"
- Detected via `$CI` or `$GITHUB_ACTIONS` environment variables

## Future Enhancements

Possible improvements to the pipeline:

1. **Incremental preprocessing**: Reuse preprocessed sessions across multiple learn runs
2. **Agent result caching**: Cache agent outputs for rapid re-synthesis
3. **Multi-plan consolidation**: Merge overlapping learn plans before implementation
4. **Tripwire auto-insertion**: Automatically add tripwires to category tripwire files

## Related Documentation

- [Agent Delegation](agent-delegation.md) - Parallel agent orchestration patterns
- [Agent Orchestration](agent-orchestration.md) - Multi-agent coordination strategies
- [Erk Learn Command](.claude/commands/erk/learn.md) - User-facing learn workflow
- [Session Analyzer Agent](.claude/agents/learn/session-analyzer.md) - Session analysis spec
- [Plan Synthesizer Agent](.claude/agents/learn/plan-synthesizer.md) - Plan synthesis spec
