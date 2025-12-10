# Artifact Lifecycle Management

This guide covers common operations when maintaining kit artifacts: renaming, moving, deleting, and validating changes.

## The Three-Step Synchronization Principle

When working with bundled kits in dev mode, changes must be synchronized across **three locations**:

1. **Source file** - The actual artifact file in `packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/`
2. **Manifest** - The `kit.yaml` file that declares which artifacts belong to the kit
3. **Installed artifact** - The symlink in `.claude/` pointing to the source file

**Critical insight**: Symlinks sync file **contents** automatically, but renaming/moving/deleting requires **manifest updates and reinstallation**.

## Renaming an Artifact

### When to Use This

- Changing a command name (e.g., `/create-from-plan` → `/erk:save-context-enriched-plan`)
- Standardizing naming conventions
- Improving clarity or consistency

### Step-by-Step Procedure

**1. Rename the source file**

```bash
cd packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>
git mv commands/old-name.md commands/new-name.md
```

**2. Update kit.yaml manifest**

Edit `packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/kit.yaml`:

```yaml
artifacts:
  command:
    - commands/erk/create-planned-wt.md # OLD (deleted)
    - commands/erk/persist-plan.md # NEW
    - commands/erk/create-planned-wt.md # NEW
```

**3. Update cross-references**

Search for references to the old artifact name in other files:

```bash
# Search for old command name
grep -r "create-from-plan" packages/dot-agent-kit/src/dot_agent_kit/data/kits/

# Common places to check:
# - Other command files that reference this command
# - Documentation that mentions the command
# - Examples or usage guides
```

Update references:

- Command invocations: `/erk:old-name` → `/erk:new-name`
- File references: `old-name.md` → `new-name.md`
- Descriptions mentioning the command

**4. Force-reinstall the kit**

```bash
# From repository root
erk kit remove <kit-name>
erk kit install bundled:<kit-name> --force
```

This recreates the symlink with the correct target.

**5. Verify the changes**

```bash
erk check
```

Should show: `✅ All checks passed!`

If you see "Missing artifacts", check that kit.yaml paths match actual files.

### Real Example: create-planned-wt split into persist-plan + create-planned-wt

This refactoring split one command into two separate commands:

```bash
# 1. Files created/modified
# - Created: commands/erk/persist-plan.md
# - Rewrote: commands/erk/create-planned-wt.md (simplified version)

# 2. kit.yaml updated
# Changed single entry to two entries:
#   - commands/erk/persist-plan.md
#   - commands/erk/create-planned-wt.md

# 3. Cross-references updated in implement-plan.md
# Updated references to new two-step workflow

# 4. Reinstall
erk kit remove erk
erk kit install bundled:erk --force

# 5. Verify
erk check
```

### Common Mistakes

❌ **Renaming file but forgetting kit.yaml** → `erk check` shows "Missing artifact"
❌ **Updating kit.yaml but not reinstalling** → Old symlink remains, points to non-existent file
❌ **Forgetting cross-references** → Other commands reference non-existent command name

## Deleting an Artifact

### When to Use This

- Removing deprecated commands/skills/agents
- Consolidating functionality into other artifacts
- Cleaning up unused items

### Step-by-Step Procedure

**1. Delete the source file**

```bash
git rm packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit-name>/path/to/artifact.md
```

**2. Remove from kit.yaml manifest**

Edit `kit.yaml` and remove the artifact entry:

```yaml
artifacts:
  command:
    - commands/erk/keep-this.md
    - commands/erk/delete-this.md # REMOVE THIS LINE
```

**3. Update cross-references**

Search for and remove/update any references to the deleted artifact:

```bash
grep -r "deleted-command-name" packages/dot-agent-kit/
```

Replace invocations with:

- Alternative command (if functionality moved)
- Removal (if functionality deprecated)

**4. Force-reinstall the kit**

```bash
erk kit remove <kit-name>
erk kit install bundled:<kit-name> --force
```

This removes the orphaned symlink.

**5. Verify deletion**

```bash
# Should not list the deleted artifact
erk artifact list

# Should pass with no missing artifacts
erk check
```

### Real Example: view-pr and view-plan deletion

From commit f967aff2:

```bash
# 1. Files deleted
git rm commands/gt/view-pr.md
git rm commands/erk/view-plan.md

# 2. kit.yaml entries removed from respective kits

# 3. No cross-references existed (these were standalone commands)

# 4. Reinstall both kits
erk kit remove gt
erk kit install bundled:gt --force
erk kit remove erk
erk kit install bundled:erk --force

# 5. Verify
erk check
```

## Moving an Artifact

### When to Use This

- Reorganizing kit directory structure
- Moving artifact between kits
- Creating namespace hierarchies

### Step-by-Step Procedure

**1. Move the source file**

```bash
# Within same kit
git mv packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit>/old/path/artifact.md \
       packages/dot-agent-kit/src/dot_agent_kit/data/kits/<kit>/new/path/artifact.md

# Between kits (more complex, see below)
```

**2. Update kit.yaml manifest**

Update the path in `kit.yaml`:

```yaml
artifacts:
  command:
    - old/path/artifact.md # OLD
    - new/path/artifact.md # NEW
```

**3. Update cross-references**

File references may need path updates:

```bash
grep -r "old/path/artifact.md" packages/dot-agent-kit/
```

**4. Force-reinstall**

```bash
erk kit remove <kit-name>
erk kit install bundled:<kit-name> --force
```

**5. Verify**

```bash
erk check
```

### Moving Between Kits

Moving an artifact from one kit to another requires updating **both** kits:

**Kit A (source):**

1. Delete file from Kit A source directory
2. Remove from Kit A's kit.yaml
3. Reinstall Kit A

**Kit B (destination):**

1. Add file to Kit B source directory
2. Add to Kit B's kit.yaml
3. Update command namespace if needed (e.g., `/kitA:cmd` → `/kitB:cmd`)
4. Reinstall Kit B

**Update references:**

- Change command invocations to new namespace
- Update any documentation mentioning the command

## Validation After Changes

### Always Run These Commands

After any artifact modification:

```bash
# 1. Check kit integrity
erk check

# 2. List artifacts to verify installation
erk artifact list

# 3. Test the artifact (if command)
/command-name --help  # or actual invocation

# 4. Verify symlinks (dev mode)
ls -la .claude/commands/<namespace>/
```

### Interpreting `erk check` Output

**✅ Success:**

```
✅ All checks passed!
```

**❌ Missing artifact:**

```
Missing artifacts (in manifest but not installed):
  - .claude/commands/erk/artifact-name.md
```

**Diagnosis:**

- Check kit.yaml has correct path
- Verify source file exists
- Force-reinstall the kit

**❌ Stale symlink:**

Symptom: File appears in `.claude/` but `check` reports missing

Diagnosis:

```bash
# Check what symlink points to
readlink .claude/commands/erk/artifact-name.md

# Should point to existing file, not deleted/renamed file
```

Fix: Reinstall kit to recreate symlink

## Common Troubleshooting

### "Artifact not found after rename"

**Symptoms:**

- `erk check` shows missing artifact
- Command invocation fails

**Causes:**

1. kit.yaml not updated with new filename
2. Cross-references still use old name
3. Kit not reinstalled after changes

**Fix:**

- Update kit.yaml manifest
- Force-reinstall kit
- Run `erk check` to verify

### "Symlink points to non-existent file"

**Symptoms:**

- Symlink exists in `.claude/` but broken
- `ls -la` shows red/broken symlink indicator

**Causes:**

1. Source file renamed but kit not reinstalled
2. Source file deleted but manifest still references it

**Fix:**

```bash
# Remove and reinstall kit
erk kit remove <kit-name>
erk kit install bundled:<kit-name> --force
```

### "Command not discoverable after changes"

**Symptoms:**

- Artifact appears in `erk artifact list`
- Command still doesn't work

**Causes:**

1. Naming convention violated (must use kebab-case)
2. Namespace incorrect (should match directory structure)
3. Metadata malformed in artifact frontmatter

**Fix:**

- Verify kebab-case naming
- Check namespace matches directory path
- Validate YAML frontmatter

## Dev Mode Gotchas

### Symlinks Sync Contents, Not Structure

**What works automatically:**

- Editing file contents in `.claude/` syncs to source
- Changes appear immediately without reinstall

**What requires manual steps:**

- Renaming files → Update kit.yaml + reinstall
- Moving files → Update kit.yaml + reinstall
- Deleting files → Update kit.yaml + reinstall

### Force Reinstall is Safe in Dev Mode

**Why reinstall?**

- Updates symlink targets after renames/moves
- Syncs manifest changes to installed state
- Cleans up orphaned symlinks

**Data safety:**

- Symlinks point to source files (no data loss)
- Source files are the source of truth
- Reinstall only recreates symlinks

## Kit Modification Checklist

Use this checklist before committing kit changes:

```markdown
## Kit Modification Checklist

- [ ] Source files renamed/moved/deleted as intended
- [ ] kit.yaml manifest updated with correct paths
- [ ] Cross-references in other artifacts updated
- [ ] Force-reinstalled kit: `erk kit install bundled:X --force`
- [ ] Ran validation: `erk check` shows ✅
- [ ] Tested artifact invocation works correctly
- [ ] Committed changes with clear description
```

## Reference: Correct Rename Pattern

See commit 3299f9c6 for a correctly executed rename operation:

**What was done:**

1. ✅ Renamed source files
2. ✅ Updated kit.yaml manifests
3. ✅ Updated cross-references
4. ✅ Recreated symlinks via reinstall
5. ✅ Updated dot-agent.toml (if applicable)

**Result:** Clean rename with no broken references

## Further Reading

- [DEVELOPING.md](../DEVELOPING.md) - Dev mode workflow
- [README.md](../README.md) - Kit structure and creation
- [GLOSSARY.md](GLOSSARY.md) - Terminology reference
