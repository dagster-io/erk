# Plan: Split Capabilities into Separate Documentation File

## Summary

Split the capabilities section from `docs/tutorials/installation.md` into a new file `docs/tutorials/advanced-configuration.md` for advanced installation administration.

## Files to Modify

1. **`docs/tutorials/installation.md`** — Remove capabilities content, add link to new file
2. **`docs/tutorials/advanced-configuration.md`** — New file with capabilities content
3. **`docs/tutorials/index.md`** — Add new file to Optional Enhancements section

## Content Split

**Keep in installation.md:**
- Install erk (lines 1-30)
- Verify Installation (lines 32-82)
- Initialize a Repository basics (lines 84-119: what project/user setup does)
- Quick Reference table
- Next Steps

**Move to advanced-configuration.md:**
- Capabilities section (lines 120-158): what they are, list command, tables of project/user capabilities, how to install
- Init flags section (lines 160-168)
- Init troubleshooting section (lines 169-173)

## Changes

### 1. Create `docs/tutorials/advanced-configuration.md`

New file with:
- Title: "Advanced Configuration"
- Brief intro explaining what capabilities are
- `erk init capability list` command
- Project capabilities table
- User capabilities table
- `erk init capability add` command
- Init flags section
- Troubleshooting section
- Link back to installation.md

### 2. Edit `docs/tutorials/installation.md`

- Remove lines 120-173 (capabilities through troubleshooting)
- Add brief mention of capabilities with link: "For optional capabilities (devrun, dignified-python, etc.), see [Advanced Configuration](advanced-configuration.md)."
- Keep Quick Reference and Next Steps

### 3. Edit `docs/tutorials/index.md`

Add to Optional Enhancements:
```markdown
- **[Advanced Configuration](advanced-configuration.md)** - Capabilities, init flags, and troubleshooting
```

## Verification

1. Check all internal links work
2. Review that installation.md still makes sense as standalone getting-started guide
3. Review that advanced-configuration.md is self-contained for users who need advanced config