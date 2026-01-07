"""Shell detection and tool availability operations."""

from erk_shared.gateway.shell.abc import Shell as Shell
from erk_shared.gateway.shell.abc import detect_shell_from_env as detect_shell_from_env
from erk_shared.gateway.shell.fake import FakeShell as FakeShell
from erk_shared.gateway.shell.fake import SpawnSubshellCall as SpawnSubshellCall
from erk_shared.gateway.shell.real import RealShell as RealShell
