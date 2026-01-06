# Plan: Add Keyword-Only Arguments Rule to dignified-python

## Summary

Add documentation for the "keyword-only arguments for functions with 5+ parameters" rule to the dignified-python skill, including the `ctx` exception and `ThreadPoolExecutor.submit()` special case. Also add a tripwire.

## Files to Modify

1. `.claude/skills/dignified-python/dignified-python-core.md` - Add new section
2. `docs/learned/tripwires.md` - Add tripwire (via frontmatter in source doc)

## Implementation

### 1. Add Section to dignified-python-core.md

**Location:** After "Default Parameter Values Are Dangerous" (~line 932), before "Speculative Tests" (~line 935)

**Section Content:**

```markdown
### Keyword-Only Arguments for Complex Functions

**Functions with 5 or more parameters MUST use keyword-only arguments.**

Use the `*` separator after the first positional parameter to enforce keyword-only at the language level. This improves call-site readability by forcing explicit parameter names.

```python
# ✅ CORRECT: Keyword-only after first param
def fetch_data(
    url,
    *,
    timeout: float,
    retries: int,
    headers: dict[str, str],
    auth_token: str,
) -> Response:
    ...

# Call site is self-documenting
response = fetch_data(
    api_url,
    timeout=30.0,
    retries=3,
    headers={"Accept": "application/json"},
    auth_token=token,
)

# ❌ WRONG: All positional parameters
def fetch_data(
    url,
    timeout: float,
    retries: int,
    headers: dict[str, str],
    auth_token: str,
) -> Response:
    ...

# Call site is unreadable - what do these values mean?
response = fetch_data(api_url, 30.0, 3, {"Accept": "application/json"}, token)
```

**Exceptions:**

1. **`self`** - Always positional (Python requirement)
2. **`ctx` / context objects** - Can remain positional as the first parameter (convention)
3. **ABC/Protocol methods** - Exempt to avoid forcing all implementations to change signatures
4. **Click callbacks** - Click injects parameters; follow Click conventions

```python
# ✅ CORRECT: ctx stays positional, rest are keyword-only
def create_worktree(
    ctx: ErkContext,
    *,
    branch_name: str,
    base_branch: str,
    path: Path,
    checkout: bool,
) -> WorktreeInfo:
    ...
```

**Special Case: ThreadPoolExecutor.submit()**

`ThreadPoolExecutor.submit()` passes arguments positionally to the callable. For functions with keyword-only parameters, wrap the call in a lambda:

```python
# ❌ WRONG: submit() passes args positionally - fails with keyword-only functions
future = executor.submit(fetch_data, url, timeout, retries, headers, token)

# ✅ CORRECT: Lambda enables keyword arguments
future = executor.submit(
    lambda: fetch_data(
        url,
        timeout=timeout,
        retries=retries,
        headers=headers,
        auth_token=token,
    )
)
```
```

### 2. Add Tripwire

Add to `docs/learned/tripwires.md` (via source frontmatter):

```
**CRITICAL: Before adding a function with 5+ parameters** → Load `dignified-python` skill first. Use keyword-only arguments (add `*` after first param). Exception: ABC/Protocol method signatures.
```

### 3. Add to Decision Checklist

Add to the "Decision Checklist" section at end of dignified-python-core.md:

```markdown
### Before adding a function with 5+ parameters:

- [ ] Have I added `*` after the first (or ctx) parameter?
- [ ] Is only `self`/`ctx` positional?
- [ ] Is this an ABC/Protocol method? (exempt from rule)
- [ ] If using ThreadPoolExecutor.submit(), am I using a lambda wrapper?

**Default: All parameters after the first should be keyword-only**
```