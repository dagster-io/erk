# Fix: Re-submit release PR via Graphite

## Context

During the 0.9.4 release, the PR was created with `git push` + `gh pr create` instead of `erk pr submit`. This means Graphite doesn't track the PR, so `gt pr` fails. The RELEASING.md instructions are already correct — I just didn't follow them.

## Steps

1. Run `gt submit --no-interactive` to register the branch with Graphite and sync the existing PR
2. Verify `gt pr` opens the PR afterward

3. Update RELEASING.md Step 7 to add an emphatic warning against using `git push` + `gh pr create` instead of `erk pr submit`, explaining that raw git/gh commands bypass Graphite tracking
