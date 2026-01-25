---
title: Tripwire System
read_when:
  - "understanding how tripwires work"
  - "adding new tripwire rules to documentation"
  - "understanding behavioral routing for agents"
  - "working with docs/learned/tripwires.md"
---

# Tripwire System

Tripwires are action-triggered safety rules embedded in documentation frontmatter. They're automatically compiled into `docs/learned/tripwires.md` and consulted by agents before taking matching actions.

## How Tripwires Work

### 1. Creation

Developers add tripwires to documentation frontmatter:

```yaml
---
title: Erk Architecture Patterns
read_when:
  - "understanding erk architecture"
tripwires:
  - action: "calling os.chdir() in erk code"
    warning: "After os.chdir(), regenerate context using regenerate_context(ctx, repo_root=repo.root). Stale ctx.cwd causes FileNotFoundError."
  - action: "passing dry_run boolean flags through business logic"
    warning: "Use dependency injection with DryRunGit/DryRunGitHub wrappers."
---
```

### 2. Compilation

Running `erk docs sync` extracts all tripwires and generates `docs/learned/tripwires.md`:

```markdown
# Tripwires

Action-triggered rules. You MUST consult these BEFORE taking any matching action.

**CRITICAL: Before calling os.chdir() in erk code** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. After os.chdir(), regenerate context...

**CRITICAL: Before passing dry_run boolean flags through business logic** → Read [Erk Architecture Patterns](architecture/erk-architecture.md) first. Use dependency injection...
```

### 3. Consultation

Agents consult `tripwires.md` before taking actions. The file is loaded via AGENTS.md:

```markdown
@docs/learned/tripwires.md
```

### 4. Safety Net

Tripwires catch patterns before they cause bugs. They're preventive, not reactive.

## Tripwire Structure

Each tripwire has two required fields:

| Field | Description |
|-------|-------------|
| `action` | The pattern that triggers the tripwire (gerund phrase) |
| `warning` | What to do instead, with context on why |

### Writing Effective Actions

Use gerund phrases that match how an agent would describe their action:

```yaml
# GOOD - matches agent's description of action
action: "calling os.chdir() in erk code"
action: "adding a new method to Git ABC"
action: "using subprocess.run with git command outside of a gateway"

# BAD - too vague
action: "changing directories"
action: "adding methods"
action: "using subprocess"
```

### Writing Effective Warnings

Include:

1. What to do instead
2. Why the original approach is problematic
3. Link to relevant documentation (automatic via source file)

```yaml
# GOOD - actionable with context
warning: "Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway, accessible only through BranchManager."

# BAD - no alternative provided
warning: "Don't do this."
```

## Tripwire Categories

Tripwires cover common mistake patterns:

| Category | Examples |
|----------|----------|
| **Context management** | os.chdir(), context regeneration |
| **Gateway patterns** | 5-place implementation, subprocess in gateways |
| **Branch mutations** | Use branch_manager not git/graphite directly |
| **Time handling** | Use context.time.sleep() not time.sleep() |
| **Config handling** | local_config precedence over global_config |
| **GitHub API** | Rate limits, retry mechanisms, GraphQL syntax |
| **Path resolution** | Use dedicated helpers not path comparisons |

## Adding New Tripwires

### Step 1: Identify the Pattern

Look for:

- Bugs that could have been prevented with a check
- Common mistakes in code reviews
- Patterns that require specific handling

### Step 2: Find the Right Document

Add the tripwire to the document that explains the correct approach:

- Gateway patterns → `gateway-abc-implementation.md`
- Architecture patterns → `erk-architecture.md`
- GitHub quirks → `github-api-rate-limits.md`

### Step 3: Add to Frontmatter

```yaml
---
title: Existing Document
tripwires:
  - action: "doing the problematic thing"
    warning: "Do this instead. Reason why."
---
```

### Step 4: Regenerate

```bash
erk docs sync
```

This updates `tripwires.md` with the new rule.

## Tripwire vs read_when

Both guide agent behavior but serve different purposes:

| Aspect | `read_when` | `tripwires` |
|--------|-------------|-------------|
| Timing | Before starting work | Before specific actions |
| Scope | Topic exploration | Pattern prevention |
| Tone | "Read this when..." | "CRITICAL: Before..." |
| Goal | Context building | Mistake prevention |

## Example Tripwires

### Gateway Implementation

```yaml
tripwires:
  - action: "adding a new method to Git ABC"
    warning: "Must implement in 5 places: abc.py, real.py, fake.py, dry_run.py, printing.py."
```

### Branch Mutations

```yaml
tripwires:
  - action: "calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch)"
    warning: "Use ctx.branch_manager instead. Branch mutation methods are in GitBranchOps sub-gateway."
```

### Time Handling

```yaml
tripwires:
  - action: "importing time module or calling time.sleep()"
    warning: "Use context.time.sleep() and context.time.now() for testability."
```

## Related Topics

- [Documentation Guide](../guide.md) - Overall documentation organization
- [Gateway ABC Implementation](gateway-abc-implementation.md) - Gateway tripwires source
- [Erk Architecture Patterns](erk-architecture.md) - Architecture tripwires source
