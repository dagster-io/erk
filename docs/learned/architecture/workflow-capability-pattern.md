---
title: Workflow Capability Pattern
read_when:
  - creating GitHub workflow capabilities
  - adding CI review workflows
---

# Workflow Capability Pattern

Pattern for capabilities that install GitHub Actions workflows with prompts.

## Structure

A workflow capability typically installs:

1. `.github/workflows/<name>.yml` - The workflow file
2. `.github/prompts/<name>.md` - The prompt file
3. Optional: shared actions (e.g., setup-claude-code)

## Reference Implementation

`DignifiedReviewCapability` in `src/erk/core/capabilities/dignified_review.py`:

```python
class DignifiedReviewCapability(Capability):
    @property
    def name(self) -> str:
        return "dignified-review"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(
                path=".github/workflows/dignified-python-review.yml",
                artifact_type="file",
            ),
            CapabilityArtifact(
                path=".github/prompts/dignified-python-review.md",
                artifact_type="file",
            ),
        ]

    def install(self, repo_root: Path | None) -> CapabilityResult:
        from erk.artifacts.sync import get_bundled_github_dir
        bundled_github_dir = get_bundled_github_dir()

        # Copy workflow
        shutil.copy2(
            bundled_github_dir / "workflows" / "dignified-python-review.yml",
            repo_root / ".github" / "workflows" / "dignified-python-review.yml"
        )

        # Copy prompt
        shutil.copy2(
            bundled_github_dir / "prompts" / "dignified-python-review.md",
            repo_root / ".github" / "prompts" / "dignified-python-review.md"
        )

        return CapabilityResult(success=True, message="Installed")
```

## Dependencies Pattern

If the workflow depends on shared actions (like setup-claude-code):

**Option 1: Require dependency** (preflight check)

```python
def preflight(self, repo_root):
    if not (repo_root / ".github/actions/setup-claude-code").exists():
        return CapabilityResult(
            success=False,
            message="Requires erk-impl-workflow capability"
        )
    return CapabilityResult(success=True, message="")
```

**Option 2: Auto-install dependency** (self-contained)

```python
def install(self, repo_root):
    # Install action if missing
    action_dst = repo_root / ".github/actions/setup-claude-code"
    if not action_dst.exists():
        self._copy_directory(
            bundled_github_dir / "actions/setup-claude-code",
            action_dst
        )
    # ... install workflow and prompt
```

## Checklist for New Workflow Capabilities

- [ ] Create capability class in `src/erk/core/capabilities/`
- [ ] Workflow file exists in `.github/workflows/`
- [ ] Prompt file exists in `.github/prompts/`
- [ ] Register in `registry.py`
- [ ] Add tests for is_installed, install
- [ ] Document any dependencies
