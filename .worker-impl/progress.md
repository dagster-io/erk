---
completed_steps: 0
steps:
- completed: false
  text: 1. Use the symlink's parent directory for relative path resolution
- completed: false
  text: 2. Do NOT follow the symlink to get the target's parent
- completed: false
  text: 3. After resolving the relative path, it's OK to follow symlinks on the TARGET
    file
- completed: false
  text: 1. `source_file.parent` gives the symlink's directory, not target's
- completed: false
  text: 2. Use `os.path.normpath()` to resolve `..` components without following symlinks
- completed: false
  text: 3. The final `.exists()` check CAN follow symlinks (for the target file)
total_steps: 6
---

# Progress Tracking

- [ ] 1. Use the symlink's parent directory for relative path resolution
- [ ] 2. Do NOT follow the symlink to get the target's parent
- [ ] 3. After resolving the relative path, it's OK to follow symlinks on the TARGET file
- [ ] 1. `source_file.parent` gives the symlink's directory, not target's
- [ ] 2. Use `os.path.normpath()` to resolve `..` components without following symlinks
- [ ] 3. The final `.exists()` check CAN follow symlinks (for the target file)