# Fix: Add `anthropic_api_fast_path` to GlobalConfigSchema

## Context

Commit 83cd5b3dc added `anthropic_api_fast_path` to `GlobalConfig` (runtime dataclass) and the load/save logic in `RealErkInstallation`, but missed adding it to `GlobalConfigSchema` (the Pydantic schema). The schema is the single source of truth for `erk config list/keys/get/set`, so the field is invisible to all CLI config commands.

The root cause extends to the docs: `docs/learned/architecture/globalconfig-field-addition.md` doesn't include a step for adding fields to `GlobalConfigSchema`.

## Changes

### 1. Add field to `GlobalConfigSchema`

**File:** `packages/erk-shared/src/erk_shared/config/schema.py` (after `cmux_integration`, line ~113)

```python
anthropic_api_fast_path: bool = Field(
    description="Use Anthropic API fast path for reduced latency",
    json_schema_extra={"level": ConfigLevel.GLOBAL_ONLY, "cli_key": "anthropic_api_fast_path"},
)
```

### 2. Update field addition checklist doc

**File:** `docs/learned/architecture/globalconfig-field-addition.md`

Add a new step between steps 2 and 3: "Add Field to GlobalConfigSchema" explaining that the Pydantic schema in `schema.py` must also be updated for the field to appear in `erk config list/keys/get/set`.

## Verification

- Run `erk config list` — `anthropic_api_fast_path` should appear in global configuration section
- Run `erk config keys` — field should be listed
- Run `erk config get anthropic_api_fast_path` — should return current value
