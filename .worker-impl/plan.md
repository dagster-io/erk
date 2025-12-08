# Plan: Enhance GitHub API Field Mapping Documentation

## Objective

Add missing field mappings and code examples to `docs/agent/architecture/github-interface-patterns.md`. This is a **replan** of issue #2521 which was partially implemented via different file structure.

## Source Information

- Original Plan: Issue #2521
- Original Session: `d1d34bd5-e421-4b11-98dc-b3ddb353aa9a`
- Replan Session: `fd29b7a3-0a22-44df-91d8-755fd1254254`

## What Changed Since Original Plan

The original plan proposed creating `docs/agent/github/api-field-mapping.md`. Instead, the documentation evolved into `docs/agent/architecture/github-interface-patterns.md` which already covers:
- PR state mapping (REST → Internal)
- Mergeability mapping
- Draft status mapping
- Fork detection (covers cross-repository)

## Remaining Gaps

### Gap 1: Branch Reference Field Mapping

**Location:** `docs/agent/architecture/github-interface-patterns.md`
**Action:** Add new section after "Fork Detection" (around line 77)

The mapping from GraphQL field names to REST API paths to internal field names is not documented:

| GraphQL | REST | Internal |
|---------|------|----------|
| `baseRefName` | `base.ref` | `base_ref_name` |
| `headRefName` | `head.ref` | `head_ref_name` |

### Gap 2: Merge State Status Mapping

**Location:** `docs/agent/architecture/github-interface-patterns.md`
**Action:** Add after Mergeability section (around line 65)

GraphQL `mergeStateStatus` maps to REST `mergeable_state` with case transformation:

| REST `mergeable_state` | Internal `merge_state_status` |
|------------------------|-------------------------------|
| `"clean"` | `"CLEAN"` |
| `"blocked"` | `"BLOCKED"` |
| `"behind"` | `"BEHIND"` |
| `"unstable"` | `"UNSTABLE"` |
| `null` | `"UNKNOWN"` |

### Gap 3: Code Examples for Normalization

**Location:** `docs/agent/architecture/github-interface-patterns.md`
**Action:** Add Python code examples showing the actual normalization logic from `real.py`

The existing documentation has tables but lacks the code patterns. Adding examples would make the mapping actionable:

```python
# PR State normalization (from real.py)
if data.get("merged"):
    state = "MERGED"
else:
    state = data["state"].upper()

# Branch refs (nested in REST)
base_ref_name = data["base"]["ref"]
head_ref_name = data["head"]["ref"]

# Cross-repository detection
head_repo = data["head"].get("repo")
is_cross_repository = head_repo["fork"] if head_repo else False
```

## Implementation Steps

1. Read current `docs/agent/architecture/github-interface-patterns.md`
2. Add "Branch Reference Fields" section after "Fork Detection" (line ~77)
3. Add "Merge State Status" section after "Mergeability" (line ~65)
4. Add "Normalization Code Examples" section before "Related Topics"
5. Run `dot-agent docs sync` to update generated files
6. Run `make fast-ci` to verify

## Scope Reduction Note

This is a smaller plan than the original because most of the core documentation now exists. The remaining work is incremental enhancement rather than creating new documentation structure.

## Related Documentation

- Skills to load: None required (documentation-only change)
- Docs: `docs/agent/architecture/github-interface-patterns.md` (target file)