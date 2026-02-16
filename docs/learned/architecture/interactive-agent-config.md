---
title: Interactive Agent Configuration
last_audited: "2026-02-07 00:00 PT"
audit_result: clean
tripwires:
  - action: "modifying InteractiveAgentConfig fields or config file format"
    warning: "Update both config loading (RealErkInstallation.load_config) and usage sites. Check backward compatibility with [interactive-claude] section."
  - action: "changing config section names ([interactive-claude] or [interactive-agent])"
    warning: "Maintain fallback from [interactive-agent] to [interactive-claude] for backward compatibility."
read_when:
  - "Working with global config loading (GlobalConfig)"
  - "Implementing interactive agent launch behavior"
  - "Adding new agent configuration options"
---

# Interactive Agent Configuration

## Cross-Cutting Pattern

`InteractiveAgentConfig` bridges two concepts that must stay synchronized:

1. **Config-level defaults** stored in `~/.erk/config.toml`
2. **CLI-level overrides** passed as flags to agent commands

The design enforces CLI-always-wins semantics through explicit override methods rather than implicit merging.

## Why Explicit Overrides Matter

**Problem:** Implicit merging of config + CLI flags makes it unclear where values originate. Did `--dangerous` get set explicitly or fall through from config?

**Solution:** `InteractiveAgentConfig.with_overrides()` takes optional parameters that explicitly signal "override this field" (non-None) vs "keep config value" (None). This makes CLI flag precedence auditable at every call site.

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, InteractiveAgentConfig.with_overrides -->

See `InteractiveAgentConfig.with_overrides()` in `packages/erk-shared/src/erk_shared/context/types.py` for the parameter-by-parameter override logic.

## Backward Compatibility Pattern

Config loading checks `[interactive-agent]` first, then falls back to `[interactive-claude]` if not found. This allows gradual migration without breaking existing configs:

```toml
# Legacy format (still works)
[interactive-claude]
model = "claude-opus-4-6"

# Future format (preferred)
[interactive-agent]
model = "claude-opus-4-6"
```

<!-- Source: packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py, RealErkInstallation.load_config -->

See `RealErkInstallation.load_config()` in `packages/erk-shared/src/erk_shared/gateway/erk_installation/real.py` for the fallback implementation (`data.get("interactive-agent", data.get("interactive-claude", {}))`).

**Why both section names exist:** The original implementation hardcoded Claude-specific naming before multi-backend support was planned. Rather than force all users to migrate configs immediately, the fallback pattern preserves existing configs while allowing new configs to use backend-agnostic naming.

## Boolean Coercion for Safety

All boolean fields pass through `bool()` during config loading:

```python
verbose=bool(ia_data.get("verbose", False))
```

**Why:** TOML parsers can return various truthy/falsy values. Explicit coercion normalizes them to Python `True`/`False`, preventing subtle bugs where `"false"` (string) is truthy.

## Permission Mode Cross-Cutting

`InteractiveAgentConfig.permission_mode` uses the generic `PermissionMode` enum (`"safe"`, `"edits"`, `"plan"`, `"dangerous"`) which maps to backend-specific flags at launch time.

For Claude backend mapping and `dangerous` mode's dual-flag requirement (`--permission-mode bypassPermissions` + `--dangerously-skip-permissions`), see [PermissionMode Abstraction](permission-modes.md).

## Decision: Why No Default Parameters in with_overrides()

The `with_overrides()` method uses `| None` parameters instead of defaults:

```python
# Actual signature
def with_overrides(
    self,
    *,
    permission_mode_override: PermissionMode | None,
    model_override: str | None,
    # ...
)

# NOT this
def with_overrides(
    self,
    *,
    permission_mode_override: PermissionMode | None = None,
    model_override: str | None = None,
    # ...
)
```

**Why:** This follows erk's no-default-parameters standard. The caller must explicitly pass `None` to mean "keep config value", making the intent visible at every call site. See [conventions.md](../conventions.md) for the broader rationale behind this standard.

## Related Documentation

- [PermissionMode Abstraction](permission-modes.md) — Backend-specific permission mode mappings
- [Conventions](../conventions.md) — Erk's no-default-parameters standard
