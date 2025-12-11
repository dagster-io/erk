"""Shell detection and tool availability operations."""

from erk_shared.gateways.shell.abc import Shell as Shell
from erk_shared.gateways.shell.abc import detect_shell_from_env as detect_shell_from_env
from erk_shared.gateways.shell.fake import FakeShell as FakeShell
from erk_shared.gateways.shell.real import RealShell as RealShell
