---
completed_steps: 0
steps:
- completed: false
  text: '1. Remove import from src/erk/cli/commands/exec/group.py (line 73): from
    erk.cli.commands.exec.scripts.post_plan_comment import post_plan_comment'
- completed: false
  text: '2. Remove registration from src/erk/cli/commands/exec/group.py (line 150):
    exec_group.add_command(post_plan_comment, name="post-plan-comment")'
- completed: false
  text: '3. Delete script: src/erk/cli/commands/exec/scripts/post_plan_comment.py'
- completed: false
  text: 4. Remove create_plan_issue_block function from packages/erk-shared/src/erk_shared/github/metadata.py
- completed: false
  text: 5. Check and remove create_plan_issue_block from packages/erk-shared/src/erk_shared/github/metadata_blocks.py
    if present
- completed: false
  text: 6. Remove tests for create_plan_issue_block from tests/unit/gateways/github/test_metadata_blocks.py
- completed: false
  text: '7. Verify with pyright: uv run pyright src/erk/cli/commands/exec/'
- completed: false
  text: '8. Verify with pytest: uv run pytest tests/unit/cli/commands/exec/ -x'
- completed: false
  text: '9. Verify with pytest: uv run pytest tests/unit/gateways/github/test_metadata_blocks.py
    -x'
total_steps: 9
---

# Progress Tracking

- [ ] 1. Remove import from src/erk/cli/commands/exec/group.py (line 73): from erk.cli.commands.exec.scripts.post_plan_comment import post_plan_comment
- [ ] 2. Remove registration from src/erk/cli/commands/exec/group.py (line 150): exec_group.add_command(post_plan_comment, name="post-plan-comment")
- [ ] 3. Delete script: src/erk/cli/commands/exec/scripts/post_plan_comment.py
- [ ] 4. Remove create_plan_issue_block function from packages/erk-shared/src/erk_shared/github/metadata.py
- [ ] 5. Check and remove create_plan_issue_block from packages/erk-shared/src/erk_shared/github/metadata_blocks.py if present
- [ ] 6. Remove tests for create_plan_issue_block from tests/unit/gateways/github/test_metadata_blocks.py
- [ ] 7. Verify with pyright: uv run pyright src/erk/cli/commands/exec/
- [ ] 8. Verify with pytest: uv run pytest tests/unit/cli/commands/exec/ -x
- [ ] 9. Verify with pytest: uv run pytest tests/unit/gateways/github/test_metadata_blocks.py -x