# Update Installation Documentation for erk-bootstrap

## Summary

Update documentation to reflect the new installation architecture where shell integration uses `uvx erk-bootstrap` to delegate to project-local erk installations. The key change is:

**Old model:** Install erk globally with `uv tool install erk`
**New model:** Install erk per-project with `uv add erk && uv sync`, shell integration uses `uvx erk-bootstrap`

## Key Documentation Files to Update

### 1. README.md (Quick Start)

**File:** `README.md`

**Current (line 14-15):**
```bash
# Install erk
uv tool install erk
```

**New:**
```bash
# In your project directory
uv add erk && uv sync
```

**Rationale:** Users install erk as a project dependency, not globally. Shell integration (set up by `erk init`) uses uvx to run erk-bootstrap which delegates to the project-local erk.

### 2. docs/tutorials/installation.md (Main Installation Docs)

**File:** `docs/tutorials/installation.md`

**Major changes:**
- Replace "Install erk as a global CLI tool" with per-project installation
- Update "Why `uv tool install`?" section to explain the new architecture
- Change `uv tool install erk` to `uv add erk && uv sync`
- Update troubleshooting section

**New Install section (lines 7-35):**
```markdown
## Install erk

Install erk as a project dependency:

```bash
cd your-project
uv add erk
uv sync
```

**How shell integration works:**

When you run `erk init --shell`, it adds a shell function that uses `uvx erk-bootstrap` to:
1. Find your project's `.venv/bin/erk`
2. Delegate commands to your project-local erk
3. Handle shell-specific features like directory switching

This means:
- **Per-project isolation**: Each project can have its own erk version
- **No global installation needed**: Shell integration handles discovery
- **Easy updates**: Update erk per-project with `uv upgrade erk`

**Verify the installation:**

```bash
# In your project directory (with venv activated)
erk --version
```
```

### 3. packages/erk-bootstrap/README.md

**File:** `packages/erk-bootstrap/README.md`

**Changes:**
- Clarify that erk-bootstrap is used automatically by shell integration
- Users don't need to install it manually (uvx handles it)

**Updated content:**
```markdown
# erk-bootstrap

Thin bootstrap CLI that delegates to project-local erk installations.

## How it's used

Shell integration (set up by `erk init --shell`) automatically uses this package via `uvx`:
- Users don't need to install erk-bootstrap manually
- `uvx erk-bootstrap` is called by the shell wrapper function
- It finds your project's `.venv/bin/erk` and delegates commands

## Manual installation (optional)

For users who prefer a persistent global command:

```bash
uv tool install erk-bootstrap
```

## How it works

When you run `erk` commands, this bootstrap:

1. Looks for `.venv/bin/erk` or `venv/bin/erk` walking up from current directory
2. If found, delegates the command to the project-local erk
3. If not found, shows a helpful error message

## Override

Set `ERK_VENV` environment variable to point to a specific venv:

```bash
ERK_VENV=/path/to/my/venv erk wt list
```

## Per-project installation

In each project where you want to use erk:

```bash
uv add erk
uv sync
```
```

### 4. docs/tutorials/shell-integration.md (Optional)

**File:** `docs/tutorials/shell-integration.md`

**Line 157:** Update example that shows `command erk` workaround.

**Current:**
```bash
command erk wt checkout my-feature  # Bypass shell function
```

**Note:** This example may still be valid as a way to bypass the shell function entirely, but should clarify that it requires erk to be in PATH (either via venv activation or global install). Consider updating the explanation.

## Files Summary

| File | Priority | Change |
|------|----------|--------|
| `README.md` | High | Update Quick Start to show `uv add erk && uv sync` |
| `docs/tutorials/installation.md` | High | Rewrite installation section for new architecture |
| `packages/erk-bootstrap/README.md` | Medium | Clarify automatic usage via uvx |
| `docs/tutorials/shell-integration.md` | Low | Optional update to `command erk` examples |

## Verification

After making changes:
1. Review that all installation instructions are consistent
2. Test the documented workflow in a fresh project:
   ```bash
   mkdir test-project && cd test-project
   git init
   uv init
   uv add erk
   uv sync
   .venv/bin/erk init --shell
   source ~/.zshrc  # or restart shell
   erk doctor
   ```