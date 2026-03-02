# Fix: Fast slug generation via Anthropic SDK

## Context

When `erk objective plan --one-shot` is called from the TUI, the "calling haiku for slug generation..." step is excessively slow. The current path spawns a full `claude --print --model haiku` subprocess — process fork, CLI cold start, config loading, auth, API round-trip — just to produce a 3-word branch slug. This takes ~5s when it should take ~200ms.

The `/erk:one-shot` **skill** avoids this by generating the slug in the skill layer (step 2) and passing `--slug`. But the TUI → `erk objective plan --one-shot` path has no skill layer to hoist to — it calls the CLI directly.

**Solution:** Add the `anthropic` Python SDK and call Haiku directly (no subprocess), falling back to deterministic sanitization if no API key is available.

## Changes

### 1. Add `anthropic` dependency

**File:** `pyproject.toml` (root)

Add `"anthropic>=0.40.0"` to the `[project] dependencies` list.

### 2. Create fast LLM utility

**New file:** `src/erk/core/fast_llm.py`

Lightweight module for direct Anthropic SDK calls, bypassing the Claude CLI subprocess:

```python
"""Fast LLM calls via Anthropic SDK.

For lightweight operations (slug generation) where spawning a full
Claude CLI subprocess is too slow.
"""

import os

def fast_haiku_call(prompt: str, *, system_prompt: str) -> str | None:
    """Call Haiku directly via Anthropic SDK (~200ms vs ~5s subprocess).

    Returns response text, or None if API key unavailable or call fails.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if api_key is None:
        return None

    try:
        from anthropic import Anthropic

        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=50,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()
    except Exception:
        return None
```

Lazy import of `anthropic` so the module doesn't break if SDK isn't installed. Returns `None` on any failure for clean fallback.

### 3. Update slug generation fallback in `dispatch_one_shot`

**File:** `src/erk/cli/commands/one_shot_dispatch.py` (lines 197-203)

Replace the `claude --print` subprocess call with: fast SDK call → deterministic fallback.

```python
# Before:
else:
    user_output(click.style("  (calling haiku for slug generation...)", dim=True))
    slug_start = time.monotonic()
    slug = generate_branch_slug(ctx.prompt_executor, params.prompt)
    ...

# After:
else:
    from erk.core.fast_llm import fast_haiku_call
    from erk.core.branch_slug_generator import BRANCH_SLUG_SYSTEM_PROMPT, _postprocess_slug

    raw = fast_haiku_call(params.prompt, system_prompt=BRANCH_SLUG_SYSTEM_PROMPT)
    slug = _postprocess_slug(raw) if raw is not None else None
    if slug is None:
        slug = sanitize_worktree_name(params.prompt)[:25].rstrip("-")
        user_output(click.style(f"  ✓ Slug: {slug} (sanitized)", dim=True))
    else:
        user_output(click.style(f"  ✓ Slug: {slug}", dim=True))
```

Remove the now-unused `generate_branch_slug` call at line 200. The `generate_branch_slug` import and `generate_branch_name` helper (lines 61-99) still exist for the dry-run path — leave them.

Add import: `from erk_shared.naming import sanitize_worktree_name`

### 4. Pre-compute slugs in objective plan handlers

**File:** `src/erk/cli/commands/objective/plan_cmd.py`

In `_handle_one_shot` (~line 709) and `_handle_all_unblocked` (~line 251), generate slugs from node descriptions and pass them to `OneShotDispatchParams(slug=...)`:

```python
from erk.core.fast_llm import fast_haiku_call
from erk.core.branch_slug_generator import BRANCH_SLUG_SYSTEM_PROMPT, _postprocess_slug
from erk_shared.naming import sanitize_worktree_name

# In _handle_one_shot:
raw = fast_haiku_call(target_node.description, system_prompt=BRANCH_SLUG_SYSTEM_PROMPT)
slug = _postprocess_slug(raw) if raw is not None else None
if slug is None:
    slug = sanitize_worktree_name(target_node.description)[:25].rstrip("-")

params = OneShotDispatchParams(
    prompt=prompt,
    model=model,
    extra_workflow_inputs={...},
    slug=slug,
)
```

Same pattern in `_handle_all_unblocked` using `node.description`.

## Files Modified

| File | Change |
|------|--------|
| `pyproject.toml` | Add `anthropic` dependency |
| `src/erk/core/fast_llm.py` | **New** — lightweight SDK-based Haiku calls |
| `src/erk/cli/commands/one_shot_dispatch.py` | Replace subprocess slug generation with fast SDK + deterministic fallback |
| `src/erk/cli/commands/objective/plan_cmd.py` | Pre-compute slugs from node descriptions before dispatching |

## Verification

1. Run existing tests: `pytest tests/commands/one_shot/`
2. Run ty/ruff on modified files
3. End-to-end: `erk objective plan <issue> --one-shot` from TUI — slug step should be ~200ms (with API key) or instant (deterministic fallback)
