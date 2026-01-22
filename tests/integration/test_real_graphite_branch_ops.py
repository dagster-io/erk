"""Integration tests for RealGraphiteBranchOps.

Tests verify that RealGraphiteBranchOps correctly invokes gt CLI commands
with proper arguments. Since gt may not be installed in CI environments,
these tests mock subprocess.run to verify command structure.
"""

import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from erk_shared.gateway.graphite.branch_ops.real import RealGraphiteBranchOps
from tests.integration.test_helpers import mock_subprocess_run


def test_track_branch_calls_gt_track_correctly(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that track_branch calls gt track with correct arguments."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGraphiteBranchOps()
        ops.track_branch(tmp_path, "feature-branch", "main")

    assert len(called_with) == 1
    assert called_with[0] == ["gt", "track", "--branch", "feature-branch", "--parent", "main"]


def test_delete_branch_calls_gt_delete_with_force(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that delete_branch calls gt delete with -f flag."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGraphiteBranchOps()
        ops.delete_branch(tmp_path, "feature-branch")

    assert len(called_with) == 1
    assert called_with[0] == ["gt", "delete", "-f", "feature-branch"]


def test_submit_branch_calls_gt_submit_correctly(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that submit_branch calls gt submit with correct arguments."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGraphiteBranchOps()
        ops.submit_branch(tmp_path, "feature-branch", quiet=False)

    assert len(called_with) == 1
    assert called_with[0] == [
        "gt",
        "submit",
        "--branch",
        "feature-branch",
        "--no-edit",
        "--no-interactive",
    ]


def test_submit_branch_quiet_mode_passes_quiet_flag(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    """Test that submit_branch with quiet=True passes --quiet flag."""
    called_with: list[list[str]] = []

    def mock_run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
        called_with.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    with mock_subprocess_run(monkeypatch, mock_run):
        ops = RealGraphiteBranchOps()
        ops.submit_branch(tmp_path, "feature-branch", quiet=True)

    assert len(called_with) == 1
    assert called_with[0] == [
        "gt",
        "submit",
        "--branch",
        "feature-branch",
        "--no-edit",
        "--no-interactive",
        "--quiet",
    ]
