# Extraction Plan: Git/Graphite Submission Architecture Documentation

## Objective

Add documentation for the two-phase submission architecture pattern and related infrastructure discovered during the git-branch-submitter consolidation planning session.

## Source Information

- Session ID: 0a136c4c-6eaa-4774-8fd5-fc96328eb846
- Context: Planning session for consolidating git and Graphite submission flows

---

## Documentation Items

### Item 1: Git vs Graphite Flow Comparison

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/architecture/submission-flows.md`
**Action:** Create new file
**Priority:** High

**Content:**

```markdown
# Submission Flow Comparison: Git vs Graphite

This document compares the two PR submission workflows available in erk.

## Overview

| Aspect | Git Flow (`/git:pr-push`) | Graphite Flow (`/gt:pr-submit`) |
|--------|---------------------------|-----------------------------------|
| Tool | git + gh CLI | Graphite (gt) |
| Stack support | None | Full stack management |
| Commit handling | Preserves history | Squashes & rebases |
| Use case | Any repo, CI automation | Graphite-enabled repos |

## Architecture Comparison

### Graphite Flow (Python-based)
\`\`\`
Slash Command → Preflight (Python) → AI Analysis → Finalize (Python)
\`\`\`

- **Preflight**: Auth checks, squash commits, gt submit, get diff
- **AI Analysis**: Diff analysis, commit message generation  
- **Finalize**: Update PR metadata, amend commit

### Git Flow (Currently Agent-based)
\`\`\`
Slash Command → Agent (all orchestration in markdown)
\`\`\`

- Single agent handles everything: auth, stage, push, PR creation, etc.
- No Python layer for testability
- Target: Align with Graphite's two-phase pattern

## Shared Infrastructure

Both flows share:
- `build_pr_body_footer()` from `erk_shared.github.pr_footer`
- Issue reference handling via `.impl/issue.json`
- `post-pr-comment` kit CLI command

## When to Use Each

- **Git flow**: CI automation, repos without Graphite, simple submissions
- **Graphite flow**: Local development with stack management, dependent PRs
```

---

### Item 2: Agent-to-Python Refactoring Pattern

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/kits/agent-to-python-refactoring.md`
**Action:** Create new file
**Priority:** High

**Content:**

```markdown
# Agent-to-Python Refactoring Pattern

When an agent grows too large (300+ lines) or contains mostly mechanical operations, consider refactoring to Python with a minimal agent.

## Signs You Need This Pattern

1. Agent has >300 lines of markdown
2. Most operations are bash commands (mechanical, not semantic)
3. Error handling is rule-based (not requiring judgment)
4. String parsing/formatting dominates the agent
5. Token cost per invocation is high (>5000 tokens)

## The Two-Phase Architecture

Refactor large agents into:

\`\`\`
Slash Command → Preflight (Python) → AI Analysis (Minimal Agent) → Finalize (Python)
\`\`\`

### Preflight Phase (Python)
- Authentication checks
- Data gathering (diffs, status)
- File operations
- Returns structured result for agent

### AI Analysis Phase (Agent)
- Only semantic operations
- Diff analysis, content generation
- Receives structured input, outputs structured result
- Target: <100 lines

### Finalize Phase (Python)
- Apply AI-generated content
- Update external systems (PRs, issues)
- Cleanup operations

## Implementation Checklist

1. Identify mechanical vs semantic operations
2. Create Python operations module in `erk_shared/integrations/<name>/`
3. Create kit CLI commands for preflight/finalize
4. Write minimal agent for semantic work only
5. Update slash command to orchestrate phases
6. Add tests with FakeGit/FakeGitHub

## Example: git-branch-submitter

**Before:** 442 lines, ~7500 tokens, untestable
**After:** ~60 lines agent + Python operations, ~2500 tokens, fully testable

See: `erk_shared/integrations/git_pr/` for implementation
```

---

### Item 3: Two-Phase Submission Architecture

**Type:** Category B (Teaching Gap)
**Location:** `docs/agent/architecture/two-phase-submission.md`
**Action:** Create new file
**Priority:** High

**Content:**

```markdown
# Two-Phase Submission Architecture

The preflight → AI → finalize pattern for PR submission workflows.

## Pattern Overview

\`\`\`
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Preflight  │ ──▶ │  AI Analysis │ ──▶ │  Finalize   │
│  (Python)   │     │   (Agent)    │     │  (Python)   │
└─────────────┘     └──────────────┘     └─────────────┘
\`\`\`

## Phase Responsibilities

### Preflight (Python)
- Verify prerequisites (auth, branch state)
- Gather data for AI analysis (diffs)
- Create draft PR if needed
- Return structured `PreflightResult`

### AI Analysis (Agent)
- Analyze diff content
- Generate commit message (title + body)
- Only semantic work - no bash, no side effects
- Return structured message

### Finalize (Python)
- Update PR with AI-generated content
- Add footer, closing references
- Post comments to issues
- Cleanup temp files

## Benefits

1. **Testability**: Python phases use FakeGit/FakeGitHub
2. **Reliability**: Auth/push errors caught before AI cost
3. **Cost**: Smaller agent = fewer tokens
4. **Speed**: Preflight can fail fast

## Implementation

Both git and Graphite flows use this pattern:
- Graphite: `erk_shared/integrations/gt/operations/`
- Git: `erk_shared/integrations/git_pr/operations/`
```

---

### Item 4: Kit CLI Push-Down Routing

**Type:** Category A (Learning Gap)
**Location:** `docs/agent/index.md` (update)
**Action:** Add routing entry
**Priority:** Medium

**Content:**

Add to index.md under Architecture section:

```markdown
- **[kit-cli-push-down.md](../developer/agentic-engineering-patterns/kit-cli-push-down.md)** — Read when refactoring large agents to Python, deciding what to push to kit CLI vs keep in agent
```