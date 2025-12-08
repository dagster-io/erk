# Documentation Extraction Plan: Git PR Consolidation Patterns

## Objective

Document patterns and lessons learned from consolidating git-branch-submitter agent into Python-based two-phase architecture.

## Source Information

- Session ID: 4f318f69-aca2-44a3-9234-36eaab9ac203
- Related Issue: #2698 (Consolidate Git and Graphite Submission Flows)

## Documentation Items

### 1. Two-Phase Operation Pattern (Category A - Learning Gap)

**Location:** `docs/agent/architecture/two-phase-operations.md`
**Action:** Create
**Priority:** High

**Content:**

The two-phase operation pattern separates mechanical Python operations from AI-powered analysis:

```
Slash Command → Preflight (Python) → AI Analysis → Finalize (Python)
```

**Structure:**

- **Preflight**: Auth checks, staging, pushing, PR creation, diff extraction
  - Returns structured result (e.g., `GitPreflightResult`) with all data AI needs
  - Yields `ProgressEvent` for status updates, `CompletionEvent` with result
  - Handles errors with typed error classes (e.g., `GitPreflightError`)

- **AI Analysis**: Only semantic work (diff analysis, message generation)
  - Receives diff file path and metadata from preflight
  - Uses `CommitMessageGenerator` or similar for AI invocation

- **Finalize**: Apply AI-generated content
  - Updates PR metadata with AI-generated title/body
  - Handles footer generation, issue closing references
  - Cleans up temp files

**Benefits:**

- Testable: FakeGit/FakeGitHub for unit tests
- Token-efficient: Agent only loaded for semantic work
- Consistent: Same pattern for git-only and Graphite flows

**Example implementations:**

- `erk_shared/integrations/gt/operations/` (Graphite flow)
- `erk_shared/integrations/git_pr/operations/` (Git-only flow)

---

### 2. Kit CLI Push-Down Pattern (Category A - Learning Gap)

**Location:** `docs/agent/kits/kit-cli-push-down.md`
**Action:** Create
**Priority:** High

**Content:**

When agent markdown files grow large (>200 lines) with embedded bash commands, push logic down to kit CLI commands.

**Before (agent-heavy):**

```markdown
# git-branch-submitter.md (442 lines)

- Embedded bash for auth, push, PR creation
- All orchestration in markdown
- ~7,500-9,000 tokens per invocation
- Untestable
```

**After (Python-backed):**

```markdown
# pr-push.md (~60 lines)

- Delegates to `erk pr push`
- Python handles all mechanics
- ~2,000-2,500 tokens
- Fully testable with fakes
```

**Steps:**

1. Identify mechanical operations (auth, push, API calls)
2. Create kit CLI commands or main CLI commands for operations
3. Create integration package with Protocol + types
4. Add real/fake implementations
5. Update slash command to delegate to CLI
6. Remove old agent from kit.yaml

---

### 3. Protocol Satisfaction via Structural Typing (Category A - Learning Gap)

**Location:** `docs/agent/architecture/protocol-vs-abc.md` (update existing)
**Action:** Update
**Priority:** Medium

**Add section:**

## Composite Protocols for Subset Dependencies

When an operation only needs a subset of `ErkContext` dependencies, create a Protocol:

```python
class GitPrKit(Protocol):
    @property
    def git(self) -> Git: ...
    @property
    def github(self) -> GitHub: ...
```

**Key insight:** `ErkContext` already has `git` and `github` properties, so it satisfies `GitPrKit` via structural typing without any changes.

**Benefits:**

- Operations can be tested with minimal fakes (just `FakeGitPrKit`)
- Operations can be called from CLI (with `ErkContext`) or kit commands (with `RealGitPrKit`)
- Clear documentation of actual dependencies

---

### 4. Symlink Cleanup After Kit Artifact Removal (Category B - Teaching Gap)

**Location:** `docs/agent/tripwires.md` (add tripwire)
**Action:** Update
**Priority:** High

**Add tripwire:**

```markdown
**CRITICAL: Before removing agents from kit.yaml artifacts** → Read [Kit Artifact and Symlink Management](kits/dev/artifact-management.md) first. When removing an agent from kit.yaml, also remove the corresponding symlink from `.claude/agents/`. The `test_no_broken_symlinks_in_claude_directory` integration test will fail if orphaned symlinks remain.
```

**Also update index.md with routing:**

```markdown
- **Before removing agents from kit.yaml** → [Kit Artifact Management](kits/dev/artifact-management.md)
```
