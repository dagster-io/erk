# Public Documentation Quick Fixes

Fix incorrect command references, config file paths, and version numbers in public documentation.

## Summary

8 edits across 6 files to fix outdated references.

## Changes

### 1. `docs/tutorials/first-plan.md`

**Line 175** - Code block:
```diff
-erk pr land
+erk land
```

**Line 214** - Table row:
```diff
-| Land PR              | `erk pr land`                                  |
+| Land PR              | `erk land`                                     |
```

### 2. `docs/howto/local-workflow.md`

**Line 75** - Code block:
```diff
-erk pr land
+erk land
```

### 3. `docs/howto/navigate-branches-worktrees.md`

**Line 95** - Table row:
```diff
-| Land PR and navigate up             | `erk pr land --up`                    |
+| Land PR and navigate up             | `erk land --up`                       |
```

### 4. `docs/user/project-setup.md`

**Line 15** - Paragraph text:
```diff
-This creates the `erk.toml` configuration file in your repository root.
+This creates the `.erk/config.toml` configuration file in your repository.
```

**Line 57** - Bullet item:
```diff
-- **`erk.toml`** - Project configuration (created by `erk init`)
+- **`.erk/config.toml`** - Project configuration (created by `erk init`)
```

### 5. `docs/user/developer-onboarding.md`

**Line 20** - Bullet item:
```diff
-- **`erk.toml`** - Project configuration
+- **`.erk/config.toml`** - Project configuration
```

### 6. `docs/tutorials/installation.md`

**Line 24** - Expected output text:
```diff
-You should see output like `erk 0.4.x`.
+You should see output like `erk 0.7.x`.
```

## Verification

After making changes:
1. Grep for any remaining `erk pr land` references: `grep -r "erk pr land" docs/`
2. Grep for any remaining `erk.toml` references: `grep -r "erk\.toml" docs/`
3. Verify the correct command exists: `erk land --help`