---
title: Agent Orchestration Safety Patterns
read_when:
  - "passing data between agents via files or inline output"
  - "designing multi-agent workflows with parallel and sequential tiers"
  - "orchestrating subagents that produce markdown, XML, or other large outputs"
tripwires:
  - action: "capturing subagent output inline when it may exceed 1KB"
    warning: "Bash tool truncates output at ~10KB with no error. Use Write tool to save agent output to scratch storage, then pass the file path to dependent agents."
  - action: "launching a dependent agent that reads a file written by a prior agent"
    warning: "Verify the file exists (ls) before launching. Write tool silently fails if the parent directory is missing, and the dependent agent wastes its entire context discovering the file isn't there."
---

# Agent Orchestration Safety Patterns

Multi-agent workflows have two silent data-loss failure modes that don't produce errors — they just deliver truncated or missing data to downstream agents. Both stem from the same root cause: Claude Code's tool infrastructure was designed for interactive single-agent use, not for pipelines where one agent's output is another agent's input.

## Why Inline Output Breaks at Scale

Bash tool output is truncated at approximately 10KB. For interactive use this is fine — humans rarely need more than a screenful. But analysis agents routinely produce 10-30KB of structured markdown (session analyses, gap reports, synthesized plans). When this output is captured inline via TaskOutput, the truncation is silent: no error, no warning, just missing content at the end.

The symptom is subtle — a downstream synthesis agent receives partial input and produces a plausible-looking but incomplete plan. The orchestrating agent has no way to detect that data was lost.

**The fix is file-based handoff**: agents write output to scratch storage via the Write tool, the orchestrator verifies the file exists, and dependent agents receive a file path rather than inline content. This moves data transfer out of the tool output channel entirely.

## Why File Verification Must Happen at the Orchestration Layer

The Write tool can silently fail when the target directory doesn't exist. If the orchestrator skips verification and launches the dependent agent, that agent spends its full context window (setup, skill loading, tool calls) only to discover its input file is missing. By then, tokens are wasted and the error message is buried in a subagent's output.

Fail-fast at the orchestration layer — run `ls` on the expected files between the write step and the dependent agent launch. This costs one trivial Bash call and catches the failure before any downstream context is spent.

**Prerequisite: Directory creation before agent launch.** When multiple agents will write to the same output directory, create the directory with `mkdir -p` before launching any agents. This prevents a race condition where the first agent to finish tries to write before the directory exists. The learn command demonstrates this pattern — it creates the `learn-agents/` subdirectory as the first step before launching parallel agents.

<!-- Source: .claude/commands/erk/learn.md, search for "mkdir -p .erk/scratch/sessions" -->

## The Three-Step Handoff Pattern

Every agent-to-agent data transfer in erk follows this sequence:

1. **Write**: Producing agent saves output to `.erk/scratch/sessions/<session-id>/<step-name>.md` via Write tool
2. **Verify**: Orchestrator confirms the file exists via `ls`
3. **Pass path**: Orchestrator launches the consuming agent with the file path as an argument

<!-- Source: .claude/commands/erk/learn.md:401-441 -->

The learn workflow is the canonical example. See the "Write Agent Results to Scratch Storage" and "Verify Files Exist" sections in `.claude/commands/erk/learn.md` — four parallel analysis agents write results to `learn-agents/` scratch subdirectory, the orchestrator verifies all expected files, then launches the sequential DocumentationGapIdentifier agent with those file paths.

## Lightweight Verification with ls -la

The three-step handoff pattern uses `ls` to verify file existence. For self-writing agents, this can be further optimized: instead of verifying one file at a time, use a single `ls -la` on the output directory to batch-verify all expected files at once.

<!-- Source: .claude/commands/erk/learn.md, search for "ls -la .erk/scratch" -->

See the verification step in `.claude/commands/erk/learn.md` for an example where a single `ls -la` call confirms all 7 agent output files exist.

**Previous approach (content relay):** Parent reads each agent's full output via TaskOutput to verify success, then writes to file. Content appears twice in parent context.

**Current approach (self-write):** Agents write files directly, parent runs one `ls -la` to confirm. No content enters parent context during verification.

This is a refinement of the verify step in the three-step handoff pattern, not a replacement. The principle remains the same: fail fast at the orchestration layer before launching dependent agents.

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

## Parallel vs Sequential Agent Dependencies

The handoff pattern becomes critical when agents have dependency relationships. The learn workflow demonstrates both tiers:

<!-- Source: .claude/commands/erk/learn.md:552-569 -->

**Parallel tier** (no dependencies between them): SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker, PRCommentAnalyzer — all launched with `run_in_background: true`, collected via TaskOutput.

**Sequential tiers** (each depends on the prior tier's output files): DocumentationGapIdentifier reads all parallel agent outputs, PlanSynthesizer reads gap analysis, TripwireExtractor reads the synthesized plan. Each tier's input is the prior tier's verified scratch file.

The dependency graph determines where the three-step handoff pattern applies — at every tier boundary, not within a tier.

## Anti-Patterns

| Pattern                                                                                | Why It Fails                                                                     |
| -------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| Passing large agent output as a string in the `prompt` parameter of the next Task call | Bash tool truncation applies; also bloats the dependent agent's prompt           |
| Using bash heredoc (`cat <<EOF > file`) instead of Write tool                          | Special characters in markdown (backticks, dollar signs) cause silent corruption |
| Verifying files inside the dependent agent instead of at the orchestration layer       | Wastes the agent's entire context budget on discovering missing input            |
| Assuming `mkdir -p` ran successfully without checking                                  | Directory creation can fail silently in sandboxed environments                   |

## Related Documentation

- [Scratch Storage](scratch-storage.md) — canonical storage locations and session-scoped directory patterns
