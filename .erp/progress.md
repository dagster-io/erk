---
completed_steps: 0
total_steps: 12
---

# Progress Tracking

- [ ] 1. Client-side check in `erk submit` - fail before triggering workflow
- [ ] 2. Early CI check in setup job - fail fast with clear messaging
- [ ] 3. Better error at `gh pr ready` step - defense in depth
- [ ] 4. Detect branch name collisions with other issues
- [ ] 1. **Layer 1 first (client)** - Start with `erk submit` validation for better local UX
- [ ] 2. **Layer 2 second (workflow)** - Add setup job validation as defense in depth
- [ ] 3. **Layer 3 third (gh pr ready)** - Improve error handling as final safety net
- [ ] 1. Submit issue where PR is closed → should fail in setup
- [ ] 2. Submit issue where PR is merged → should fail in setup
- [ ] 3. Submit two issues with same derived branch name → should fail with collision error
- [ ] 1. **GitHub API approach**: Use `ctx.github` abstraction with a new `get_pr_for_branch()` method using GraphQL `closingIssuesReferences` instead of regex parsing PR body.
- [ ] 2. **Issue linkage extraction**: Use GitHub's official API (`closingIssuesReferences` GraphQL field) rather than regex parsing of PR body text.
