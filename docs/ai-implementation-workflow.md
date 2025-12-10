# AI Implementation Workflow

Automated AI-driven development system using GitHub Actions, erk worktrees, and Claude Code.

## Overview

This system enables automated implementation of features from pre-created, enriched plan files. It leverages:

- **erk**: Git worktree manager for isolated development
- **dot-agent**: Claude Code CLI for executing implementation plans
- **GitHub Actions**: CI/CD for automated workflow execution

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Local Development                                          │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Create plan with /erk:persist-plan              │    │
│  │ 2. Review and commit plan file (*-plan.md)         │    │
│  │ 3. Push to repository or trigger manually          │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions Workflow                                    │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Discover and validate plan file                 │    │
│  │ 2. Setup AI tools (erk, dot-agent, Claude)         │    │
│  │ 3. Create worktree from plan                       │    │
│  │ 4. Execute /erk:implement-plan via dot-agent       │    │
│  │ 5. Run validation suite (tests, types, linting)    │    │
│  │ 6. Track token usage and costs                     │    │
│  │ 7. Create pull request with implementation         │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│  Review & Merge                                             │
│  ┌────────────────────────────────────────────────────┐    │
│  │ 1. Review generated PR                             │    │
│  │ 2. Validate implementation against plan            │    │
│  │ 3. Run additional tests if needed                  │    │
│  │ 4. Merge or request modifications                  │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Workflows

### Main Workflow (`ai-implement.yml`)

Full implementation with comprehensive validation.

**Triggers:**

- Manual: `workflow_dispatch` with plan file selection
- Automatic: Push commits containing `*-plan.md` files

**Features:**

- Complete validation suite (unit tests, integration tests, type checking, linting)
- Progress monitoring with real-time updates
- Automatic PR creation with detailed context
- Token usage tracking and cost estimation
- Error recovery and partial implementation handling

**Usage:**

```bash
# Via GitHub Actions UI
Actions → AI Implementation System → Run workflow
  → Select plan file
  → Choose validation level (full/quick/none)
  → Run

# Via CLI helper script
./scripts/ai-implementation-helper.sh trigger feature-name-plan.md

# Via gh CLI directly
gh workflow run ai-implement.yml -f plan-file=feature-name-plan.md -f validation-level=full
```

### Quick Workflow (`ai-implement-quick.yml`)

Fast implementation without validation for rapid prototyping.

**Triggers:**

- Manual only: `workflow_dispatch`

**Features:**

- Skips validation suite for faster execution
- Creates draft PR automatically
- Ideal for experiments and quick iterations

**Usage:**

```bash
# Via CLI helper script
./scripts/ai-implementation-helper.sh trigger-quick prototype-plan.md

# Via gh CLI
gh workflow run ai-implement-quick.yml -f plan-file=prototype-plan.md
```

## Getting Started

### Prerequisites

1. **Repository Setup:**
   - This workflow system must be committed to your repository
   - GitHub Actions must be enabled

2. **Secrets Configuration:**
   - Add `ANTHROPIC_API_KEY` to repository secrets
   - Settings → Secrets and variables → Actions → New repository secret

3. **Local Tools (for plan creation):**
   - Install erk: `uv tool install erk`
   - Install Claude Code: `npm install -g @anthropic-ai/claude-code`
   - Install erk kit: `dot-agent kit install erk`

### Creating a Plan

Plans are created locally using interactive Claude sessions:

```bash
# Start Claude Code session
claude

# In Claude conversation:
> I want to implement [feature description]
> [Discuss requirements, architecture, approach]
> /erk:persist-plan

# This creates an enriched plan file: [feature-name]-plan.md
```

**What makes a good plan:**

- Clear objective and context
- Implementation steps with success criteria
- Architectural insights and design decisions
- Known constraints and edge cases
- Related context linking steps to understanding

### Committing and Triggering

Once you have a plan file:

```bash
# Commit the plan
git add feature-name-plan.md
git commit -m "Add implementation plan for feature-name"
git push

# Option 1: Automatic trigger (if push trigger enabled)
# Workflow runs automatically on push

# Option 2: Manual trigger via helper script
./scripts/ai-implementation-helper.sh trigger feature-name-plan.md

# Option 3: Manual trigger via GitHub UI
# Navigate to Actions tab and select workflow
```

## Helper Scripts

### `ai-implementation-helper.sh`

Developer CLI tool for managing workflows.

**Commands:**

```bash
# List available plan files
./scripts/ai-implementation-helper.sh list

# Validate plan structure
./scripts/ai-implementation-helper.sh validate feature-name-plan.md

# Trigger full implementation
./scripts/ai-implementation-helper.sh trigger feature-name-plan.md

# Trigger quick implementation
./scripts/ai-implementation-helper.sh trigger-quick prototype-plan.md

# Check workflow status
./scripts/ai-implementation-helper.sh status
```

### `track-token-usage.sh`

Extract and report token usage from implementation logs.

**Usage:**

```bash
# Generate text report
./scripts/track-token-usage.sh implementation.log

# Generate JSON report
./scripts/track-token-usage.sh implementation.log json
```

## Plan File Structure

A valid plan file should contain:

**Required:**

- `enriched_by_persist_plan: true` (YAML front matter)
- `## Implementation Steps` or `## Implementation Phases`
- Clear, actionable step descriptions

**Recommended:**

- `## Objective` - What you're building and why
- `## Context & Understanding` - Architectural insights, API quirks, domain logic
- Success criteria for each step
- Related context references linking steps to understanding

**Example:**

```markdown
---
enriched_by_persist_plan: true
---

## Implementation Plan: Feature Name

### Objective

Clear description of what we're building...

### Context & Understanding

#### API/Tool Quirks

- Discovered behavior X
- Tool Y requires Z

#### Architectural Insights

- Design decision A because B
- Pattern C chosen over D

### Implementation Steps

1. **Step 1**: Description
   - Success: Criteria
   - Related Context: See API/Tool Quirks

2. **Step 2**: Description
   - Success: Criteria
```

## Monitoring and Artifacts

### Workflow Outputs

Each workflow run produces:

1. **GitHub Actions Summary**: Progress tracking, validation results
2. **Implementation Artifacts**: `.plan/` folder with progress tracking
3. **Token Usage Report**: Estimated costs for the implementation
4. **Implementation Log**: Full output from Claude Code execution

### Accessing Artifacts

```bash
# Via GitHub UI
Actions → Select workflow run → Artifacts section

# Via gh CLI
gh run list --workflow=ai-implement.yml
gh run view <run-id>
gh run download <run-id>
```

### Real-time Monitoring

```bash
# Watch latest run
gh run watch

# View logs
gh run view <run-id> --log

# Check status
./scripts/ai-implementation-helper.sh status
```

## Cost Management

Token usage and costs are tracked automatically:

**Viewing Costs:**

- Check workflow summary for cost estimates
- Download `token-usage.json` artifact for detailed breakdown
- Use `track-token-usage.sh` on implementation logs

**Pricing (Claude Sonnet 4.5):**

- Input: $3.00 per million tokens
- Output: $15.00 per million tokens

**Cost Control Tips:**

- Use quick mode for experiments (skip validation)
- Review plans before triggering to ensure clarity
- Monitor token usage trends across implementations

## Validation

The validation suite includes:

**Unit Tests:**

```bash
make test-unit
# or
uv run pytest tests/unit -v
```

**Integration Tests:**

```bash
make test-integration
# or
uv run pytest tests/integration -v
```

**Type Checking:**

```bash
make pyright
# or
uv run pyright
```

**Linting:**

```bash
make lint
# or
uv run ruff check .
```

**Validation Levels:**

- `full`: All checks (unit, integration, types, linting)
- `quick`: Unit tests and type checking only
- `none`: Skip validation (quick mode)

## Pull Request Workflow

Generated PRs include:

- Implementation summary from plan
- Validation results
- Token usage and cost estimates
- Review checklist
- Links to implementation artifacts

**PR States:**

- **Ready for review**: Implementation succeeded, validation passed
- **Draft**: Implementation completed with warnings or validation failed
- **Quick mode**: Always draft, requires manual testing

**Review Process:**

1. Check implementation against plan requirements
2. Review generated code for security issues
3. Verify test coverage
4. Run local tests if needed
5. Check validation results in workflow
6. Approve and merge, or request changes

## Troubleshooting

### Workflow Fails to Start

**Symptoms:** Workflow doesn't trigger after push or manual trigger

**Solutions:**

- Check `ANTHROPIC_API_KEY` is set in repository secrets
- Verify workflow files are present in `.github/workflows/`
- Check GitHub Actions is enabled for repository
- Review workflow run logs for specific errors

### Plan File Not Found

**Symptoms:** "Plan file not found" error

**Solutions:**

- Verify plan file exists in repository root
- Check file name matches pattern `*-plan.md`
- Ensure file is committed and pushed
- Use correct file name in workflow dispatch input

### Implementation Fails

**Symptoms:** Implementation completes with errors

**Solutions:**

- Review implementation log in artifacts
- Check plan structure is valid (`validate` command)
- Verify plan has clear, actionable steps
- Ensure success criteria are testable
- Check for missing dependencies or context

### Validation Failures

**Symptoms:** Tests or type checking fails

**Solutions:**

- Review validation results in workflow summary
- Download validation artifacts for detailed output
- Run tests locally to reproduce
- Update plan with additional context if needed
- Use quick mode to skip validation temporarily

### Token Tracking Unavailable

**Symptoms:** "Unable to extract token usage" message

**Solutions:**

- This is expected if log format changes
- Token tracking is informational, not critical
- Check implementation log manually for token counts
- Update `track-token-usage.sh` if needed

### Worktree Creation Fails

**Symptoms:** "Failed to create worktree" error

**Solutions:**

- Ensure erk is installed correctly
- Check git repository state is clean
- Verify plan file is valid
- Review erk logs for specific errors

## Advanced Usage

### Custom Validation Commands

Modify validation steps in `ai-implement.yml`:

```yaml
- name: Run custom validation
  run: |
    # Add your custom validation commands
    ./scripts/custom-check.sh
```

### Multiple Plan Files

Trigger implementations for multiple plans:

```bash
for plan in *-plan.md; do
  ./scripts/ai-implementation-helper.sh trigger "$plan"
  sleep 60  # Rate limiting
done
```

### Integration with CI/CD

Chain with existing workflows:

```yaml
# In your existing workflow
- name: Trigger AI implementation
  if: contains(github.event.head_commit.message, '[ai-implement]')
  run: |
    plan_file=$(git diff-tree --no-commit-id --name-only -r ${{ github.sha }} | grep -E '.*-plan\.md$')
    gh workflow run ai-implement.yml -f plan-file="$plan_file"
```

### Custom Cost Tracking

Modify pricing in `track-token-usage.sh`:

```bash
# Update pricing constants
INPUT_COST_PER_MTok=3.00
OUTPUT_COST_PER_MTok=15.00
```

## Security Considerations

1. **API Key Protection:**
   - Never commit `ANTHROPIC_API_KEY` to repository
   - Use GitHub Secrets for sensitive values
   - Rotate keys periodically

2. **Code Review:**
   - Always review generated code before merging
   - Check for security vulnerabilities
   - Validate against plan requirements
   - Test thoroughly

3. **Branch Protection:**
   - Enable branch protection on main/master
   - Require PR reviews before merging
   - Enforce status checks

4. **Access Control:**
   - Limit who can trigger workflows
   - Use CODEOWNERS for PR reviews
   - Monitor workflow runs

## Best Practices

1. **Plan Quality:**
   - Invest time in creating clear, detailed plans
   - Include architectural context and constraints
   - Reference related code and patterns
   - Define clear success criteria

2. **Iterative Development:**
   - Start with quick mode for experiments
   - Use full mode for production features
   - Iterate on plans based on results

3. **Cost Awareness:**
   - Review plans before triggering
   - Monitor token usage trends
   - Use quick mode when appropriate
   - Consolidate related changes

4. **Testing:**
   - Ensure test coverage for generated code
   - Run local tests before merging
   - Add integration tests for complex features

5. **Documentation:**
   - Document generated features
   - Update architectural docs
   - Maintain plan history

## Limitations

1. **Plan Dependency:**
   - Quality of implementation depends on plan quality
   - Requires clear, actionable steps
   - Context-heavy plans may be expensive

2. **Token Limits:**
   - Very large implementations may hit token limits
   - Break into smaller plans if needed

3. **Validation Coverage:**
   - Automated validation is not exhaustive
   - Manual review still required
   - Security checks are basic

4. **Cost:**
   - API usage can be expensive for large plans
   - Monitor and manage token usage
   - Use quick mode judiciously

## Support and Feedback

For issues or questions:

1. Check troubleshooting section above
2. Review workflow logs and artifacts
3. Validate plan structure
4. Test components locally

## Related Documentation

- [erk Documentation](https://github.com/user/erk) - Git worktree manager
- [Claude Code Documentation](https://docs.claude.com/claude-code) - AI coding assistant
- [GitHub Actions Documentation](https://docs.github.com/actions) - CI/CD workflows

---

**Last Updated:** 2025-01-19
