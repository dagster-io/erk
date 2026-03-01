---
name: cli-push-down
description: Moving mechanical computation from LLM prompts into tested CLI commands. Use when writing or reviewing slash commands with embedded bash, when a skill/command exceeds ~100 lines of procedural steps, when adding parsing/validation/transformation logic to markdown prompts, when debugging flaky embedded scripts, or when refactoring commands to reduce token overhead.
---

You are an expert at identifying mechanical computation embedded in agent prompts and pushing it down into tested `erk exec` CLI commands. This skill documents a proven pattern for reducing prompt complexity, improving reliability, and making agent workflows testable.

## The Pattern

**If it requires understanding meaning, keep it in the agent. If it's mechanical transformation, push it to `erk exec`.**

Like database query optimizers that "push down" predicates closer to the data layer for efficiency, this pattern moves computation from LLM prompts to Python CLI where it belongs.

| Push to `erk exec`                                  | Keep in Agent                              |
| --------------------------------------------------- | ------------------------------------------ |
| Parsing/validation (URLs, formats, paths)           | Semantic analysis (summarizing, naming)    |
| Data extraction (JSON/YAML, filtering)              | Content generation (docs, code, messages)  |
| Deterministic operations (file queries, transforms) | Complex reasoning (trade-offs, ambiguity)  |
| Token reduction (compressing, pre-filtering)        | Decision-making (planning, interpretation) |

## Why It Matters

**Token reduction.** Every line of bash, parsing logic, and error handling in a markdown prompt consumes context tokens. Pushing mechanical work to Python shrinks prompts by 50-70%, leaving the agent focused on decisions that require judgment.

**Testability.** You cannot unit test bash embedded in markdown. An `erk exec` command is a regular Python function with pytest coverage, mocked dependencies, and edge case validation. Bugs get caught in CI, not during agent runs.

**Reliability.** Embedded bash varies between shells, lacks type safety, and fails silently on typos. Python provides a real execution environment with proper error handling, structured JSON output, and deterministic behavior.

**Composability.** Once logic lives in an exec command, multiple skills and commands can invoke it. Changes to the logic propagate to all callers without updating markdown files.

## Recognizing Opportunities

A prompt is a candidate for push-down when you spot any of these smells:

- **Inline bash blocks** parsing JSON, extracting fields, or constructing commands
- **Multi-step shell pipelines** (e.g., `gh api ... | jq ... | sed ...`)
- **Conditional logic in markdown** with nested if/else decision trees
- **String manipulation** (regex matching, URL parsing, slug generation)
- **Data transformation** (YAML to JSON, filtering lists, merging objects)
- **Repeated mechanical sequences** duplicated across multiple commands/skills
- **Agent instructions for deterministic work** ("extract the plan number from the URL", "parse the YAML roadmap and find matching nodes")
- **Prompt exceeding ~100 lines** of procedural steps (not counting context/explanation)

## The Push-Down Checklist

1. **Identify the mechanical segment.** Find the block of deterministic logic in the prompt. Ask: "Does an LLM add value here, or is it just executing instructions mechanically?"

2. **Define the JSON contract.** Design the input (CLI flags/args) and output (JSON schema) before writing code. The agent will read this JSON, so make it agent-friendly:
   - Include `success: bool` at the top level
   - On failure, include `error` with human-readable `message`
   - Include all data the agent needs for subsequent steps

3. **Create the exec script.** Write it at `src/erk/cli/commands/exec/scripts/<name>.py`. Follow erk conventions: frozen dataclasses, LBYL, pathlib, no default parameters.

4. **Write tests first.** Create `tests/unit/cli/commands/exec/scripts/test_<name>.py`. Test the happy path, error cases, and edge cases. Mock external dependencies (gateways).

5. **Register the command.** Add it to `src/erk/cli/commands/exec/group.py`.

6. **Update the prompt.** Replace the mechanical block with a single `erk exec <name>` invocation. The prompt should now focus on interpreting the JSON output and making decisions.

7. **Verify token reduction.** Compare before/after line counts. A well-executed push-down reduces the prompt section by 50-70%.

## Case Studies

### Case Study 1: Plan-Implement Consolidation

**Commit:** `4bf1b6dcb` (PR #7998)

**Before:** `/erk:plan-implement` was 360 lines with a 15-step workflow. Steps 0-2d contained a complex decision tree with 4 input paths, 8 sub-steps, and inline bash for branch detection, impl-context cleanup, and session upload.

**After:** A single `erk exec setup-impl` command replaced the entire decision tree. Three additional exec commands (`detect-plan-from-branch`, `cleanup-impl-context`, `upload-impl-session`) replaced inline bash blocks. The prompt shrank from 360 to ~180 lines.

**Impact:**

- 50% prompt reduction (360 -> 180 lines)
- 4 new exec commands with full unit test coverage
- Eliminated 18 lines of inline bash with idempotent, tested Python
- Fixed a bug (`--issue-number` vs `--plan-id`) that was invisible in untested bash

### Case Study 2: Objective Update Workflow

**Commit:** `28cb8cc2f` (PR #8069)

**Before:** `/erk:objective-update-with-landed-pr` required 7 steps across 173 lines. The agent had to execute 5+ sequential commands, parse JSON at each step, extract plan references from YAML, and construct complex command-line flags. Most of this was deterministic.

**After:** A single `erk exec objective-apply-landed-update` combined fetch-context, update-roadmap-nodes, and post-action-comment into one atomic call. The agent now only does prose reconciliation (the part requiring judgment). Instructions shrank from 173 to ~70 lines.

**Impact:**

- ~60% prompt reduction (173 -> 70 lines)
- Agent burden reduced from YAML parsing + 5 sequential commands to 1 command + prose review
- Eliminated race conditions between intermediate steps
- 400-line test suite covering happy path, errors, and edge cases

### Case Study 3: Push-and-Create-PR

**Commit:** `4c5e7ef92` (PR #7955)

**Before:** `/erk:pr-submit` Step 1 used the monolithic `erk pr submit --skip-description` command. The flag approach mixed semantic concerns (generating PR description) with mechanical concerns (pushing branch, creating PR).

**After:** `erk exec push-and-create-pr` runs only the first three pipeline steps (prepare, commit-wip, push-and-create) with suppressed progress output, returning structured JSON. The semantic work (generating description) remains with the agent.

**Impact:**

- Clean separation of mechanical (push/create) from semantic (describe) concerns
- Reusable exec command for any workflow needing PR creation
- Added quiet mode to pipeline for JSON-clean output
- Simplified error messages across sibling exec scripts

### Case Study 4: Learn Trigger Simplification

**Commit:** `b94b466e9` (PR #8323)

**Before:** The async learn pipeline triggered by `erk land` spanned ~363 lines across 7 helper functions: session discovery, preprocessing, gist upload, CI workflow dispatch, multi-agent analysis, plan-save, and metadata tracking. It included an interactive 4-option menu.

**After:** Replaced with two lightweight helpers (`_should_create_learn_issue` and `_create_learn_issue_with_sessions`) that create a GitHub issue directly. Fire-and-forget instead of interactive menu and CI workflow dispatch.

**Impact:**

- 363 lines of complex async code removed
- 1,021 lines of associated tests deleted (testing removed complexity)
- Interactive menu eliminated in favor of fire-and-forget issue creation
- TUI learn trigger removed (execution pipeline handles it)

## Anti-Patterns

### Over-pushing into scattered exec scripts

Push-down can go too far. When each small task becomes its own exec script, you get a proliferation of tiny commands that are hard to discover and maintain.

**Example:** Commit `e2bd53d05` (PR #7987) had to reconsolidate 4 scattered exec scripts (`setup-impl`, `cleanup-impl-context`, `detect-plan-from-branch`, `upload-impl-session`) back into the workflow documentation and an integrated `--stage=impl` flag on `erk pr check`. The scripts were too granular to justify their overhead.

**Rule of thumb:** If the exec script is under ~30 lines of logic and only called from one place, consider whether it belongs as part of a larger command instead.

### Under-composing outputs

A push-down exec command that returns minimal JSON forces the agent to make additional calls for related data. Design the output to include everything the agent needs for the next decision.

**Bad:** `{"plan_number": 2521}` — agent must now fetch plan details separately.
**Good:** `{"plan_number": 2521, "title": "...", "phases": [...], "related_docs": {...}}` — agent can proceed immediately.

### Pushing semantic work

Not everything belongs in Python. If the agent needs to understand meaning, summarize, name things, or make judgment calls, that work should stay in the prompt. Push-down is for mechanical transformation, not reasoning.

### Ignoring the JSON contract

Exec commands must return structured JSON with `success: bool`. Without a consistent contract, agents resort to text parsing, which defeats the purpose of push-down.

## Related Resources

- **Exec command reference:** Load the `erk-exec` skill for command listings and conventions
- **Exec script directory:** `src/erk/cli/commands/exec/scripts/`
