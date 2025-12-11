"""Shell completion script generation operations."""

from erk_shared.gateways.completion.abc import Completion as Completion
from erk_shared.gateways.completion.fake import FakeCompletion as FakeCompletion
from erk_shared.gateways.completion.real import RealCompletion as RealCompletion
