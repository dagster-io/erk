---
description: Detailed exception handling patterns including B904 chaining, third-party API compatibility, and anti-patterns.
---

# Exception Handling Reference

**Read when**: Writing try/except blocks, scoping try-except blocks, wrapping third-party APIs, seeing `from e` or `from None`

---

## When Exceptions ARE Acceptable

Exceptions are ONLY acceptable at:

1. **Error boundaries** (CLI/API level)
2. **Third-party API compatibility** (when no alternative exists)
3. **Adding context before re-raising**

### 1. Error Boundaries

```python
# ACCEPTABLE: CLI command error boundary
@click.command("create")
@click.pass_obj
def create(ctx: ErkContext, name: str) -> None:
    """Create a worktree."""
    try:
        create_worktree(ctx, name)
    except subprocess.CalledProcessError as e:
        click.echo(f"Error: Git command failed: {e.stderr}", err=True)
        raise SystemExit(1)
```

### 2. Third-Party API Compatibility

```python
# ACCEPTABLE: Third-party API forces exception handling
def _get_bigquery_sample(sql_client, table_name):
    """
    BigQuery's TABLESAMPLE doesn't work on views.
    There's no reliable way to determine a priori whether
    a table supports TABLESAMPLE.
    """
    try:
        return sql_client.run_query(f"SELECT * FROM {table_name} TABLESAMPLE...")
    except Exception:
        return sql_client.run_query(f"SELECT * FROM {table_name} ORDER BY RAND()...")
```

> **The test for "no alternative exists"**: Can you validate or check the condition BEFORE calling the API? If yes (even using a different function/method), use LBYL. The exception only applies when the API provides NO way to determine success a priori—you literally must attempt the operation to know if it will work.

### What Does NOT Qualify as Third-Party API Compatibility

Standard library functions with known LBYL alternatives do NOT qualify:

```python
# WRONG: int() has LBYL alternative (str.isdigit)
try:
    port = int(user_input)
except ValueError:
    port = 80

# CORRECT: Check before calling
if user_input.lstrip('-+').isdigit():
    port = int(user_input)
else:
    port = 80

# WRONG: datetime.fromisoformat() can be validated first
try:
    dt = datetime.fromisoformat(timestamp_str)
except ValueError:
    dt = None

# CORRECT: Validate format before parsing
def _is_iso_format(s: str) -> bool:
    return len(s) >= 10 and s[4] == "-" and s[7] == "-"

if _is_iso_format(timestamp_str):
    dt = datetime.fromisoformat(timestamp_str)
else:
    dt = None
```

### 3. Adding Context Before Re-raising

```python
# ACCEPTABLE: Adding context before re-raising
try:
    process_file(config_file)
except yaml.YAMLError as e:
    raise ValueError(f"Failed to parse config file {config_file}: {e}") from e
```

---

## Minimal Exception Scope

**When exceptions are the correct tool, scope the try block to the single operation that raises.**

The LBYL philosophy extends into exception handling itself: minimize the region of code governed by implicit control flow. A try-except block should be a surgical instrument targeting one operation, not a safety net draped over a paragraph of logic.

### The Problem with Broad Try Blocks

```python
# WRONG: Broad scope — RuntimeError catch covers subprocess AND json AND update
try:
    result = run_subprocess(cmd)
    output = json.loads(result.stdout)
    if output.get("success"):
        update_metadata(output)
except RuntimeError as e:
    logger.warning(f"Failed: {e}")
```

This is problematic even when exceptions are justified:

1. **Imprecise attribution** — the handler cannot distinguish which operation raised `RuntimeError`
2. **Accidental catch** — if `update_metadata` later starts raising `RuntimeError`, this handler silently swallows it
3. **Coupled recovery** — different operations may need different error messages or recovery strategies

### The Pattern: One Operation Per Try Block

Scope each try-except to the single operation that can raise. Use early returns to keep subsequent code flat:

```python
# CORRECT: Each try wraps exactly one operation
try:
    result = run_subprocess(cmd)
except RuntimeError as e:
    logger.warning(f"Subprocess failed: {e}")
    return

try:
    output = json.loads(result.stdout)
except json.JSONDecodeError:
    logger.warning(f"Bad JSON: {result.stdout}")
    return

if output.get("success"):
    update_metadata(output)
```

Each handler knows exactly what failed. New code between the blocks cannot be accidentally caught. Different operations get different exception types, different messages, and different recovery logic.

### When Broader Scope Is Acceptable

A try block MAY contain multiple statements when they form an **atomic unit** — a failure in any part means the same thing and requires the same recovery:

```python
# ACCEPTABLE: Atomic unit — both lines are "reading the config file"
try:
    raw = config_path.read_text(encoding="utf-8")
    config = tomllib.loads(raw)
except (OSError, tomllib.TOMLDecodeError) as e:
    raise UserFacingCliError(f"Failed to read config: {e}") from e
```

**The test**: if the handler's message and recovery action would be identical regardless of which line raised, the scope is appropriate. If you would write a different message or take a different action, split the blocks.

### Race Condition Exception: TOCTOU Hazards

File system operations are the canonical case where try-except legitimately wraps the check-and-act pair, because the state can change between check and action:

```python
# ACCEPTABLE: TOCTOU — file may disappear between stat() and unlink()
try:
    if script_file.stat().st_mtime < cutoff:
        script_file.unlink()
except (FileNotFoundError, PermissionError):
    continue
```

This is not a violation of minimal scope — the two lines are logically atomic because splitting them would introduce the exact race condition the try-except is guarding against.

### Relationship to LBYL

This standard is subordinate to LBYL. The decision tree:

1. **Can you check the condition before acting?** → Use LBYL, no try-except at all
2. **Do callers branch on the error type?** → Use discriminated unions (see `discriminated-union-error-handling.md`)
3. **Must you use try-except?** → Scope it to the single operation that raises

Minimal exception scope is how you stay true to the LBYL philosophy even when exceptions are unavoidable: you minimize the region of code governed by implicit control flow.

---

## Exception Chaining (B904 Lint Compliance)

**Ruff rule B904** requires explicit exception chaining when raising inside an `except` block. This prevents losing the original traceback.

```python
# CORRECT: Chain to preserve context
try:
    parse_config(path)
except ValueError as e:
    click.echo(json.dumps({"success": False, "error": str(e)}))
    raise SystemExit(1) from e  # Preserves traceback

# CORRECT: Explicitly break chain when intentional
try:
    fetch_from_cache(key)
except KeyError:
    # Original exception is not relevant to caller
    raise ValueError(f"Unknown key: {key}") from None

# WRONG: Missing exception chain (B904 violation)
try:
    parse_config(path)
except ValueError:
    raise SystemExit(1)  # Lint error: missing 'from e' or 'from None'

# CORRECT: CLI error boundary with JSON output
try:
    result = some_operation()
except RuntimeError as e:
    click.echo(json.dumps({"success": False, "error": str(e)}))
    raise SystemExit(0) from None  # Exception is in JSON, traceback irrelevant to CLI user
```

**When to use each:**

- `from e` - Preserve original exception for debugging
- `from None` - Intentionally suppress original (e.g., transforming exception type, CLI JSON output)

---

## Exception Anti-Patterns

**Never swallow exceptions silently**

Even at error boundaries, you must at least log/warn so issues can be diagnosed:

```python
# WRONG: Silent exception swallowing
try:
    risky_operation()
except:
    pass

# WRONG: Silent swallowing even at error boundary
try:
    optional_feature()
except Exception:
    pass  # Silent - impossible to diagnose issues

# CORRECT: Let exceptions bubble up (default)
risky_operation()

# CORRECT: At error boundaries, log the exception
try:
    optional_feature()
except Exception as e:
    logging.warning("Optional feature failed: %s", e)  # Diagnosable
```

**Never use silent fallback behavior**

```python
# WRONG: Silent fallback masks failure
def process_text(text: str) -> dict:
    try:
        return llm_client.process(text)
    except Exception:
        return regex_parse_fallback(text)

# CORRECT: Let error bubble to boundary
def process_text(text: str) -> dict:
    return llm_client.process(text)
```
