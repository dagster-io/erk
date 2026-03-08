# Update CHANGELOG.md Unreleased Section

## Context

The CHANGELOG.md unreleased section is synced to `7d49225f8`. Since then, 34 commits have landed on master. After filtering out internal refactors, test infra, build tooling, already-documented commits, and erk-dev commands, 6 user-visible changes warrant changelog entries.

## File to Modify

- `CHANGELOG.md` — Unreleased section only

## Changes

### 1. Update "As of" marker

Change:
```
<!-- As of: 7d49225f8 -->
```
To:
```
<!-- As of: f1268fd27 -->
```

### 2. Add to Added section (1 entry)

Append after the last existing Added entry:
```
- Add Check 8 to `erk objective check` for roadmap table sync validation: detects when the prose roadmap table has drifted from YAML source of truth (20f3cd393)
```

### 3. Add to Changed section (5 entries)

Append after the last existing Changed entry:
```
- Remove `--sync` from `erk pr checkout` (now purely local); add `--script` and `--sync` options to `erk pr teleport` for remote Graphite submission workflows (7065d4546)
- Rename bundled slash command `/erk:rebase` to `/erk:pr-rebase` for consistency with PR-focused command naming (51d6ccb84)
- `erk objective view` now infers the objective from the current branch when no explicit reference is provided (56dbf1a04)
- Add arrow key navigation to the objective nodes screen in TUI (91d3f1143)
- Update `/erk:pr-rebase` skill to use AskUserQuestion for push options (932de4cca)
```

## Verification

After editing, confirm:
1. `<!-- As of: f1268fd27 -->` is at the top of the Unreleased section
2. The Added section has 7 entries (6 existing + 1 new)
3. The Changed section has 7 entries (2 existing + 5 new)
4. The Fixed section is unchanged (1 entry)
5. No existing entries were modified or removed
