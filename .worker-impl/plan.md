# Rename erk_shared.integrations → erk_shared.gateways

## Task

Rename the `integrations` module to `gateways` with no backwards compatibility.

## Steps

1. **Rename directory**
   - `packages/erk-shared/src/erk_shared/integrations/` → `packages/erk-shared/src/erk_shared/gateways/`

2. **Update all imports** (find/replace across codebase)
   - Replace `erk_shared.integrations` → `erk_shared.gateways` in all `.py` files

3. **Rename test directories** (if they exist)
   - Check for `packages/erk-shared/tests/unit/integrations/` → rename to `gateways/`

4. **Run verification**
   - `pyright` for type checking
   - `pytest` for tests

## Files to Modify

- ~56 source files in `packages/erk-shared/src/erk_shared/integrations/`
- ~90+ import statements across tests and source
