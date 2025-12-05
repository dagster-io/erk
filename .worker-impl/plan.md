# Add Command Aliases: `erk pr co` and `erk wt ls`

## Summary

Add two command aliases following the existing alias pattern in the codebase:
- `erk pr co` → alias for `erk pr checkout`
- `erk wt ls` → alias for `erk wt list`

## Implementation

### Step 1: Add `co` alias to `erk pr checkout`

**File: `src/erk/cli/commands/pr/checkout_cmd.py`**
- Add import: `from erk.cli.alias import alias`
- Add `@alias("co")` decorator above `@click.command("checkout")`

**File: `src/erk/cli/commands/pr/__init__.py`**
- Add import: `from erk.cli.alias import register_with_aliases`
- Change `pr_group.add_command(pr_checkout, name="checkout")` to `register_with_aliases(pr_group, pr_checkout)`

### Step 2: Add `ls` alias to `erk wt list`

**File: `src/erk/cli/commands/wt/list_cmd.py`**
- Add import: `from erk.cli.alias import alias`
- Add `@alias("ls")` decorator above `@click.command("list")`

**File: `src/erk/cli/commands/wt/__init__.py`**
- Add import: `from erk.cli.alias import register_with_aliases`
- Change `wt_group.add_command(list_wt)` to `register_with_aliases(wt_group, list_wt)`

### Step 3: Verify

Run the commands to verify aliases work:
```bash
erk pr co --help
erk wt ls --help
```

## Critical Files

- `src/erk/cli/commands/pr/checkout_cmd.py`
- `src/erk/cli/commands/pr/__init__.py`
- `src/erk/cli/commands/wt/list_cmd.py`
- `src/erk/cli/commands/wt/__init__.py`
- `src/erk/cli/alias.py` (reference only - contains the alias infrastructure)