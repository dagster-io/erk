---
description: Rename current CMUX workspace to the current git branch name
---

Run the following two commands sequentially:

1. Get the current git branch name:

   ```bash
   git branch --show-current
   ```

2. Rename the current CMUX workspace to that branch name:
   ```bash
   cmux rename-workspace "<branch>"
   ```

Tell the user the workspace was renamed to the branch name.
