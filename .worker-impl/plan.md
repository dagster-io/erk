# Omnibus Documentation Plan

This plan consolidates 15 open documentation extraction issues into a single implementation effort.

## Consolidated From

| Issue | Title | Status |
|-------|-------|--------|
| #2725 | Extraction Plan: PR Discussion Comments | Superseded |
| #2717 | Enhance GitHub API Field Mapping Documentation | Superseded |
| #2705 | Documentation Extraction: Git PR Consolidation Patterns | Superseded |
| #2700 | Extraction Plan: Git/Graphite Submission Architecture | Superseded |
| #2664 | Documentation Extraction: Kit CLI Scratch Patterns | Superseded |
| #2651 | Extraction Plan: Session Store Testing Patterns | Superseded |
| #2648 | Extraction Plan: Hook Output Conventions | Superseded |
| #2642 | Extraction Plan: Conflict Resolution Style | Superseded |
| #2630 | Add Kit CLI Command Testing Documentation | Superseded |
| #2475 | Documentation Extraction: Schema v2 Consolidation | Superseded |
| #2245 | Extraction Plan: gh issue develop Removal | Superseded |
| #2004 | Kit Shared Includes Documentation | Superseded |
| #2002 | Document CLI-to-Slash-Command Delegation | Superseded |
| #1974 | Add Kit Artifact Dev Mode Documentation | Superseded |
| #1902 | Markdown Documentation Discoverability Analysis | Deferred (feature) |

**Note:** #2656 (Add Plan Support to ClaudeCodeSessionStore) was excluded - it's a feature, not documentation.

---

## Phase 1: Architecture Documentation

### 1.1 GitHub Interface Implementation Guides

**New Files:**
- `docs/agent/architecture/github-issues-abc.md` - Implementation checklist for GitHubIssues ABC
- Update `docs/agent/architecture/github-interface-patterns.md` - Add branch refs and merge state mapping

**Content from:** #2725, #2717

**Deliverables:**
1. Tripwire for GitHubIssues ABC method additions
2. Implementation checklist (4 files: abc.py, real.py, fake.py, dry_run.py)
3. Fake mutation tracking pattern
4. Branch reference field mapping table
5. Merge state status mapping table
6. Code examples for normalization

### 1.2 Two-Phase Operation Architecture

**New Files:**
- `docs/agent/architecture/two-phase-operations.md` - Preflight → AI → Finalize pattern
- `docs/agent/architecture/submission-flows.md` - Git vs Graphite comparison

**Content from:** #2700, #2705

**Deliverables:**
1. Two-phase architecture diagram and explanation
2. Preflight/AI/Finalize phase responsibilities
3. Git vs Graphite flow comparison table
4. Agent-to-Python refactoring guide
5. Benefits (testability, token efficiency, reliability)

### 1.3 Result Pattern Documentation

**New Files:**
- `docs/agent/architecture/result-pattern.md` - Frozen dataclass result pattern

**Content from:** #2475

**Deliverables:**
1. When to use Result pattern vs exceptions
2. Structure (success, error, partial success fields)
3. Caller pattern examples
4. Anti-patterns

---

## Phase 2: Testing Documentation

### 2.1 Session Store Testing Patterns

**New Files:**
- `docs/agent/testing/session-store-testing.md` - FakeClaudeCodeSessionStore usage

**Content from:** #2651

**Deliverables:**
1. Basic setup patterns
2. Injecting via DotAgentContext
3. Key methods reference
4. Mock elimination workflow

### 2.2 Kit CLI Command Testing

**Update Files:**
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/fake-driven-testing/skills/fake-driven-testing/references/patterns.md`

**Content from:** #2630

**Deliverables:**
1. Kit CLI command testing section
2. CliRunner + DotAgentContext.for_test() pattern
3. JSON output testing
4. FakeGitHubIssues helper examples

---

## Phase 3: Kit Development Documentation

### 3.1 Kit CLI Scratch Patterns

**Update Files:**
- `docs/agent/kits/dependency-injection.md` - Add scratch storage section

**Content from:** #2664

**Deliverables:**
1. Scratch storage access in kit CLI commands
2. Correct import path (erk_shared.scratch.scratch)
3. Repo root resolution pattern
4. Common mistakes section

### 3.2 Kit Shared Includes

**New Files:**
- `docs/agent/kits/kit-shared-includes.md` - Sharing content between kit commands

**Content from:** #2004

**Deliverables:**
1. File location guidance (docs/erk/includes/)
2. Reference syntax from command files
3. Naming conventions (no underscore prefix)
4. Symlink requirements

### 3.3 Kit Artifact Dev Mode

**New Files:**
- `docs/agent/kits/dev/artifact-dev-mode.md` - Adding artifacts in dev mode

**Content from:** #1974

**Deliverables:**
1. Dev mode detection
2. 5-step process (create, register, symlink, toml, fixtures)
3. Verification steps
4. Common pitfalls

### 3.4 Kit Artifact Symlink Cleanup

**Update Files:**
- `docs/agent/tripwires.md` (via frontmatter)

**Content from:** #2705

**Deliverables:**
1. Tripwire for removing agents from kit.yaml

---

## Phase 4: CLI & Hook Documentation

### 4.1 CLI-to-Slash-Command Delegation

**New Files:**
- `docs/agent/cli/cli-slash-command-delegation.md`

**Content from:** #2002

**Deliverables:**
1. ClaudeExecutor abstraction overview
2. StreamEvent types
3. Argument passing pattern
4. Existing commands using pattern
5. FakeClaudeExecutor testing

### 4.2 Hook Output Conventions

**Update Files:**
- `docs/agent/hooks/` (TBD which file)

**Content from:** #2648

**Deliverables:**
1. Skill reminder format
2. Routing reminder format
3. Context injection format
4. Context minimization principles

---

## Phase 5: Workflow & Glossary Updates

### 5.1 Conflict Resolution Style

**Update Files:**
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/docs/erk/includes/conflict-resolution.md`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/erk/merge-conflicts-fix.md`

**Content from:** #2642

**Deliverables:**
1. Style/readability conflict guidance
2. Cherry-pick vs rebase detection

### 5.2 Glossary Updates

**Update Files:**
- `docs/agent/glossary.md`

**Content from:** #2725, #2245

**Deliverables:**
1. PR Discussion Comments vs Review Threads entry
2. gh issue develop (removed) historical entry

### 5.3 Integration Layer Removal Checklist

**Update Files:**
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/fake-driven-testing/skills/fake-driven-testing/references/workflows.md`

**Content from:** #2245

**Deliverables:**
1. "Removing an Integration Layer" section

---

## Phase 6: Index Updates

**Update Files:**
- `docs/agent/index.md`
- `AGENTS.md` routing table

**Add entries for:**
- All new architecture docs
- All new kit docs
- CLI delegation doc

---

## Deferred Items

### #1902 - Markdown Documentation Discoverability Analysis

This issue describes creating new CLI commands (`dot-agent md orphans`, `dot-agent md tree`) rather than documentation. It should remain open as a separate feature request.

---

## Implementation Order

1. **Phase 1** - Architecture docs (foundational patterns)
2. **Phase 2** - Testing docs (enables better testing)
3. **Phase 3** - Kit docs (development workflow)
4. **Phase 4** - CLI/Hook docs (operational)
5. **Phase 5** - Workflow/Glossary (polish)
6. **Phase 6** - Index updates (discoverability)

---

## Success Criteria

- [ ] All new documentation files created
- [ ] All update targets modified
- [ ] All tripwires added via frontmatter + sync
- [ ] Index files updated with routing
- [ ] CI passes (no broken links)
