---
description: Run the post-init prompt hook for project setup
---

# /erk:post-init

Execute the project-specific post-init prompt hook to complete setup for a developer joining this project.

## Execution

Read `.erk/prompt-hooks/post-init.md` in the current repository.

If the file exists, execute its instructions. These may include:

- Installing additional dependencies
- Configuring environment variables
- Setting up local databases or services
- Running one-time setup scripts

If file does not exist, inform the user:

```
No post-init hook found at .erk/prompt-hooks/post-init.md
This is optional - create this file to provide setup instructions for new developers.
```
