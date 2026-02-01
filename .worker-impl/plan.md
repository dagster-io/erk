# Documentation Plan: Optimize objective-update-with-landed-pr: 4 turns to 2 turns (with Haiku delegation)

## Context

This implementation optimized the `objective-update-with-landed-pr` command by delegating mechanical, template-driven work to a Haiku subagent instead of executing multiple sequential LLM turns in the parent session. The original command required 4 turns: (1) load skill, (2) analyze and compose action comment, (3) update roadmap body, (4) validate via GitHub re-fetch. The optimized version reduces this to 2 turns: (1) fetch context JSON, (2) delegate composition, writing, and validation to a single Haiku subagent.

The key insight is that **turn count is the dominant factor in wall-clock latency**, not token count. Each LLM turn adds approximately 10-15 seconds of latency. By fusing multiple mechanical steps into a single Haiku subagent turn, we achieved 46-62% wall-clock time savings while also reducing model costs (Haiku is significantly cheaper than Sonnet/Opus). The Haiku subagent can self-validate by counting steps in the objective body it just composed, eliminating the need for a separate GitHub API call to re-fetch and verify.

Future agents optimizing commands or workflows should consider this delegation pattern. When work is deterministic and template-driven (composition from structured input, validation against known rules), it is an excellent candidate for Haiku delegation. The parent model orchestrates and the smaller model executes the mechanical work with full context embedded directly in the prompt.

## Raw Materials

https://gist.github.com/schrockn/036f94c2678c47db11acab06005bfb20

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 4     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Haiku Subagent Delegation for Optimization [NEW_DOC]

**Location:** `docs/learned/architecture/subagent-delegation-for-optimization.md`
**Source:** [Impl]

**Key Content:**
- Pattern for delegating mechanical work to Haiku subagents
- Performance impact: 46-62% wall-clock time savings via turn reduction
- Implementation pattern showing parent context fetch → Haiku subagent execution
- When to use: deterministic, template-driven work, multi-step mechanical processes
- Cost reduction: Haiku is ~10x cheaper than Sonnet, 30x cheaper than Opus

**Deliverable:** Comprehensive guide with implementation pattern, rationale, and examples from objective-update-with-landed-pr optimization.

#### 2. Turn Count as Performance Metric [NEW_DOC]

**Location:** `docs/learned/optimization/turn-count-profiling.md`
**Source:** [Impl]

**Key Content:**
- Core insight: Each LLM turn adds 10-15 seconds latency regardless of token count
- Profiling methodology: Count turns, identify fusible steps, measure after optimization
- Anti-pattern: Token optimization without turn awareness provides marginal benefit
- Example: 4-turn 40-60s workflow → 2-turn 15-23s workflow = 46-62% savings

**Deliverable:** Methodology for profiling workflow latency and optimization strategy focused on turn reduction.

### MEDIUM Priority

#### 3. Subagent Self-Validation Pattern [NEW_DOC]

**Location:** `docs/learned/architecture/subagent-self-validation.md`
**Source:** [Impl]

**Key Content:**
- Pattern: Validate by analyzing composed content rather than re-fetching
- Why: Eliminates API latency, reduces rate limit pressure, subagent already has context
- When it works: Deterministic validation, rules-based checking, pattern matching
- When it doesn't: External transformation needed, race conditions possible
- Tripwire: If subagent is re-fetching available context, context embedding is incomplete

**Deliverable:** Pattern documentation with implementation examples and failure mode guidance.

#### 4. Prompt Context Embedding for Subagents [NEW_DOC]

**Location:** `docs/learned/architecture/subagent-prompt-structure.md`
**Source:** [Impl]

**Key Content:**
- Principle: Subagent prompts must be completely self-contained
- Structure: Context blob + templates + rules + instructions + success criteria
- Common mistake: Referencing external skills instead of embedding templates
- Tripwire: Incomplete context causes silent subagent failures

**Deliverable:** Prompt structure guide with template, checklist, and anti-patterns.

#### 5. Subagent Model Selection Heuristic [NEW_DOC]

**Location:** `docs/learned/reference/subagent-model-selection.md`
**Source:** [Impl]

**Key Content:**
- Decision matrix: Template composition → Haiku, reasoning → Sonnet, creative → Opus
- Cost/speed tradeoffs: Haiku 1x cost/fast, Sonnet 10x cost/medium, Opus 30x cost
- Default to Haiku for mechanical work
- Escalate only for quality-critical or reasoning-heavy tasks

**Deliverable:** Decision matrix and heuristic for model selection in subagent delegation.

#### 6. Command Documentation as Executable Spec [UPDATE_EXISTING]

**Location:** `docs/learned/cli/command-specification.md`
**Source:** [Impl]

**Key Content:**
- Principle: `.claude/commands/` files are executable specs, not just documentation
- Implications: Changes take effect immediately, formatting matters, content is code
- Tripwire: Run `make prettier` immediately after editing command files
- CI validation: Prettier is enforced in CI

**Deliverable:** Brief guide clarifying command file role and Prettier requirement.

#### 7. CI Environment Detection [UPDATE_EXISTING]

**Location:** `docs/learned/planning/agent-delegation.md`
**Source:** [Impl]

**Content Update:**
- Add reference to batch vs interactive session detection pattern
- Pattern: Check CI environment variables early, adjust behavior (auto-submit vs confirm)
- Used in learn workflow for CI-aware execution

#### 8. Branch Naming Conventions [UPDATE_EXISTING]

**Location:** `docs/learned/erk/branch-naming-conventions.md`
**Source:** [Impl]

**Content Update:**
- Graphite-style branch naming: `P{issue}-{description}-{date}-{time}`
- Example: `P6540-erk-plan-optimize-objecti-02-01-0830`
- Used in plan workflows for automated integration

#### 9. Task Output Error Handling [UPDATE_EXISTING]

**Location:** `docs/learned/architecture/task-tool-patterns.md`
**Source:** [Impl]

**Content Update:**
- Pattern: Always parse JSON and check for errors before accessing payload
- Common mistake: Direct payload access without error check
- Tripwire: Use structured error checking for TaskOutput results

## Prevention Insights

### Errors and Resolutions

1. **Prettier Formatting on Command Files** - Edited `.claude/commands/` files without running Prettier. Resolution: Run `make prettier` immediately after edits.

2. **Session ID Unavailable** - `impl-signal started` failed in remote context. Resolution: Non-blocking failure; session still logged.

## Tripwire Candidates

Four HIGH-priority tripwires to prevent recurrence of non-obvious patterns:

### 1. Subagent Self-Validation [Score: 6/10]

**Trigger:** Before reviewing subagent code for GitHub API calls
**Warning:** If subagent is re-fetching context already available/passed in the prompt, context embedding is incomplete. Add missing data to prompt instead.
**Type:** Silent performance regression (no error message, just wasted API calls)

### 2. Prettier Formatting on Command Files [Score: 5/10]

**Trigger:** After editing `.claude/commands/` files
**Warning:** Run `make prettier` immediately; formatting affects CI validation.
**Type:** CI blocker (non-obvious requirement)

### 3. Task vs Direct Execution Decision [Score: 5/10]

**Trigger:** When implementing deterministic command logic
**Warning:** Consider Task delegation with Haiku for mechanical, template-driven work. Turn count dominates wall-clock latency.
**Type:** Performance optimization pattern (missed optimization opportunity)

### 4. Prompt Completeness for Delegation [Score: 4/10]

**Trigger:** When delegating to subagents via Task tool
**Warning:** Verify prompt includes: (1) full context blob, (2) all templates, (3) "DO NOT re-fetch" instructions, (4) clear success criteria.
**Type:** Silent failure (subagent makes wrong decisions without exceptions)

## No Contradictions

Existing delegation documentation in `docs/learned/planning/agent-delegation.md` aligns with patterns discovered. No updates needed for safety/consistency.

## Recommendations for Implementation

1. **Start with HIGH priority:** Haiku delegation pattern and turn count profiling will immediately benefit ongoing optimization work
2. **Add tripwires:** All 4 candidates are worth protecting against future regression
3. **Update existing docs:** Minor updates to 5 existing docs will keep knowledge current
4. **Create new category:** `docs/learned/optimization/` is needed for turn-count profiling doc