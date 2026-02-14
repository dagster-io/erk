# Documentation Plan: Make /erk:learn context-efficient by having agents self-write outputs

## Context

The `/erk:learn` command orchestrates a 7-agent pipeline that analyzes implementation sessions, extracts documentation gaps, and produces learn plans. Prior to this work, the parent orchestrator suffered from a "content relay" anti-pattern: it would read each agent's full output via `TaskOutput`, then write it to scratch storage via `Write`, causing every agent's output (5-15KB each) to appear twice in the parent's context window -- once as a tool result, once as a tool parameter. The parent never reasoned about this content; it was purely mechanical relay work that bloated context by 60-180K tokens.

The fix was to have agents write their own output files and return only short confirmations. This required adding `Write` to agent frontmatter, passing `output_path` as a Task parameter, and embedding "Output Routing" instructions in orchestrator Task prompts. The implementation took an interesting architectural turn: the initial approach modified agent files directly (adding output sections and parameters), but user feedback redirected toward an orchestrator-controlled approach where agents remain generic and the orchestrator's Task prompts control output routing. This preserves agent reusability across contexts that may want different output handling.

The implementation surfaced several non-obvious lessons: frontmatter governs tool access even for general-purpose agents, `gt sync` can create WIP commits that lose uncommitted changes, and automated review bots can produce false positives that should be investigated before acting on. These lessons, along with the core self-write pattern, need to be captured in documentation to prevent future agents from re-discovering them.

## Raw Materials

https://gist.github.com/schrockn/266b74209211e84c7a5236ad1704ceed

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 16    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Stale Documentation Cleanup

No stale documentation detected. All referenced code artifacts in existing docs were verified as current.

## Contradiction Resolutions

No contradictions found. Existing documentation is consistent with the new implementation.

## Documentation Items

### HIGH Priority

#### 1. Context Efficiency and the Content Relay Anti-Pattern

**Location:** `docs/learned/architecture/context-efficiency.md`
**Action:** CREATE
**Source:** [Plan] [Impl] [PR #6949]

**Draft Content:**

```markdown
---
title: Context Efficiency in Multi-Agent Pipelines
read_when:
  - "designing multi-agent orchestration commands"
  - "parent context is being exhausted or compacted during agent pipelines"
  - "choosing how agents should return their results"
tripwires:
  - action: "reading agent output with TaskOutput then writing it to a file with Write"
    warning: "This is the content relay anti-pattern. Content appears twice in parent context (tool result + tool parameter) with no reasoning benefit. Have agents write their own outputs instead."
---

# Context Efficiency in Multi-Agent Pipelines

## The Content Relay Anti-Pattern

When a parent orchestrator calls TaskOutput(block: true) to read an agent's result, then Write(content) to persist it, the content flows through the parent's context twice: once as the TaskOutput tool result, once as the Write tool parameter. The parent never reasons about this content — it is purely mechanical relay. For N agents producing K tokens each, the parent accumulates 2NK tokens of relay overhead.

## The Self-Write Solution

Instead of relaying content, have agents write their own output files:

1. Parent creates output directory before launching agents
2. Parent passes output_path to each agent via Task prompt
3. Parent includes Output Routing instructions telling the agent to write to output_path and return only a short confirmation
4. Parent verifies files exist with a single ls -la call after all agents complete

## Token Impact

<!-- Source: .claude/commands/erk/learn.md, Output Routing sections -->

The /erk:learn command reduced parent context from ~105-262K tokens to ~35-53K tokens (3-5x reduction) by applying this pattern to 7 agents. Each agent produces 5-15K tokens of analysis, so the relay overhead was 6 agents x 2 copies x 5-15K = 60-180K tokens eliminated.

## When to Apply

Use self-write when:
- Parent orchestrates N agents producing large outputs (>1KB each)
- Parent does not need to reason about intermediate outputs
- Parent only needs final synthesis or specific outputs

Keep relay (TaskOutput) when:
- Parent needs to make decisions based on agent output content
- Output is small (<1KB) and the relay overhead is negligible
- Agent output determines which subsequent agents to launch

## Related Documentation

- [Agent Orchestration Safety](../planning/agent-orchestration-safety.md) — File-based handoff patterns
- [Multi-Tier Agent Orchestration](../planning/agent-orchestration.md) — Pipeline design
- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Embedded-prompt vs agent-file tradeoff
```

---

#### 2. Agent Output Routing Strategies

**Location:** `docs/learned/planning/agent-output-routing-strategies.md`
**Action:** CREATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

```markdown
---
title: Agent Output Routing Strategies
read_when:
  - "deciding whether to embed output instructions in agent files or orchestrator Task prompts"
  - "modifying agent definitions to control where output goes"
  - "designing reusable agents that may be called from multiple contexts"
tripwires:
  - action: "adding output_path or Output Routing sections to agent definition files"
    warning: "Consider whether this agent is single-purpose or general-purpose. For general-purpose agents, embed routing instructions in the orchestrator's Task prompt to preserve reusability."
---

# Agent Output Routing Strategies

When agents need to write their own outputs, there are two strategies for controlling where and how they write. The choice depends on whether the agent is single-purpose or general-purpose.

## Strategy 1: Embedded-Prompt (Preferred for General-Purpose Agents)

The orchestrator's Task prompt includes output routing instructions. The agent definition remains clean and context-independent.

**How it works:** The orchestrator adds an "Output Routing" section to each Task prompt, telling the agent to write to a specific output_path and return only a confirmation message. The agent's own definition file does not mention output routing at all.

<!-- Source: .claude/commands/erk/learn.md, search for "## Output Routing" -->

See the Output Routing blocks in `.claude/commands/erk/learn.md` for the canonical implementation. Each Task prompt includes the routing instructions inline.

**Advantages:**
- Agent remains reusable across contexts with different output needs
- Single file to modify (orchestrator) instead of N agent files
- Output behavior is visible at the orchestration layer

**Disadvantages:**
- Requires consistent orchestrator discipline (every Task call must include routing)
- If orchestrator forgets the instructions, agent returns full content to parent

## Strategy 2: Agent-File (For Single-Purpose Agents)

The agent definition itself includes output_path in its Input section and an Output section with self-write instructions.

**How it works:** The agent file declares output_path as an input parameter and includes instructions to write output and return only a confirmation. The orchestrator only needs to pass the path.

**Advantages:**
- Guaranteed behavior — agent always self-writes regardless of orchestrator
- Less orchestrator boilerplate per Task call

**Disadvantages:**
- Reduces agent reusability (hardcoded to always self-write)
- Multiple files to modify when changing the pattern

## Decision Framework

| Agent characteristic | Strategy | Rationale |
|---------------------|----------|-----------|
| Called from multiple orchestrators | Embedded-prompt | Preserves flexibility |
| Single-purpose, one orchestrator | Either works | Choose based on preference |
| Output behavior must be guaranteed | Agent-file | No orchestrator discipline required |
| Orchestrator already has complex Task prompts | Agent-file | Avoids prompt bloat |

## The Output Routing Template

When using the embedded-prompt strategy, include this block in each Task prompt:

See the "Output Routing" sections in `.claude/commands/erk/learn.md` for the standardized template that tells agents to write to output_path, return only confirmation, and not include analysis content in their final message.

## Related Documentation

- [Context Efficiency](../architecture/context-efficiency.md) — Why self-write matters
- [Agent Orchestration Safety](agent-orchestration-safety.md) — File-based handoff patterns
- [Command-Agent Delegation](agent-delegation.md) — When to delegate vs inline
```

---

#### 3. Tool Restriction Safety: Frontmatter Must Match Tool Usage (Tripwire)

**Location:** `docs/learned/commands/tool-restriction-safety.md`
**Action:** UPDATE
**Source:** [PR #6949]

**Draft Content:**

Add a new section after "The Minimal-Set Principle" titled "Frontmatter Must Match All Tool Invocations":

```markdown
## Frontmatter Must Match All Tool Invocations

When agent instructions (either in the agent file or in the orchestrator's Task prompt) tell the agent to use a specific tool, that tool MUST appear in the agent's allowed-tools frontmatter. Claude Code enforces allowed-tools at runtime — a tool call outside the allowed set fails silently or with a non-obvious error.

This is the inverse of the minimal-set principle: while you should not add tools the agent doesn't need, you must not omit tools the agent does need. In PR #6949, six agents gained Write instructions but initially lacked Write in their frontmatter, which would have caused silent failures at runtime.

**Verification pattern:** Before launching agents, audit each agent's instructions for tool invocations (Write, Bash, Grep, etc.) and cross-check against the allowed-tools frontmatter list. This applies to both agent-file instructions and embedded Task prompt instructions.

<!-- Source: .claude/agents/learn/session-analyzer.md, frontmatter -->

See the frontmatter in any `.claude/agents/learn/*.md` file for examples of allowed-tools lists that include Write for self-writing agents.
```

Also add a new tripwire to the frontmatter:

```yaml
- action: "adding tool invocations to agent instructions without updating frontmatter"
  warning: "allowed-tools frontmatter MUST include every tool the agent's instructions reference. Missing tools cause silent runtime failures."
```

---

#### 4. Missing Frontmatter Detection (Tripwire)

**Location:** `docs/learned/commands/tool-restriction-safety.md`
**Action:** UPDATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

Add a section "Frontmatter Completeness Requirement":

```markdown
## Frontmatter Completeness Requirement

All agent files in `.claude/agents/` MUST have a YAML frontmatter block with at minimum: name, description, and allowed-tools. An agent file without frontmatter will be treated as a plain markdown prompt with no tool restrictions or metadata, which can lead to unpredictable behavior.

In PR #6949, the tripwire-extractor agent was discovered to be missing its entire frontmatter block. This was a silent failure — the agent ran but without the metadata that Claude Code uses for tool restriction and identity.

**Prevention:** When creating new agent files, always start with the frontmatter template. When reviewing PRs that add or modify agents, verify frontmatter presence.
```

Also add a new tripwire to the frontmatter:

```yaml
- action: "creating new agent files in .claude/agents/"
  warning: "All agent files MUST have YAML frontmatter with name, description, and allowed-tools. Missing frontmatter causes silent behavioral failures."
```

---

#### 5. Git Sync Losing Working Tree Changes (Tripwire)

**Location:** `docs/learned/workflows/git-sync-state-preservation.md`
**Action:** CREATE
**Source:** [Impl]

Note: `docs/learned/workflows/tripwires.md` is auto-generated from frontmatter. The tripwire is defined in the new document's frontmatter and will propagate to the tripwires index via `erk docs sync`.

**Draft Content:**

```markdown
---
title: Git Sync State Preservation
read_when:
  - "running gt sync or gt rebase during active development"
  - "working tree has uncommitted changes when syncing"
tripwires:
  - action: "running gt sync with uncommitted changes in the working tree"
    warning: "gt sync can rebase and create WIP commits that lose uncommitted working tree changes. Always commit or stash before sync, and verify git status after."
---

# Git Sync State Preservation

## The Problem

When running `gt sync` while the working tree has uncommitted changes, the sync operation may rebase commits and create WIP commits that do not preserve the working tree state. The result is that uncommitted edits are silently lost — no error message, no warning.

## When This Happens

This occurs specifically when:
1. Your branch has diverged from its remote tracking branch
2. You have uncommitted changes in the working tree
3. `gt sync` performs a rebase to reconcile the divergence

The rebase creates a clean commit state, and uncommitted changes that were in the working tree are not carried forward.

## Prevention

1. **Before sync:** Always commit or stash all working tree changes
2. **After sync:** Always run `git status` to verify the working tree state
3. **If changes are lost:** Re-apply edits from memory or from the reflog

## Related Documentation

- [Agent Orchestration Safety](../planning/agent-orchestration-safety.md) — Verification patterns between pipeline steps
```

---

### MEDIUM Priority

#### 6. Output Routing Instruction Protocol

**Location:** `docs/learned/commands/agent-patterns.md`
**Action:** CREATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

```markdown
---
title: Agent Output Routing Patterns
read_when:
  - "adding output routing to Task prompts for self-writing agents"
  - "creating standardized instruction blocks for agent pipelines"
  - "designing commands that orchestrate multiple agents"
---

# Agent Output Routing Patterns

## The Output Routing Instruction Block

When orchestrating agents that should write their own outputs, include a standardized Output Routing section in each Task prompt. This tells the agent where to write, what format to use for confirmation, and what not to do (return full content).

<!-- Source: .claude/commands/erk/learn.md, search for "## Output Routing" -->

See the "Output Routing" sections in `.claude/commands/erk/learn.md` for the canonical template. The block includes three critical instructions: write to output_path, return only confirmation text, and do not return analysis content in the final message.

## Template Components

The Output Routing block has three required elements:
1. **Write directive** — tells agent to use Write tool to save output to the specified path
2. **Confirmation format** — specifies the exact short message to return (e.g., "Output written to <path>")
3. **Prohibition** — explicitly forbids returning full content in the final message

## When to Use

Use Output Routing blocks when:
- Agents produce large outputs (>1KB) that parent does not need to reason about
- Multiple agents run in parallel and their outputs are consumed by a later synthesis step
- Parent context budget is a concern

## Related Documentation

- [Context Efficiency](../architecture/context-efficiency.md) — Why self-write matters for token budgets
- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Embedded-prompt vs agent-file approaches
```

---

#### 7. output_path Task Parameter Convention

**Location:** `docs/learned/planning/agent-delegation.md`
**Action:** UPDATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

Add a new section "Task Parameters for Self-Writing Agents" after the "Background Agent Synchronization" section:

```markdown
## Task Parameters for Self-Writing Agents

When agents write their own outputs (instead of returning content to the parent), pass `output_path` as a Task parameter. This tells the agent where to write its output file.

**Pattern:**
- Create the output directory before launching agents: `mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/`
- Pass output_path in the Task input block, pointing to a unique file in that directory
- Include Output Routing instructions in the Task prompt (see [Agent Output Routing Patterns](../commands/agent-patterns.md))
- After all agents complete, verify files exist with `ls -la` instead of reading full content via TaskOutput

<!-- Source: .claude/commands/erk/learn.md, search for "output_path:" -->

See the Task calls in `.claude/commands/erk/learn.md` for the canonical implementation of this pattern across 7 agents.

**Key insight:** Use `ls -la` batch verification instead of TaskOutput reads. This confirms files exist without loading their content into parent context.
```

---

#### 8. Parent Verification: ls -la Batch Pattern

**Location:** `docs/learned/planning/agent-orchestration-safety.md`
**Action:** UPDATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

Add a section after "The Three-Step Handoff Pattern" titled "Lightweight Verification with ls -la":

```markdown
## Lightweight Verification with ls -la

The three-step handoff pattern uses `ls` to verify file existence. For self-writing agents, this can be further optimized: instead of verifying one file at a time, use a single `ls -la` on the output directory to batch-verify all expected files at once.

<!-- Source: .claude/commands/erk/learn.md, search for "ls -la .erk/scratch" -->

See the verification step in `.claude/commands/erk/learn.md` for an example where a single `ls -la` call confirms all 7 agent output files exist.

**Previous approach (content relay):** Parent reads each agent's full output via TaskOutput to verify success, then writes to file. Content appears twice in parent context.

**Current approach (self-write):** Agents write files directly, parent runs one `ls -la` to confirm. No content enters parent context during verification.

This is a refinement of the verify step in the three-step handoff pattern, not a replacement. The principle remains the same: fail fast at the orchestration layer before launching dependent agents.
```

---

#### 9. Self-Writing Agent Pattern Formalization

**Location:** `docs/learned/planning/agent-orchestration-safety.md`
**Action:** UPDATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

Add a section "The Self-Write Extension" after "The Three-Step Handoff Pattern":

```markdown
## The Self-Write Extension

The three-step handoff pattern assumes the parent writes files on behalf of agents. The self-write extension shifts step 1 to the agent itself:

**Original three-step handoff:**
1. Parent calls TaskOutput to read agent result, then Write to persist it
2. Parent verifies file exists
3. Parent passes path to dependent agent

**Self-write extension:**
1. Agent writes its own output to output_path (received via Task prompt)
2. Parent verifies file exists (using ls -la batch check)
3. Parent passes path to dependent agent

The critical difference: step 1 no longer flows content through the parent. The agent writes directly, and the parent only sees a short confirmation message. This eliminates the content relay overhead described in [Context Efficiency](../architecture/context-efficiency.md).

<!-- Source: .claude/commands/erk/learn.md, search for "## Output Routing" -->

See the Output Routing sections in `.claude/commands/erk/learn.md` for the canonical implementation where 7 agents use this pattern.
```

---

#### 10. Inline Agent Self-Writing Pattern

**Location:** `docs/learned/commands/inline-agent-patterns.md`
**Action:** CREATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

```markdown
---
title: Inline Agent Patterns
read_when:
  - "defining agents inline within command files instead of as separate agent files"
  - "adding output routing to agents defined directly in orchestrator commands"
---

# Inline Agent Patterns

## Inline vs File-Based Agents

Most agents in erk are defined as separate files in `.claude/agents/`. However, some agents are defined inline within command files — their instructions appear directly in the orchestrator's Task prompt rather than referencing an external agent file.

## Output Routing for Inline Agents

Inline agents need the same output routing as file-based agents, but the mechanism differs:

**File-based agents:** Routing instructions are embedded in the Task prompt by the orchestrator (embedded-prompt strategy) or in the agent file itself (agent-file strategy).

**Inline agents:** Routing instructions are part of the inline agent definition within the command file. Since there is no separate agent file, there is no frontmatter to set allowed-tools — the agent inherits tool access from how it is launched.

<!-- Source: .claude/commands/erk/learn.md, search for "PR Comment Analyzer" -->

See the PR Comment Analyzer (Agent 4) in `.claude/commands/erk/learn.md` for an example of an inline agent with output routing. It receives output_path and includes the same Output Routing instructions as file-based agents.

## When to Use Inline Agents

| Characteristic | File-based | Inline |
|---------------|-----------|--------|
| Reused across commands | Yes | No |
| Has complex instructions | Yes | Maybe |
| Single-use, tightly coupled to orchestrator | No | Yes |
| Needs its own frontmatter/metadata | Yes | N/A |

## Related Documentation

- [Agent Output Routing Strategies](../planning/agent-output-routing-strategies.md) — Embedded-prompt vs agent-file approaches
- [Command-Agent Delegation](../planning/agent-delegation.md) — When to delegate to agents
```

---

#### 11. Multi-Layer Exploration Strategy

**Location:** `docs/learned/planning/exploration-strategies.md`
**Action:** CREATE
**Source:** [Plan]

**Draft Content:**

```markdown
---
title: Multi-Layer Exploration Strategies
read_when:
  - "planning an implementation that requires understanding multiple code areas"
  - "using nested Task(Explore) agents for information gathering"
  - "designing planning workflows that need comprehensive context"
---

# Multi-Layer Exploration Strategies

## The Pattern

Before entering Plan mode for complex tasks, use nested Task(Explore) agents to gather comprehensive information from multiple code areas. Each Explore agent targets a different aspect of the system, and their results inform the planning phase.

## When to Use

Use multi-layer exploration when:
- The task spans multiple files or subsystems
- Understanding the current implementation is required before planning changes
- Multiple independent questions need answering before a coherent plan can be formed

## Example: Context Efficiency Diagnosis

The planning session for PR #6949 used two nested Explore agents before entering Plan mode:
1. First Explore agent: Analyzed the learn command implementation to understand where context consumption occurred
2. Second Explore agent: Examined agent definitions and the existing self-write precedent (tripwire-extractor)

The Explore agents gathered enough context to diagnose the content relay anti-pattern and calculate exact token overhead (6 agents x 2 copies x 5-15K = 60-180K tokens), which then informed the plan.

## Key Principle

Explore agents are cheap — they run at lower model tiers and their output stays in the planning context. The alternative (loading all files directly into the main conversation) is more expensive and less organized. Delegate exploration to subagents, then synthesize their findings into a coherent plan.

## Related Documentation

- [Agent Delegation](agent-delegation.md) — When to delegate to agents
- [Context Efficiency](../architecture/context-efficiency.md) — Why context management matters
```

---

#### 12. Prettier as Markdown Formatting Authority

**Location:** `docs/learned/ci/prettier-fixes.md`
**Action:** CREATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

```markdown
---
title: Prettier as Markdown Formatting Authority
read_when:
  - "CI fails with prettier formatting violations"
  - "prettier restores content you removed"
  - "deciding whether to fight prettier's formatting decisions"
tripwires:
  - action: "removing content that prettier restores on formatting"
    warning: "When prettier restores content you removed, it signals the content is structurally necessary. Prettier is the formatting authority — do not fight it."
---

# Prettier as Markdown Formatting Authority

## Resolving Prettier CI Failures

When `make fast-ci` fails due to prettier violations, run prettier on the specific file via devrun:

Ask devrun to run: `npx prettier --write <file-path>`

Do NOT attempt to manually fix formatting issues — prettier's output is authoritative.

## The Restoration Signal

When you remove content from a markdown file and prettier restores it during formatting, this is a signal that the content is structurally necessary for correct markdown rendering. This commonly occurs with:

- Closing backticks in multi-level code block templates
- Blank lines between structural elements
- Trailing newlines

In PR #6949, an automated reviewer flagged a "stray closing backtick" in plan-synthesizer.md. Investigation revealed prettier had restored this backtick because it was structurally necessary for the template's nested code block format. The reviewer's complaint was a false positive.

**Rule:** When prettier disagrees with a manual edit or an automated reviewer, prettier is correct.

## Related Documentation

- [Formatting Workflow](formatting-workflow.md) — General formatting patterns
- [CI Iteration](ci-iteration.md) — Running CI commands via devrun
```

---

### LOW Priority

#### 13. Frontmatter Alphabetization Convention

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to the existing conventions document, in an appropriate section:

```markdown
## Frontmatter Conventions

### Alphabetical Ordering of allowed-tools

When listing tools in agent or command frontmatter allowed-tools, maintain alphabetical order. This makes it easy to scan for a specific tool and ensures consistent formatting across files.

Example ordering: `Bash, Edit, Glob, Grep, Read, Task, Write` (not arbitrary insertion order).

This convention was established in PR #6949 when adding Write to 6 agent files — each insertion maintained alphabetical position rather than appending to end.
```

---

#### 14. Output Directory Creation Timing

**Location:** `docs/learned/planning/agent-orchestration-safety.md`
**Action:** UPDATE
**Source:** [Impl] [PR #6949]

**Draft Content:**

Add a note to the "Why File Verification Must Happen at the Orchestration Layer" section:

```markdown
**Prerequisite: Directory creation before agent launch.** When multiple agents will write to the same output directory, create the directory with `mkdir -p` before launching any agents. This prevents a race condition where the first agent to finish tries to write before the directory exists. The learn command demonstrates this pattern — it creates the `learn-agents/` subdirectory as the first step before launching parallel agents.

<!-- Source: .claude/commands/erk/learn.md, search for "mkdir -p .erk/scratch/sessions" -->
```

---

#### 15. Multi-Step File Modification Approach

**Location:** `docs/learned/conventions.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add to conventions document:

```markdown
## Multi-Step File Editing

When making multiple structural changes to a single file (e.g., updating frontmatter, adding an input parameter, and adding an output section), use separate Edit calls for each change rather than one large replacement. This approach:

1. Makes each change atomic and independently verifiable
2. Prevents conflicts from overlapping edit contexts
3. Allows partial rollback if one edit produces unexpected results

In PR #6949, each of the 6 agent files received three separate Edit calls: one for frontmatter, one for input parameters, and one for the output section.
```

---

#### 16. False Positive Automated Review Handling

**Location:** `docs/learned/pr-operations/automated-review-handling.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
title: Handling Automated Review False Positives
read_when:
  - "automated review bot flags an issue in a PR"
  - "deciding whether to fix or investigate a bot complaint"
tripwires:
  - action: "fixing code flagged by automated reviewers without investigation"
    warning: "Automated reviewers can produce false positives. Always investigate by reading the flagged code and running formatters/linters before making changes."
---

# Handling Automated Review False Positives

## Investigation Before Action

When automated review bots (tripwires review, lint bots, etc.) flag issues in a PR, always investigate before acting:

1. **Read the flagged code** — understand the context and intent
2. **Run the project's formatter** — if prettier/linter disagrees with the bot, the formatter is correct
3. **Verify the issue exists** — the complaint may be a false positive from the bot misunderstanding complex structure
4. **If false positive:** Reply to the review thread explaining why the code is correct
5. **If real issue:** Fix it

## Example: Nested Code Block False Positive

In PR #6949, the tripwires review bot flagged a "stray closing backtick" in plan-synthesizer.md. Investigation revealed the backtick was part of a multi-level code block template. Prettier confirmed this by restoring the backtick when the agent initially removed it.

## Related Documentation

- [Prettier as Markdown Formatting Authority](../ci/prettier-fixes.md) — Prettier as source of truth
```

---

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Content Relay Context Bloat

**What happened:** Parent orchestrator accumulated 60-180K tokens of relay overhead by reading all agent outputs via TaskOutput then writing them via Write, with the parent never reasoning about the content.
**Root cause:** The original pipeline design treated the parent as a message bus between agents and the filesystem, creating 2x content duplication per agent.
**Prevention:** Have agents accept output_path parameter and write their own outputs. Parent receives only short confirmations and uses ls -la to verify files exist.
**Recommendation:** TRIPWIRE — see Context Efficiency doc (item #1)

### 2. Lost Changes After Git Sync

**What happened:** After running `gt sync`, all uncommitted working tree changes were lost. The agent had to re-apply all edits from scratch.
**Root cause:** `gt sync` rebased diverged branches and created WIP commits that did not preserve the working tree state. Uncommitted changes were silently discarded.
**Prevention:** Always commit or stash changes before running `gt sync`. After sync completes, immediately check `git status` to verify working tree state.
**Recommendation:** TRIPWIRE — this is a high-severity silent failure (score 7)

### 3. Agent Reusability Issues from Hardcoded Output Behavior

**What happened:** Initial implementation modified 6 agent files to add output_path parameters and Output sections. User pointed out this reduces reusability — agents become hardcoded to always self-write even when called from contexts that want output returned.
**Root cause:** Placing orchestration logic (output routing) in agent definitions instead of in the orchestrator's Task prompts.
**Prevention:** Keep orchestration logic in orchestrator Task prompts. Agent definitions should remain context-independent. The orchestrator owns routing decisions.
**Recommendation:** ADD_TO_DOC — captured in Agent Output Routing Strategies doc (item #2)

### 4. Tool Access Violations from Missing Frontmatter

**What happened:** Six agents gained Write instructions but initially lacked Write in their allowed-tools frontmatter. This would have caused silent runtime failures.
**Root cause:** Frontmatter allowed-tools was not cross-checked against the tools referenced in agent instructions.
**Prevention:** Before launching agents, audit each agent's instructions for tool invocations and verify they appear in allowed-tools frontmatter.
**Recommendation:** TRIPWIRE — cross-cutting pattern affecting all agent development (score 6)

### 5. False Positive from Automated Reviewer

**What happened:** Automated tripwires review bot flagged a "stray closing backtick" that was actually part of an intentional template structure.
**Root cause:** Bot misunderstood the multi-layered code block structure in the output format template.
**Prevention:** Always investigate automated reviewer complaints before fixing. Run the project's formatter — if it disagrees with the bot, the formatter is correct.
**Recommendation:** ADD_TO_DOC — captured in Automated Review Handling doc (item #16)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Git Sync Losing Working Tree Changes

**Score:** 7/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2, Silent failure +1)
**Trigger:** After running `gt sync` with uncommitted working tree changes
**Warning:** "gt sync can rebase and create WIP commits that lose uncommitted working tree changes. Always commit or stash before sync, and verify git status after."
**Target doc:** `docs/learned/workflows/git-sync-state-preservation.md`

This is tripwire-worthy because the failure is completely silent — no error, no warning, just missing edits. The agent must re-discover and re-apply all changes. In the PR #6949 implementation session, the agent had to redo all 6 output routing block insertions after a sync operation discarded them. The impact compounds with the number of pending edits: a sync after 20 file edits means re-doing 20 edits. The trigger is mechanical (any gt sync with uncommitted changes) and the prevention is simple (commit first), making this an ideal tripwire.

### 2. Tool Restriction Safety: Frontmatter Must Match Tool Usage

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** Before launching agents that use Write, Bash, or other tools referenced in their instructions
**Warning:** "Verify allowed-tools frontmatter includes every tool the agent's instructions reference. Missing tools cause silent runtime failures."
**Target doc:** `docs/learned/commands/tool-restriction-safety.md`

This deserves a tripwire because the failure mode is particularly insidious: the agent launches successfully, attempts to call the restricted tool, and receives a non-obvious error that does not clearly indicate the root cause is a frontmatter configuration issue. In PR #6949, six agents were given Write instructions but initially lacked Write in frontmatter. Without the PR review catching this, all six agents would have failed at runtime when attempting to write their output files.

### 3. Missing Frontmatter Detection

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before creating new agent files in `.claude/agents/`
**Warning:** "All agent files MUST have YAML frontmatter with name, description, and allowed-tools. Missing frontmatter causes silent behavioral failures."
**Target doc:** `docs/learned/commands/tool-restriction-safety.md`

The tripwire-extractor agent in the learn pipeline was discovered to be missing its entire frontmatter block. Without frontmatter, Claude Code treats the file as a plain markdown prompt with no metadata — the agent still runs, but without tool restrictions or identity metadata. This is a setup-time error that is easy to prevent with a simple check.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Agent Reusability Consideration

**Score:** 3/10 (criteria: Cross-cutting +2, Repeated pattern +1)
**Notes:** When modifying agent definitions to control output behavior, consider whether the agent is reused across contexts. If so, embed routing instructions in orchestrator Task prompts instead. This is more of a design guideline than a tripwire — the failure mode (reduced reusability) is not destructive and is easily reversed. If future PRs show repeated instances of hardcoding behavior that should be orchestrator-controlled, this could be promoted.

### 2. Prettier CI Fix Workflow

**Score:** 3/10 (criteria: Non-obvious +1, External tool quirk +2)
**Notes:** When `make fast-ci` fails on prettier violations, the fix is to run `npx prettier --write <file>` via devrun, not to manually adjust formatting. This didn't meet the threshold because the failure mode (manual formatting fight) is annoying but not destructive, and the correct workflow is documented in CI iteration patterns. Additional evidence of agents wasting time fighting prettier would promote this.