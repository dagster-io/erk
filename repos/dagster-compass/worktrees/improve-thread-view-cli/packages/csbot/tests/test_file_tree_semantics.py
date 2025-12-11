"""
Test to verify that GitCommitFileTree and FilesystemFileTree have identical semantics.

This test creates a real git repository with various file structures and verifies
that both tree implementations behave identically for all operations.
"""

import glob
import tempfile
from pathlib import Path

import pygit2
import pytest

from csbot.local_context_store.git.file_tree import FilesystemFileTree, GitCommitFileTree


class TestFileTreeSemantics:
    """Test semantic equivalence between GitCommitFileTree and FilesystemFileTree."""

    @pytest.fixture
    def git_repo_with_content(self):
        """Create a real git repository with various content types for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_path = Path(temp_dir)

            # Initialize git repository
            repo = pygit2.init_repository(str(repo_path), bare=False)

            # Create various file structures to test
            test_files = {
                "simple.txt": "Hello, World!",
                "nested/dir/file.md": "# Nested File\n\nContent in nested directory.",
                "docs/dataset1.yaml": "name: dataset1\ntype: table\nschema_hash: abc123",
                "docs/dataset2.yaml": "name: dataset2\ntype: view\nschema_hash: def456",
                "context/project.yaml": "project_name: test\ndescription: Test project",
                "context/nested/deep/context.yaml": "topic: deep\ncontent: deeply nested",
                "system_prompt.md": "You are a helpful assistant.",
                "cronjobs/job1.yaml": "schedule: '0 0 * * *'\ncommand: backup",
                "cronjobs/job2.yaml": "schedule: '0 12 * * *'\ncommand: cleanup",
                "empty_dir/.gitkeep": "",  # Empty directory marker
                "unicode_文件.txt": "Unicode filename test 🚀",
                "special-chars_file[1].txt": "File with special characters",
            }

            # Write all test files
            for file_path, content in test_files.items():
                full_path = repo_path / file_path
                full_path.parent.mkdir(parents=True, exist_ok=True)
                full_path.write_text(content, encoding="utf-8")

            # Stage all files
            index = repo.index
            for file_path in test_files.keys():
                index.add(file_path)
            index.write()

            # Create initial commit
            signature = pygit2.Signature("Test User", "test@example.com")
            tree_id = index.write_tree()
            repo.create_commit(
                "HEAD",  # reference
                signature,  # author
                signature,  # committer
                "Initial commit with test files",  # message
                tree_id,  # tree
                [],  # parents
            )

            # Get the committed tree object
            commit = repo[repo.head.target]
            tree = commit.peel(pygit2.Tree)

            yield {
                "repo_path": repo_path,
                "repo": repo,
                "tree": tree,
                "test_files": test_files,
            }

    def test_read_text_equivalence(self, git_repo_with_content):
        """Test that read_text returns identical content for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test all files
        for file_path, expected_content in data["test_files"].items():
            if file_path.endswith(".gitkeep"):
                continue  # Skip empty files

            git_content = git_wrapper.read_text(file_path)
            fs_content = fs_wrapper.read_text(file_path)

            assert git_content == fs_content == expected_content, (
                f"Content mismatch for {file_path}\n"
                f"Git: {repr(git_content)}\n"
                f"FS:  {repr(fs_content)}\n"
                f"Expected: {repr(expected_content)}"
            )

    def test_exists_equivalence(self, git_repo_with_content):
        """Test that exists returns identical results for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test existing files
        for file_path in data["test_files"].keys():
            git_exists = git_wrapper.exists(file_path)
            fs_exists = fs_wrapper.exists(file_path)

            assert git_exists == fs_exists is True, (
                f"Exists check failed for {file_path}: git={git_exists}, fs={fs_exists}"
            )

        # Test non-existing files
        non_existing_paths = [
            "nonexistent.txt",
            "nested/missing.md",
            "docs/missing_dataset.yaml",
            "completely/missing/path/file.txt",
        ]

        for path in non_existing_paths:
            git_exists = git_wrapper.exists(path)
            fs_exists = fs_wrapper.exists(path)

            assert git_exists == fs_exists is False, (
                f"Exists check failed for non-existing {path}: git={git_exists}, fs={fs_exists}"
            )

    def test_is_file_equivalence(self, git_repo_with_content):
        """Test that is_file returns identical results for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test files
        test_files = [
            "simple.txt",
            "nested/dir/file.md",
            "docs/dataset1.yaml",
            "context/project.yaml",
        ]

        for file_path in test_files:
            git_is_file = git_wrapper.is_file(file_path)
            fs_is_file = fs_wrapper.is_file(file_path)

            assert git_is_file == fs_is_file is True, (
                f"is_file check failed for {file_path}: git={git_is_file}, fs={fs_is_file}"
            )

        # Test directories
        test_dirs = ["nested", "nested/dir", "docs", "context", "cronjobs"]

        for dir_path in test_dirs:
            git_is_file = git_wrapper.is_file(dir_path)
            fs_is_file = fs_wrapper.is_file(dir_path)

            assert git_is_file == fs_is_file is False, (
                f"is_file check failed for directory {dir_path}: git={git_is_file}, fs={fs_is_file}"
            )

    def test_is_dir_equivalence(self, git_repo_with_content):
        """Test that is_dir returns identical results for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test directories
        test_dirs = ["nested", "nested/dir", "docs", "context", "context/nested", "cronjobs"]

        for dir_path in test_dirs:
            git_is_dir = git_wrapper.is_dir(dir_path)
            fs_is_dir = fs_wrapper.is_dir(dir_path)

            assert git_is_dir == fs_is_dir is True, (
                f"is_dir check failed for {dir_path}: git={git_is_dir}, fs={fs_is_dir}"
            )

        # Test files
        test_files = ["simple.txt", "nested/dir/file.md", "docs/dataset1.yaml"]

        for file_path in test_files:
            git_is_dir = git_wrapper.is_dir(file_path)
            fs_is_dir = fs_wrapper.is_dir(file_path)

            assert git_is_dir == fs_is_dir is False, (
                f"is_dir check failed for file {file_path}: git={git_is_dir}, fs={fs_is_dir}"
            )

    def test_listdir_equivalence(self, git_repo_with_content):
        """Test that listdir returns identical results for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test root directory
        git_root_list = sorted(git_wrapper.listdir(""))
        fs_root_list = sorted(fs_wrapper.listdir(""))

        assert git_root_list == fs_root_list, (
            f"Root listdir mismatch:\nGit: {git_root_list}\nFS:  {fs_root_list}"
        )

        # Test subdirectories
        test_dirs = ["docs", "context", "cronjobs", "nested", "nested/dir"]

        for dir_path in test_dirs:
            git_list = sorted(git_wrapper.listdir(dir_path))
            fs_list = sorted(fs_wrapper.listdir(dir_path))

            assert git_list == fs_list, (
                f"listdir mismatch for {dir_path}:\nGit: {git_list}\nFS:  {fs_list}"
            )

    def test_glob_equivalence(self, git_repo_with_content):
        """Test that glob returns identical results for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test various glob patterns
        test_patterns = [
            ("docs", "*.yaml"),
            ("cronjobs", "*.yaml"),
            ("", "*.txt"),
            ("", "*.md"),
            ("context", "*"),
            ("nested/dir", "*"),
        ]

        for directory, pattern in test_patterns:
            git_results = sorted(list(git_wrapper.glob(directory, pattern)))
            fs_results = sorted(list(fs_wrapper.glob(directory, pattern)))

            assert git_results == fs_results, (
                f"glob mismatch for '{directory}' pattern '{pattern}':\n"
                f"Git: {git_results}\nFS:  {fs_results}"
            )

    def test_recursive_glob_equivalence(self, git_repo_with_content):
        """Test that recursive_glob returns identical results for both implementations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test recursive patterns
        test_patterns = [
            "*.yaml",
            "*.txt",
            "*.md",
            "**/file.md",
            "**/project.yaml",
            "context/**/*.yaml",
        ]

        for pattern in test_patterns:
            git_results = sorted(list(git_wrapper.recursive_glob(pattern)))
            fs_results = sorted(list(fs_wrapper.recursive_glob(pattern)))

            assert git_results == fs_results, (
                f"recursive_glob mismatch for pattern '{pattern}':\n"
                f"Git: {git_results}\nFS:  {fs_results}"
            )

    def test_error_conditions_equivalence(self, git_repo_with_content):
        """Test that both implementations raise identical errors for invalid operations."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test reading non-existent file
        with pytest.raises(FileNotFoundError):
            git_wrapper.read_text("nonexistent.txt")

        with pytest.raises(FileNotFoundError):
            fs_wrapper.read_text("nonexistent.txt")

        # Test reading directory as file
        with pytest.raises(IsADirectoryError):
            git_wrapper.read_text("docs")

        with pytest.raises(IsADirectoryError):
            fs_wrapper.read_text("docs")

        # Test listing non-existent directory
        with pytest.raises(FileNotFoundError):
            git_wrapper.listdir("nonexistent_dir")

        with pytest.raises(FileNotFoundError):
            fs_wrapper.listdir("nonexistent_dir")

        # Test listing file as directory
        with pytest.raises(NotADirectoryError):
            git_wrapper.listdir("simple.txt")

        with pytest.raises(NotADirectoryError):
            fs_wrapper.listdir("simple.txt")

    def test_unicode_and_special_chars_equivalence(self, git_repo_with_content):
        """Test that both implementations handle unicode and special characters identically."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        # Test unicode filename
        unicode_file = "unicode_文件.txt"
        git_content = git_wrapper.read_text(unicode_file)
        fs_content = fs_wrapper.read_text(unicode_file)

        assert git_content == fs_content, (
            f"Unicode file content mismatch:\nGit: {repr(git_content)}\nFS:  {repr(fs_content)}"
        )

        # Test special characters filename
        special_file = "special-chars_file[1].txt"
        git_content = git_wrapper.read_text(special_file)
        fs_content = fs_wrapper.read_text(special_file)

        assert git_content == fs_content, (
            f"Special chars file content mismatch:\n"
            f"Git: {repr(git_content)}\nFS:  {repr(fs_content)}"
        )

    def test_comprehensive_file_tree_equivalence(self, git_repo_with_content):
        """Comprehensive test that verifies the entire file tree structure is identical."""
        data = git_repo_with_content
        git_wrapper = GitCommitFileTree(data["tree"], None)
        fs_wrapper = FilesystemFileTree(data["repo_path"])

        def get_tree_structure(wrapper, path=""):
            """Recursively get complete tree structure."""
            structure = {}

            if not wrapper.exists(path):
                return structure

            if wrapper.is_file(path):
                structure["type"] = "file"
                try:
                    structure["content"] = wrapper.read_text(path)
                except UnicodeDecodeError:
                    # Handle binary files by marking them as binary
                    structure["content"] = "<BINARY_FILE>"
                return structure

            if wrapper.is_dir(path):
                structure["type"] = "directory"
                structure["children"] = {}

                for item in wrapper.listdir(path):
                    child_path = f"{path}/{item}" if path else item
                    structure["children"][item] = get_tree_structure(wrapper, child_path)

                return structure

            return structure

        # Get complete tree structures
        git_structure = get_tree_structure(git_wrapper)
        fs_structure = get_tree_structure(fs_wrapper)

        assert git_structure == fs_structure, (
            "Complete tree structures don't match between git and filesystem implementations"
        )

    def test_recursive_glob_context_pattern_equivalence(self, git_repo_with_content):
        """Test that recursive_glob context pattern behaves identically and correctly excludes nested bots."""
        # Add context files to the existing repo
        data = git_repo_with_content
        repo_path = data["repo_path"]
        repo = data["repo"]

        # Create org context files
        org_context_dir = repo_path / "context" / "general"
        org_context_dir.mkdir(parents=True)
        (org_context_dir / "org_context.yaml").write_text(
            "topic: org\nincorrect_understanding: wrong\ncorrect_understanding: right\nsearch_keywords: org"
        )

        # Create nested bot context that should be included in org search
        nested_bot_dir = repo_path / "context" / "multi_channel_bots" / "channel1" / "context"
        nested_bot_dir.mkdir(parents=True)
        (nested_bot_dir / "bot_context.yaml").write_text(
            "topic: bot\nincorrect_understanding: wrong\ncorrect_understanding: right\nsearch_keywords: bot"
        )

        # Create root-level bot context (should be separate from org context)
        root_bot_dir = repo_path / "multi_channel_bots" / "test_channel" / "context"
        root_bot_dir.mkdir(parents=True)
        (root_bot_dir / "root_bot_context.yaml").write_text(
            "topic: root bot\nincorrect_understanding: wrong\ncorrect_understanding: right\nsearch_keywords: root, bot"
        )

        glob_result = glob.glob("context/**/*.yaml", recursive=True, root_dir=repo_path)
        expected_result = [
            "context/project.yaml",
            "context/general/org_context.yaml",
            "context/nested/deep/context.yaml",
            "context/multi_channel_bots/channel1/context/bot_context.yaml",
        ]
        expected_result.sort()
        glob_result.sort()
        assert glob_result == expected_result

        # Commit the new files
        index = repo.index
        index.add_all()
        index.write()

        signature = pygit2.Signature("Test User", "test@example.com")
        tree_id = index.write_tree()
        repo.create_commit(
            "HEAD",
            signature,
            signature,
            "Add context files for testing",
            tree_id,
            [repo.head.target],
        )

        # Get updated tree
        commit = repo[repo.head.target]
        tree = commit.peel(pygit2.Tree)

        git_wrapper = GitCommitFileTree(tree, None)
        fs_wrapper = FilesystemFileTree(repo_path)

        # Test the problematic pattern: context/**/*.yaml
        git_context_files = sorted(list(git_wrapper.recursive_glob("context/**/*.yaml")))
        fs_context_files = sorted(list(fs_wrapper.recursive_glob("context/**/*.yaml")))

        git_context_files.sort()
        fs_context_files.sort()

        assert git_context_files == fs_context_files, (
            f"Context glob mismatch between implementations:\n"
            f"Git: {git_context_files}\n"
            f"FS:  {fs_context_files}"
        )

        assert git_context_files == expected_result, "git did not match glob.glob result"
        assert fs_context_files == expected_result, "fs did not match glob.glob result"

        org_files = [f for f in git_context_files if "context/general/" in f]
        nested_bot_files = [f for f in git_context_files if "context/multi_channel_bots/" in f]
        root_bot_files = [f for f in git_context_files if "multi_channel_bots/test_channel/" in f]

        assert len(org_files) == 1, f"Should find org context, got: {git_context_files}"
        assert len(nested_bot_files) == 1, (
            f"Should find nested bot context, got: {git_context_files}"
        )
        assert len(root_bot_files) == 0, (
            f"Should not find root bot context, got: {git_context_files}"
        )
