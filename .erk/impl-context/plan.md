# Fix: Statusline model indicator shows S¹ᴹ for Opus 1M

## Context

The statusline incorrectly shows `S¹ᴹ` (Sonnet 1M) when Opus 4.6 with 1M context is selected. The model ID is `claude-opus-4-6[1m]`, and the code checks for `[1m]` first, hardcoding `S¹ᴹ` for any 1M model regardless of type.

## File to modify

`packages/erk-statusline/src/erk_statusline/statusline.py` (lines 1200-1210)

## Current (buggy) code

```python
model = data.get("model", {}).get("display_name", "")
model_id = data.get("model", {}).get("id", "")
if "[1m]" in model_id.lower():
    model_code = "S¹ᴹ"        # BUG: always Sonnet regardless of actual model
elif "sonnet" in model.lower():
    model_code = "S"
elif "opus" in model.lower():
    model_code = "O"
else:
    model_code = model[:1].upper() if model else "?"
```

## Fix

Determine the model letter first, then append 1M suffix if present:

```python
model = data.get("model", {}).get("display_name", "")
model_id = data.get("model", {}).get("id", "")
if "opus" in model.lower():
    model_code = "O"
elif "sonnet" in model.lower():
    model_code = "S"
elif "haiku" in model.lower():
    model_code = "H"
else:
    model_code = model[:1].upper() if model else "?"
if "[1m]" in model_id.lower():
    model_code += "¹ᴹ"
```

Expected outputs:
- `claude-opus-4-6[1m]` → `O¹ᴹ`
- `claude-sonnet-4-6[1m]` → `S¹ᴹ`
- `claude-haiku-4-5[1m]` → `H¹ᴹ`
- `claude-sonnet-4-6` → `S`

## Verification

1. Run existing tests for statusline
2. Confirm model indicator renders correctly for all model types with and without 1M context
