"""
Tests for file path resolution - ensures protection works based on target path, not CWD.

The protection hook should check if a file is protected based on where the file
actually is, not based on the current working directory where the hook is executed.
"""
from tests.conftest import (
    create_block_file,
    is_blocked,
    make_edit_input,
    make_write_input,
    make_bash_input,
    run_hook,
)


class TestFilePathResolution:
    """Tests that protection is based on target file path, not current directory."""

    def test_absolute_path_protected_when_running_from_different_directory(
        self, test_dir, hooks_dir
    ):
        """
        Protection should work when using absolute paths and running from a
        completely different directory.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)
        target_file = protected_dir / "src" / "file.txt"
        target_file.parent.mkdir(parents=True)

        # Create a separate unprotected directory to run from
        unprotected_dir = test_dir / "unprotected_workspace"
        unprotected_dir.mkdir(parents=True)

        # Run hook from unprotected directory, targeting absolute path in protected dir
        input_json = make_edit_input(str(target_file))
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=unprotected_dir)

        assert is_blocked(stdout), (
            "Should block when targeting absolute path in protected directory, "
            "even when running from unprotected directory"
        )

    def test_absolute_path_allowed_when_running_from_protected_directory(
        self, test_dir, hooks_dir
    ):
        """
        Protection should NOT apply when using absolute paths to unprotected
        files, even when running from a protected directory.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)

        # Create a separate unprotected directory with a target file
        unprotected_dir = test_dir / "unprotected_workspace"
        target_file = unprotected_dir / "file.txt"
        target_file.parent.mkdir(parents=True)

        # Run hook from protected directory, targeting absolute path in unprotected dir
        input_json = make_edit_input(str(target_file))
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=protected_dir)

        assert not is_blocked(stdout), (
            "Should NOT block when targeting absolute path in unprotected directory, "
            "even when running from protected directory"
        )

    def test_relative_path_resolves_from_cwd_then_checks_protection(
        self, test_dir, hooks_dir
    ):
        """
        Relative paths should be resolved from CWD, then protection checked
        based on the resolved absolute path.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)
        (protected_dir / "src").mkdir(parents=True)

        # Run hook from protected directory with relative path
        input_json = make_edit_input("src/file.txt")
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=protected_dir)

        assert is_blocked(stdout), (
            "Relative path should resolve from CWD and be blocked when in protected dir"
        )

    def test_relative_path_unprotected_when_cwd_is_unprotected(
        self, test_dir, hooks_dir
    ):
        """
        Relative paths should be allowed when CWD is in an unprotected directory.
        """
        # Create unprotected directory (no .block file)
        unprotected_dir = test_dir / "unprotected_project"
        (unprotected_dir / "src").mkdir(parents=True)

        # Run hook from unprotected directory with relative path
        input_json = make_edit_input("src/file.txt")
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=unprotected_dir)

        assert not is_blocked(stdout), (
            "Relative path should be allowed when CWD is in unprotected directory"
        )

    def test_protection_in_subdirectory_of_protected_dir(
        self, test_dir, hooks_dir
    ):
        """
        Running from subdirectory of protected directory should still block.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)
        subdir = protected_dir / "src" / "deep" / "nested"
        subdir.mkdir(parents=True)

        # Run hook from subdirectory with relative path
        input_json = make_edit_input("file.txt")
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=subdir)

        assert is_blocked(stdout), (
            "Should block in subdirectory of protected directory"
        )

    def test_protection_with_root_absolute_path(
        self, test_dir, hooks_dir
    ):
        """
        Absolute paths starting from root should resolve correctly.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)
        target_file = protected_dir / "file.txt"

        # Different cwd entirely
        other_dir = test_dir / "other"
        other_dir.mkdir(parents=True)

        # Use full absolute path
        input_json = make_edit_input(str(target_file.absolute()))
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=other_dir)

        assert is_blocked(stdout), (
            "Absolute path to protected file should be blocked regardless of CWD"
        )

    def test_write_tool_respects_path_resolution(
        self, test_dir, hooks_dir
    ):
        """
        Write tool should also respect path resolution rules.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)
        target_file = protected_dir / "new_file.txt"

        # Run from different directory
        other_dir = test_dir / "other"
        other_dir.mkdir(parents=True)

        input_json = make_write_input(str(target_file))
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=other_dir)

        assert is_blocked(stdout), (
            "Write tool should be blocked when targeting protected path"
        )

    def test_bash_tool_respects_path_resolution(
        self, test_dir, hooks_dir
    ):
        """
        Bash tool should also respect path resolution rules.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)
        target_file = protected_dir / "file.txt"

        # Run from different directory
        other_dir = test_dir / "other"
        other_dir.mkdir(parents=True)

        input_json = make_bash_input(f"touch {target_file}")
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=other_dir)

        assert is_blocked(stdout), (
            "Bash tool should be blocked when targeting protected path"
        )

    def test_sibling_directories_isolated(
        self, test_dir, hooks_dir
    ):
        """
        Protection in one directory should not affect sibling directories.
        """
        # Create protected and unprotected sibling directories
        protected_dir = test_dir / "projects" / "protected"
        unprotected_dir = test_dir / "projects" / "unprotected"
        create_block_file(protected_dir)
        (protected_dir / "src").mkdir(parents=True)
        (unprotected_dir / "src").mkdir(parents=True)

        # Run from parent directory targeting unprotected sibling
        parent_dir = test_dir / "projects"
        input_json = make_edit_input(str(unprotected_dir / "src" / "file.txt"))
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=parent_dir)

        assert not is_blocked(stdout), (
            "Should NOT block files in unprotected sibling directory"
        )

        # Now target protected sibling
        input_json = make_edit_input(str(protected_dir / "src" / "file.txt"))
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=parent_dir)

        assert is_blocked(stdout), (
            "Should block files in protected sibling directory"
        )

    def test_deeply_nested_cwd_with_protection_at_ancestor(
        self, test_dir, hooks_dir
    ):
        """
        Protection at ancestor directory should apply to deeply nested CWD.
        """
        # Create protected directory with .block file
        protected_dir = test_dir / "protected_project"
        create_block_file(protected_dir)

        # Create deeply nested directory
        deeply_nested = protected_dir / "a" / "b" / "c" / "d" / "e"
        deeply_nested.mkdir(parents=True)

        # Run from deeply nested directory
        input_json = make_edit_input("file.txt")
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=deeply_nested)

        assert is_blocked(stdout), (
            "Ancestor .block file should protect deeply nested directories"
        )

    def test_mixed_absolute_and_relative_paths_in_bash(
        self, test_dir, hooks_dir
    ):
        """
        Bash commands with mixed absolute and relative paths should check each.
        """
        # Create protected directory
        protected_dir = test_dir / "protected"
        create_block_file(protected_dir)
        (protected_dir / "src").mkdir(parents=True)

        # Create unprotected directory
        unprotected_dir = test_dir / "unprotected"
        unprotected_dir.mkdir(parents=True)

        # Bash command targeting protected absolute path
        input_json = make_bash_input(f"cp {protected_dir}/src/file.txt ./local.txt")
        exit_code, stdout, stderr = run_hook(hooks_dir, input_json, cwd=unprotected_dir)

        # Should block because we're touching a file in protected_dir
        assert is_blocked(stdout), (
            "Should block bash command that touches protected absolute path"
        )
