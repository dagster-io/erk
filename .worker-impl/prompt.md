 (erk) ➜  erk-slot-21 git:(planned/plan-add-erk-cc-usage-f-02-22-0606) erk down --delete-current -f
Warning: Pull request for branch 'planned/plan-add-erk-cc-usage-f-02-22-0606' is still open.
https://github.com/dagster-io/erk/pull/7824
Delete branch anyway? [y/N]: y
Close the PR? [Y/n]: y
✓ Closed PR #7824

To activate and delete branch planned/plan-add-erk-cc-usage-f-02-22-0606:
  source /Users/schrockn/code/erk/.erk/bin/activate.sh && erk br delete planned/plan-add-erk-cc-usage-f-02-22-0606  (copied to clipboard)
(erk) ➜  erk-slot-21 git:(planned/plan-add-erk-cc-usage-f-02-22-0606) source /Users/schrockn/code/erk/.erk/bin/activate.sh && erk br delete planned/plan-add-erk-cc-usage-f-02-22-0606
-> cd /Users/schrockn/code/erk
direnv: loading ~/code/erk/.envrc
direnv: loading ~/code/erk/.erk/bin/activate.sh
-> cd /Users/schrockn/code/erk
-> Activating venv: /Users/schrockn/code/erk/.venv (3.13.1)
Activated: /Users/schrockn/code/erk
direnv: export +VIRTUAL_ENV +VIRTUAL_ENV_PROMPT ~PATH
-> Activating venv: /Users/schrockn/code/erk/.venv (3.13.1)
Activated: /Users/schrockn/code/erk
📋 Planning to perform the following operations:
  1. 🔓 Unassign slot: erk-slot-21 (keep worktree for reuse)
  2. 🌳 Delete branch: planned/plan-add-erk-cc-usage-f-02-22-0606

Proceed with these operations? [Y/n]:
✓ Unassigned slot erk-slot-21
✅ Deleted branch: planned/plan-add-erk-cc-usage-f-02-22-0606
(erk) ➜  erk git:(master)

make -f actually skip these prompts

