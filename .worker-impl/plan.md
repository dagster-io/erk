# Documentation Plan: Generalize PlanRowData.issue_number to plan_id

## Context

This PR implemented a pure mechanical rename across the TUI layer to generalize GitHub-specific terminology (`issue_number`, `issue_url`, `issue_body`) to backend-agnostic plan terminology (`plan_id`, `plan_url`, `plan_body`). This is a prerequisite for enabling the TUI to work with multiple plan backends (GitHub issues, draft PRs, or future providers). The implementation touched 32 files across the TUI layer, gateway ABCs, implementations, tests, and documentation.

The implementation demonstrated exemplary patterns for large-scale refactoring: systematic scope discovery using subagents (176 occurrences across 19 files), clear semantic boundaries (TUI-layer renames vs. API-layer preservation), dependency-ordered execution (types -> ABCs -> implementations -> consumers -> tests), and comprehensive multi-pass verification. The session also surfaced important lessons about bulk rename tools operating syntactically rather than semantically, which caused some out-of-scope changes that had to be reverted.

Documentation from this session matters because future agents will face similar bulk refactoring tasks. The patterns for: (1) pre-rename reconnaissance, (2) scope boundary management, (3) multi-pass verification, and (4) frozen dataclass type-safe refactoring are all valuable for preventing errors in future sessions. Additionally, the PR review surfaced 9 documentation drift instances (8 pre-existing), revealing systematic patterns about maintaining command availability tables and ABC interface documentation.

## Raw Materials

https://gist.github.com/schrockn/ab3465ae470a279939753ea489604fff

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 27    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 6     |
| Potential tripwires (score 2-3)| 8     |

## Documentation Items

### HIGH Priority

#### 1. CommandExecutor Gateway Method Parameter Renames

**Location:** `docs/learned/architecture/command-executor-gateway.md`
**Action:** CREATE
**Source:** [Impl], [PR #7473]

**Draft Content:**

```markdown
---
read-when:
  - Working with CommandExecutor gateway
  - Implementing command execution in TUI
  - Adding plan-related commands
---

# CommandExecutor Gateway

The `CommandExecutor` gateway provides methods for executing plan-related operations from the TUI.

## Method Signatures

The following methods use backend-agnostic plan terminology:

- `close_plan(*, plan_id: int, plan_url: str) -> CloseResult`
- `submit_to_queue(*, plan_id: int, plan_url: str) -> SubmitResult`

See `CommandExecutor` ABC in `packages/erk-shared/src/erk_shared/gateway/command_executor/abc.py` for full interface.

## Implementation Pattern

When implementing CommandExecutor methods:

1. Accept `plan_id` and `plan_url` parameters (not `issue_number`/`issue_url`)
2. The underlying implementation may translate to GitHub API calls using issue numbers, but the interface remains backend-agnostic
3. Update all 3 places for each gateway: ABC, fake, real

See `docs/learned/architecture/gateway-abc-implementation.md` for the 5-place update pattern.
```

---

#### 2. Gateway Type Change Propagation Pattern (TRIPWIRE)

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Gateway Type Change Propagation

**Trigger:** When changing a field type in a dataclass used by gateways

**Warning:** Must update all 5 places: ABC + fake + real for EACH affected gateway (not just one). When `PlanRowData` fields change, both `PlanDataProvider` AND `CommandExecutor` gateways need updates.

**Checklist:**
1. Dataclass definition (e.g., `PlanRowData` in `types.py`)
2. ABC method signatures for gateway 1 (e.g., `PlanDataProvider`)
3. Fake implementation for gateway 1
4. Real implementation for gateway 1
5. Repeat steps 2-4 for each additional gateway using the dataclass

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
```

---

#### 3. Bulk Rename Scope Verification (TRIPWIRE)

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Bulk Rename Scope Verification

**Trigger:** After running bulk rename tools (sed, libcst, ast-grep)

**Warning:** Use `git diff --stat` to verify only expected files changed. Spot-check for semantic boundary violations (e.g., TUI data types vs GitHub API types sharing the same field name).

**Context:** Bulk rename tools operate syntactically, not semantically. A term like `issue_number` may appear in both TUI data structures (PlanRowData) and GitHub API structures (Issue.json) - these are different semantic domains that should not be renamed together.

**Verification steps:**
1. Run `git diff --stat` after bulk rename
2. Check if unexpected files appear in the list
3. For files outside intended scope, revert with `git checkout HEAD -- <path>`
4. Spot-check 2-3 modified files to verify semantic correctness

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
```

---

#### 4. Multi-Pass Rename Verification After Bulk Refactors (TRIPWIRE)

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Multi-Pass Rename Verification

**Trigger:** After libcst-refactor completes bulk renames

**Warning:** Grep for old patterns in BOTH `src/` AND `tests/`. Check: constructor params, method params, display strings, test assertions, JSON keys.

**Verification checklist:**
- [ ] Grep `src/` for old field/class names
- [ ] Grep `tests/` for old field/class names
- [ ] Check constructor parameter names in `__init__` methods
- [ ] Check method parameter names in definitions
- [ ] Check display strings and user-facing messages
- [ ] Check JSON serialization key names
- [ ] Check test assertion expected values

**Example commands:**
```bash
# After renaming issue_number -> plan_id
rg "\.issue_number" src/
rg "issue_number" tests/
rg "\"issue_number\"" tests/  # JSON keys in test assertions
```

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
```

---

#### 5. Frozen Dataclass Field Rename Propagation (TRIPWIRE)

**Location:** `docs/learned/refactoring/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Frozen Dataclass Field Renames

**Trigger:** When renaming fields on frozen dataclasses

**Warning:** Update: field declarations, constructor kwargs at ALL call sites, internal assignments, docstrings, JSON serialization tests.

**Why frozen dataclasses help:** Every missed field access causes a type error. The type checker catches most issues, but be aware of:
- Test code using `**kwargs` patterns
- JSON serialization tests with string key assertions
- Docstrings mentioning field names
- Display strings interpolating field values

**Update locations:**
1. Field declaration in dataclass
2. All `ClassName(field_name=value)` constructor calls
3. Internal `self._field_name = field_name` assignments
4. Docstrings and comments referencing the field
5. Test assertions checking JSON output keys

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
```

---

#### 6. Documentation Drift Detection - Command Availability Tables

**Location:** `docs/learned/tui/command-availability-documentation.md`
**Action:** CREATE
**Source:** [PR #7473]

**Draft Content:**

```markdown
---
read-when:
  - Documenting TUI command availability
  - Updating action-inventory.md
  - Adding new commands to command registry
tripwires: 3
---

# Command Availability Documentation Patterns

## Problem

PR #7473 review revealed 5 documentation drift instances related to command availability tables. Common issues:
- Commands missing from predicate-based tiers
- Commands grouped under wrong predicates
- Command counts that don't match implementation

## Audit Procedure

When updating command availability documentation:

1. **Extract from source:** Grep registry.py for all command registrations
   See `CommandDef` class in `src/erk/tui/commands/registry.py`
2. **Group by predicate type:** Commands with same availability predicate go together
3. **Verify counts:** Don't write "Six commands" - list them and let the count speak for itself
4. **Use source pointers:** For complex predicates, point to `registry.py` instead of copying code

## Predicate-Based Grouping Rules

Group commands by their `is_available` predicate, not by conceptual similarity:
- "Needs PR" tier: commands with `pr_url is not None` predicate
- "Needs worktree" tier: commands with `worktree_branch is not None` predicate
- Do NOT mix predicates even if commands seem related

## Anti-Patterns

- Listing command counts in prose ("Six commands require...")
- Copying verbatim predicate code into docs (it drifts)
- Grouping by human intuition rather than actual predicate
```

---

### MEDIUM Priority

#### 7. make_plan_row() Test Helper Parameter Changes

**Location:** `docs/learned/testing/tui-testing-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Writing TUI tests
  - Creating test plan data
  - Using make_plan_row() factory
---

# TUI Testing Patterns

## make_plan_row() Factory

The `make_plan_row()` factory function creates `PlanRowData` instances for testing.

**Current parameter names:**
- `plan_id: int` (not `issue_number`)
- `plan_url: str | None` (not `issue_url`)
- `plan_body: str` (not `issue_body`)

See `make_plan_row()` in `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/fake.py`.

## Usage Pattern

```python
from erk_shared.gateway.plan_data_provider.fake import make_plan_row

row = make_plan_row(
    plan_id=123,
    plan_url="https://github.com/owner/repo/issues/123",
    plan_body="# Implementation Plan\n...",
)
```

## When Updating Test Infrastructure

If `PlanRowData` fields change, update:
1. The dataclass definition in `types.py`
2. The `make_plan_row()` defaults in `fake.py`
3. All test files calling `make_plan_row()` with explicit kwargs
```

---

#### 8. dash_data.py JSON Schema Breaking Change

**Location:** `docs/learned/cli/dash-data-json-schema.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Consuming dash_data.py JSON output
  - Building external tools that read plan data
  - Debugging JSON serialization issues
---

# dash_data.py JSON Schema

The `dash_data.py` exec script emits plan data as JSON via `dataclasses.asdict(PlanRowData)`.

## Current Field Names

- `plan_id` (formerly `issue_number`)
- `plan_url` (formerly `issue_url`)
- `plan_body` (formerly `issue_body`)

See `_serialize_plan_row()` in `src/erk/cli/commands/exec/scripts/dash_data.py`.

## Breaking Changes Policy

Per project policy (see `docs/learned/conventions.md`), erk does not maintain backwards compatibility. External consumers must update when field names change.

## External Consumer Checklist

If consuming dash_data JSON output, check for:
- Field name references in parsing code
- JSON key expectations in tests
- Any caching or persistence that stores field names
```

---

#### 9. TUI Display String Terminology Consistency (TRIPWIRE)

**Location:** `docs/learned/tui/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Display String Terminology

**Trigger:** When adding new TUI status messages or display strings

**Warning:** Use 'plan' terminology (not 'issue') to maintain consistency with backend-agnostic naming.

**Examples:**
- "Opened plan #123" (not "Opened issue #123")
- "by plan#" sort label (not "by issue#")
- Info row label "Plan" (not "Issue")

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
```

---

#### 10. Command Registry Display Name Generators

**Location:** `docs/learned/tui/command-display-generators.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Adding new TUI commands
  - Creating display name generators
  - Working with command registry
---

# Command Display Name Generators

Display name generators in the command registry reference plan data using backend-agnostic field names.

## Pattern

```python
def _display_name_generator(ctx: CommandContext) -> str:
    return f"Open plan #{ctx.row.plan_id}"  # Not issue_number
```

## Field References

Use these field names in display generators:
- `ctx.row.plan_id` (not `ctx.row.issue_number`)
- `ctx.row.plan_url` (not `ctx.row.issue_url`)

See display name generators in `src/erk/tui/commands/registry.py` - grep for `ctx.row.plan_id`.
```

---

#### 11. Context-Preserved Naming in Plan Formats (TRIPWIRE)

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Context-Preserved Naming

**Trigger:** When renaming `issue_*` -> `plan_*` in TUI layer

**Warning:** Preserve `issue_*` in: `.impl/issue.json` format, plan header YAML `issue_number`, learn fields (`learn_plan_issue`, `objective_issue`).

**Context:** These formats represent the underlying GitHub data model, not the TUI's plan abstraction. The TUI uses `plan_id` but the persisted data still refers to GitHub issues.

**What to rename (TUI layer):**
- `PlanRowData.issue_number` -> `plan_id`
- Display strings ("Opened issue #" -> "Opened plan #")
- Method parameters in data providers

**What to preserve (file formats):**
- `.impl/issue.json` field names
- Plan header YAML fields (`issue_number:`)
- Learn issue metadata fields

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
```

---

#### 12. Pre-Existing Test Failures Isolation Pattern

**Location:** `docs/learned/testing/pre-existing-failures.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Debugging test failures during refactoring
  - Working in a codebase with known test failures
  - Distinguishing new failures from old ones
---

# Pre-Existing Test Failures Pattern

When working in a codebase with known test failures, use this pattern to distinguish pre-existing failures from new ones:

## The git stash Pattern

```bash
# Establish baseline (what fails without your changes)
git stash
pytest path/to/tests
# Note the failures

# Test your changes
git stash pop
pytest path/to/tests
# Compare failures - any new ones are yours to fix
```

## Why This Matters

During refactoring, seeing test failures can be confusing:
- Are these caused by my changes?
- Were they already broken?
- Am I wasting time debugging unrelated issues?

The stash pattern gives you clarity: if a test fails both before and after your changes, it's pre-existing.

## When to Use

- During large refactors that touch many files
- When entering an unfamiliar area of the codebase
- When test failures seem unrelated to your changes
```

---

#### 13. Subagent Reconnaissance Before Bulk Refactors (Potential Tripwire)

**Location:** `docs/learned/planning/subagent-reconnaissance.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Planning bulk rename operations
  - Launching libcst-refactor for large changes
  - Scoping refactoring tasks
tripwires: 1
---

# Subagent Reconnaissance Pattern

Before executing bulk renames, launch Explore subagents to understand scope.

## Why This Matters

The PR #7473 implementation discovered 176 occurrences across 19 files. This upfront reconnaissance:
- Prevents under-renaming (missing files)
- Prevents over-renaming (changing wrong semantic domains)
- Enables accurate effort estimation

## Reconnaissance Queries

Launch Explore subagents to:

1. **Find method signatures:** "Find all method signatures with parameter named `issue_number`"
2. **Count field access:** "Count occurrences of `.issue_number` field access across packages"
3. **Identify semantic boundaries:** "Which files use `issue_number` to refer to GitHub issues vs. plan identifiers?"

## Pattern

```
1. Launch Explore subagent for scope discovery
2. Wait for results before committing to strategy
3. Use findings to inform libcst-refactor instructions
4. After bulk rename, verify against original count
```

**Potential tripwire score:** 3/10 (Non-obvious +2, Repeated pattern +1)
```

---

#### 14. Scope Discipline in TUI vs API Layer Renames

**Location:** `docs/learned/refactoring/scope-discipline.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Renaming fields that appear in multiple layers
  - Distinguishing TUI changes from API changes
  - Avoiding over-renaming during bulk refactors
---

# Scope Discipline in Renames

When renaming domain terms (like `issue_number`), distinguish semantic domains:

## TUI Layer (Should Rename)

- `PlanRowData` fields - these are TUI abstractions
- Display strings and user-facing messages
- TUI widget field references
- Data provider method parameters (ABC interface)

## API Layer (Should NOT Rename)

- GitHub API response parsing
- `.impl/issue.json` file format
- Plan header YAML fields
- Anything that maps directly to external API field names

## How to Identify

Use grep to distinguish consumers from producers:

```bash
# TUI layer files (should rename)
rg "issue_number" src/erk/tui/

# API layer files (should NOT rename)
rg "issue_number" src/erk/gateway/github/  # GitHub API mapping
```

## The PR #7473 Example

Renamed in TUI layer:
- `PlanRowData.issue_number` -> `plan_id`
- `SortKey.ISSUE_NUMBER` -> `PLAN_ID`
- Display strings "Opened issue #" -> "Opened plan #"

Preserved in API layer:
- `.impl/issue.json` field names
- Plan header YAML `issue_number:` field
```

---

#### 15. libcst-refactor Dependency Ordering

**Location:** `docs/learned/refactoring/libcst-dependency-ordering.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Planning large-scale refactors
  - Using libcst-refactor for bulk renames
  - Avoiding intermediate broken states
---

# libcst-refactor Dependency Ordering

When executing large refactors, order changes by dependency:

## Correct Ordering

1. **Types first:** Dataclass definitions, type aliases, enums
2. **ABCs second:** Abstract base class method signatures
3. **Implementations third:** Fake and real implementations
4. **Consumers fourth:** Code that uses the types/ABCs
5. **Tests last:** Test files that exercise consumers

## Why This Order Matters

- Types must exist before ABCs can reference them
- ABCs must be updated before implementations
- Consumers depend on stable ABC interfaces
- Tests verify final behavior after all changes

## Example Instruction for libcst-refactor

```
Rename in this order:
1. PlanRowData fields in types.py
2. PlanDataProvider ABC method parameters
3. FakePlanDataProvider method parameters
4. RealPlanDataProvider method parameters
5. TUI code referencing the fields
6. Test files
```

This prevents intermediate states where type checker sees mismatches.
```

---

#### 16. Frozen Dataclass Mechanical Rename Pattern

**Location:** `docs/learned/refactoring/frozen-dataclass-renames.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Renaming fields on frozen dataclasses
  - Planning type-safe refactors
  - Understanding why frozen dataclasses enable confident renames
---

# Type-Safe Refactoring with Frozen Dataclasses

Frozen dataclasses provide a safety net for mechanical renames.

## Why Frozen Helps

With `@dataclass(frozen=True)`:
- Every field access is explicit (`row.plan_id`)
- Type checker catches any missed renames
- No sneaky `setattr` or dictionary access to bypass checks

## The Refactoring Pattern

1. **Rename the field** in the dataclass definition
2. **Run type checker** (ty, mypy, pyright)
3. **Fix every error** - these are the exact locations needing updates
4. **Trust the type checker** - if it passes, you found everything

## What Type Checking Misses

Even with frozen dataclasses, grep for:
- String literals containing field names (`"issue_number"` in JSON tests)
- Docstrings mentioning the field
- Display strings interpolating the field
- Test assertions comparing against expected strings

## PR #7473 Example

After renaming `PlanRowData.issue_number` -> `plan_id`:
- Type checker caught ~150 field access sites
- Manual grep found ~20 additional string literals
- Total: 176 changes across 19 files
```

---

#### 17. Documentation Bulk Update Pattern

**Location:** `docs/learned/documentation/bulk-update-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Updating documentation during renames
  - Planning doc updates for large refactors
  - Learning systematic doc maintenance approach
---

# Documentation Bulk Update Pattern

When renaming code, update docs systematically:

## The Pattern

1. **Grep for references** across both `src/` and `docs/`
2. **Read all matching files** in parallel
3. **Edit systematically** by category:
   - Source code changes first
   - Test files second
   - Documentation third

## PR #7473 Example

The PR updated 8 documentation files alongside code:
- `docs/learned/tui/data-contract.md`
- `docs/learned/tui/plan-row-data.md`
- `docs/learned/tui/architecture.md`
- `docs/learned/tui/action-inventory.md`
- `docs/learned/tui/modal-screen-pattern.md`
- `docs/learned/tui/view-switching.md`
- `docs/learned/tui/index.md`
- `docs/learned/tui/tripwires.md`

## Why Co-Evolution Matters

Updating docs alongside code:
- Prevents drift (docs stay accurate)
- Reduces future maintenance burden
- Validates that you understand all impact areas
- Catches issues early (wrong doc = wrong understanding)
```

---

#### 18. ABC Interface Documentation Patterns

**Location:** `docs/learned/architecture/abc-documentation-patterns.md`
**Action:** CREATE
**Source:** [PR #7473]

**Draft Content:**

```markdown
---
read-when:
  - Documenting ABC interfaces
  - Writing gateway documentation
  - Avoiding method count drift
---

# ABC Interface Documentation Patterns

PR #7473 review found 3 instances of ABC documentation drift. This doc provides patterns to prevent drift.

## Problem

Manual method lists and counts become stale as interfaces evolve:
- "Key methods" lists miss newly added methods
- "5 abstract methods" becomes wrong when a 6th is added
- Field counts on large dataclasses drift silently

## Solutions

### 1. Use Source Pointers

Instead of listing methods, point to the source:

```markdown
See `PlanDataProvider` abstract methods in
`packages/erk-shared/src/erk_shared/gateway/plan_data_provider/abc.py`
```

### 2. Avoid Numeric Counts

Instead of "5 abstract methods", write:

```markdown
Key abstract methods include:
- `fetch_plans()` - retrieves plan list
- `close_plan()` - closes a plan
- ... (see ABC for complete list)
```

### 3. Programmatic Verification

For critical counts, add verification scripts or grep commands:

```bash
# Verify method count
rg "abstractmethod" abc.py | wc -l
```
```

---

#### 19. Documentation Specificity Guidelines

**Location:** `docs/learned/documentation/specificity-guidelines.md`
**Action:** CREATE
**Source:** [PR #7473]

**Draft Content:**

```markdown
---
read-when:
  - Writing learned documentation
  - Deciding detail level for docs
  - Understanding bot vs human review tension
---

# Documentation Specificity Guidelines

## The Tension

PR #7473 revealed tension between:
- **Bot enforcement:** Technical accuracy of every predicate and count
- **Human preference:** High-level guidance without replicating source

Human reviewer dismissed detailed predicate documentation as "overly specific to be in learned docs."

## Guidelines

### What Belongs in docs/learned/

- Mental models and patterns
- Decision frameworks
- Tripwires and warnings
- Cross-cutting concerns
- "Why" explanations

### What Should Stay in Source

- Exact method signatures
- Complete field lists
- Verbatim predicate implementations
- Counts that change frequently

### The Source Pointer Solution

When accuracy matters but detail doesn't:

```markdown
Commands are grouped by availability predicate.
See `registry.py` for current predicate implementations.
```

This maintains accuracy without maintenance burden.
```

---

#### 20. Documentation Co-Evolution During Refactoring

**Location:** `docs/learned/documentation/doc-code-sync.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Planning refactors that affect documentation
  - Understanding doc maintenance during code changes
  - Learning the co-evolution pattern
---

# Documentation Co-Evolution

Update documentation alongside code changes, not after.

## The Pattern

During refactoring:
1. Identify affected docs (grep for terms being renamed)
2. Include doc updates in the same PR
3. Verify doc accuracy as part of implementation

## Benefits

- Docs stay accurate (never drift)
- Validates understanding (wrong doc = wrong mental model)
- Reduces future maintenance
- Single review for code + docs

## PR #7473 Example

The PR updated 8 documentation files alongside 24 source files. This co-evolution:
- Kept `docs/learned/tui/` accurate
- Caught 9 documentation drift instances via audit-pr-docs bot
- Demonstrated model behavior for future refactors

## Anti-Pattern

"I'll update docs later" leads to:
- Forgotten updates
- Docs that drift silently
- Future agents re-learning solved problems
```

---

### LOW Priority

#### 21. PR Edit Fallback Pattern

**Location:** `docs/learned/pr-operations/pr-edit-fallback.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Creating PRs from multi-session implementations
  - Handling gh pr create failures
  - Working with existing PRs
---

# PR Edit Fallback Pattern

When `gh pr create` fails because a PR already exists, fall back to `gh pr edit`.

## Pattern

```bash
# Try create first
gh pr create --title "Title" --body "Body"

# If fails with "already exists", get PR number and edit
gh pr edit 7473 --title "Title" --body "Body"
```

## When This Happens

- Multi-part implementation sessions
- Resumed work on an existing branch
- Previous session created PR, current session wants to update

## Implementation

See PR #7473 session part 9 for example: `gh pr create` failed, agent immediately pivoted to `gh pr edit 7473`.
```

---

#### 22. Test Parameter Validation After Refactoring (Potential Tripwire)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Test Parameter Validation

**Trigger:** When refactoring method signatures

**Warning:** Check all test call sites including those using `**kwargs` or keyword arguments that may not trigger type errors.

**Context:** Type checkers don't catch all parameter mismatches in tests, especially with dynamic patterns.

**Potential tripwire score:** 2/10 (Non-obvious +2)
```

---

#### 23. Test Method Name False Positives in Grep (Potential Tripwire)

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Test Method Name False Positives

**Trigger:** When grepping for field references during renames

**Warning:** Test method names (e.g., `test_filter_by_issue_number`) are strings, not attribute accesses. Don't count them as actual field usage that needs fixing.

**Context:** After grep finds `issue_number` in a test file, verify whether it's:
- An attribute access (`row.issue_number`) - needs updating
- A method name (`def test_filter_by_issue_number`) - leave alone

**Potential tripwire score:** 2/10 (Non-obvious +2)
```

---

#### 24. Type-Safe Refactoring with Frozen Dataclasses

**Location:** `docs/learned/refactoring/type-safe-refactoring.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Planning large-scale refactors
  - Understanding type safety benefits
  - Working with frozen dataclasses
---

# Type-Safe Refactoring

Frozen dataclasses + strict type checking enable confident mechanical renames.

## The Safety Net

With frozen dataclasses:
- All field access is through explicit attribute access
- Type checker verifies every access site
- No dynamic attribute setting to bypass checks

## Workflow

1. Change the field name in the dataclass
2. Run type checker
3. Fix every error it reports
4. Run tests to catch string literal issues

## What It Catches

- Direct field access (`row.plan_id`)
- Constructor kwargs (`PlanRowData(plan_id=123)`)
- Comparison operations (`row.plan_id == other.plan_id`)

## What It Misses

- JSON key strings (`"issue_number"` in test assertions)
- Display strings (`f"Issue #{row.issue_number}"`)
- Docstrings and comments

Use grep for these after type checking passes.
```

---

#### 25. audit-pr-docs Bot Drift Detection Patterns

**Location:** `docs/learned/ci/audit-pr-docs-patterns.md`
**Action:** CREATE
**Source:** [PR #7473]

**Draft Content:**

```markdown
---
read-when:
  - Interpreting audit-pr-docs bot findings
  - Understanding documentation drift categories
  - Working with the pr-address workflow
---

# audit-pr-docs Bot Patterns

The audit-pr-docs bot detects documentation drift during PR review.

## Categories of Drift

Based on PR #7473 (9 findings):

1. **Wrong predicates:** Docs claim `pr_number is not None` but code checks `pr_url is not None`
2. **Missing items:** Command exists in registry but missing from availability table
3. **Stale counts:** "Six commands" but actually seven
4. **Verbatim code drift:** Copied code block references non-existent field

## Addressing Findings

The pr-address workflow automates fixes:
1. Bot posts findings as review comments
2. `/erk:pr-address` reads comments and applies fixes
3. Fixes committed to same PR branch

## Prevention

- Use source pointers instead of verbatim code
- Avoid numeric counts in prose
- Cross-reference implementation when documenting lists
- Run audits before PR submission
```

---

#### 26. Verification Grep Patterns

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Verification Grep Patterns

Add these greps after completing renames:

```bash
# After renaming field from old_name to new_name
rg "\.old_name" src/ tests/           # Field access
rg "old_name=" src/ tests/            # Constructor kwargs
rg "\"old_name\"" tests/              # JSON keys in assertions
rg "old_name" docs/learned/           # Documentation references
```

Run ALL patterns across BOTH `src/` and `tests/` directories.
```

---

#### 27. Async Agent Work Patterns

**Location:** `docs/learned/planning/agent-async-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - Launching async subagents
  - Managing parallel work during implementations
  - Optimizing agent efficiency
---

# Async Agent Work Patterns

Don't idle while async agents run.

## Pattern

After launching an async subagent (e.g., libcst-refactor):
1. Immediately start parallel work
2. Read files for manual edits
3. Plan next steps
4. Only block when you've exhausted independent work

## PR #7473 Example

After launching libcst-refactor async:
- Started reading files for display string changes
- Identified manual edits (CSS selectors, file renames)
- Prepared for manual work phase

## Anti-Pattern

Launching async agent, then waiting with `TaskOutput(block=true)` immediately. This wastes time that could be used for parallel investigation.
```

---

## Contradiction Resolutions

No contradictions detected. The proposed change is architecturally consistent with existing patterns (`PlanRef` already uses `plan_id: str`).

## Stale Documentation Cleanup

No stale documentation found. All references in existing docs were verified as valid.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Out-of-Scope Changes from Bulk Rename

**What happened:** Bulk sed/libcst renamed `issue_number` in GitHub API layer files that should have been preserved (they refer to actual GitHub issues, not plan identifiers).

**Root cause:** Bulk rename tools operate syntactically, not semantically. Same term used in different semantic domains.

**Prevention:** After bulk renames, use `git diff --stat` to verify only expected files changed. Revert changes to files outside intended scope.

**Recommendation:** TRIPWIRE (score 5)

### 2. Missed References in Test Files

**What happened:** Initial verification only grepped `src/` directory, missing test file references to old names (e.g., `_issue_number` in test assertions).

**Root cause:** Tests often contain string literals and direct attribute access that bypass type checking.

**Prevention:** Always include `tests/` in verification greps for bulk renames.

**Recommendation:** TRIPWIRE (score 5)

### 3. Pre-Existing Test Failures Blocking Progress

**What happened:** Assumed all test failures were caused by current changes, wasted time debugging unrelated issues.

**Root cause:** Codebase had known test failures; no baseline established.

**Prevention:** Use `git stash && pytest && git stash pop` to establish baseline before debugging.

**Recommendation:** ADD_TO_DOC

### 4. Invalid Test Parameters Not Caught by Type Checker

**What happened:** Test was passing invalid `author` parameter that never existed in method signature.

**Root cause:** Test used patterns that bypassed type checking.

**Prevention:** When refactoring method signatures, grep for all call sites (not just type-checked ones) and manually verify parameter compatibility.

**Recommendation:** ADD_TO_DOC

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Gateway Type Change Propagation

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When changing a field type in a dataclass used by gateways
**Warning:** Must update all 5 places: ABC + fake + real for EACH affected gateway (not just one)
**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because a gateway type change that only updates one gateway (e.g., PlanDataProvider) but not another that uses the same type (e.g., CommandExecutor) causes runtime type errors that are hard to trace back to incomplete updates.

### 2. Bulk Rename Scope Verification

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After running bulk rename tools (sed, libcst, ast-grep)
**Warning:** Use `git diff --stat` to verify only expected files changed. Spot-check for semantic boundary violations.
**Target doc:** `docs/learned/refactoring/tripwires.md`

Without this tripwire, bulk renames silently cross semantic boundaries, causing bugs in unrelated areas (e.g., GitHub API parsing breaking because field names changed).

### 3. Multi-Pass Rename Verification

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** After libcst-refactor completes bulk renames
**Warning:** Grep for old patterns in BOTH src/ AND tests/. Check: constructor params, method params, display strings, test assertions, JSON keys.
**Target doc:** `docs/learned/refactoring/tripwires.md`

Tests contain string literals and assertions that type checkers miss. Without multi-pass verification, tests fail with confusing errors about expected vs actual strings.

### 4. Frozen Dataclass Field Renames

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1)
**Trigger:** When renaming fields on frozen dataclasses
**Warning:** Update: field declarations, constructor kwargs at ALL call sites, internal assignments, docstrings, JSON serialization tests.
**Target doc:** `docs/learned/refactoring/tripwires.md`

Missing even one constructor call site causes AttributeError at runtime. The type checker catches most but not all (especially in tests with dynamic patterns).

### 5. TUI Display String Terminology

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When adding new TUI status messages or display strings
**Warning:** Use 'plan' terminology (not 'issue') to maintain consistency with backend-agnostic naming.
**Target doc:** `docs/learned/tui/tripwires.md`

Inconsistent terminology confuses users and creates technical debt for future backend abstraction work.

### 6. Context-Preserved Naming

**Score:** 4/10 (Non-obvious +2, Cross-cutting +2)
**Trigger:** When renaming issue_* -> plan_* in TUI layer
**Warning:** Preserve issue_* in: .impl/issue.json format, plan header YAML, learn fields.
**Target doc:** `docs/learned/planning/tripwires.md`

Over-renaming file format fields breaks persistence and deserialization, causing hard-to-debug errors in plan loading.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Subagent Reconnaissance

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Useful for large refactors but not critical for smaller changes. Could be promoted if future sessions show wasted effort from skipping reconnaissance.

### 2. Test Parameter Validation

**Score:** 2/10 (Non-obvious +2)
**Notes:** Only impacts tests with dynamic patterns. Most test code is type-checked. Promotion unlikely unless pattern becomes more common.

### 3. Test Method Name False Positives

**Score:** 2/10 (Non-obvious +2)
**Notes:** Edge case during grep verification. Experienced agents recognize this quickly. Low severity.

### 4. Documentation Drift in Command Tables

**Score:** 3/10 (Cross-cutting +2, Repeated pattern +1)
**Notes:** 5 findings in PR suggest systematic issue. Could warrant dedicated tripwire in `tui/tripwires.md` with additional evidence.

### 5. ABC Documentation Drift

**Score:** 2/10 (Cross-cutting +2)
**Notes:** 3 findings suggest need for verification pattern. May warrant tripwire if pattern continues.

### 6. libcst Dependency Ordering

**Score:** 2/10 (Non-obvious +2)
**Notes:** Standard software engineering practice. May not need explicit tripwire for experienced agents.

### 7. Scope Discipline in Renames

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Important for domain-crossing renames. The TUI vs API layer distinction is specific to this codebase.

### 8. Pre-Existing Test Failures

**Score:** 2/10 (Non-obvious +2)
**Notes:** Useful debugging technique but not error-prone enough to warrant tripwire. Pattern documented in testing docs.