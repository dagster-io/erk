"""Scratch space for inter-process file passing.

Provides a `.erk/scratch/` directory in the repository root for temporary files
that need to be readable by subagents without permission prompts.

Import from submodules:
- scratch: get_scratch_dir, write_scratch_file, cleanup_stale_scratch
"""
