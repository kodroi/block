"""
Agent-specific permissions tests for the block plugin.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from tests.conftest import (
    create_block_file,
    is_blocked,
    make_edit_input,
)


def run_hook_with_transcript(
    hooks_dir: Path, input_json: str, transcript_path: str = ""
) -> tuple:
    """Run hook with optional transcript path."""
    if transcript_path:
        input_data = json.loads(input_json)
        input_data["transcript_path"] = transcript_path
        input_json = json.dumps(input_data)

    hook_script = hooks_dir / "protect_directories.py"
    result = subprocess.run(
        [sys.executable, str(hook_script)],
        input=input_json,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def create_transcript_with_agent(agent_type: str) -> str:
    """Create a mock transcript file with a Task invocation."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
        # Write a Task tool invocation line
        entry = {
            "message": {
                "content": [
                    {
                        "name": "Task",
                        "input": {"subagent_type": agent_type, "prompt": "test"},
                    }
                ]
            }
        }
        f.write(json.dumps(entry) + "\n")
        return f.name


class TestAgentSpecificPermissions:
    """Tests for agent-specific permissions."""

    def test_agent_config_allows_specific_agent_patterns(self, test_dir, hooks_dir):
        """Agent-specific allowed patterns should work."""
        project_dir = test_dir / "project"
        config = {
            "agents": {
                "tdd-test-writer": {"allowed": ["**/*.test.ts"]},
                "*": {"blocked": []},
            }
        }
        create_block_file(project_dir, json.dumps(config))

        # Create transcript for tdd-test-writer agent
        transcript_path = create_transcript_with_agent("tdd-test-writer")

        try:
            # Test file should be allowed for tdd-test-writer
            input_json = make_edit_input(str(project_dir / "src/component.test.ts"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert not is_blocked(stdout)

            # Non-test file should be blocked for tdd-test-writer
            input_json = make_edit_input(str(project_dir / "src/component.ts"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert is_blocked(stdout)
        finally:
            Path(transcript_path).unlink()

    def test_agent_config_blocks_specific_agent_patterns(self, test_dir, hooks_dir):
        """Agent-specific blocked patterns should work."""
        project_dir = test_dir / "project"
        config = {
            "agents": {
                "code-reviewer": {"blocked": ["**/*.secret"]},
                "*": {"blocked": []},
            }
        }
        create_block_file(project_dir, json.dumps(config))

        transcript_path = create_transcript_with_agent("code-reviewer")

        try:
            # Secret file should be blocked for code-reviewer
            input_json = make_edit_input(str(project_dir / "config.secret"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert is_blocked(stdout)

            # Regular file should be allowed for code-reviewer
            input_json = make_edit_input(str(project_dir / "config.json"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert not is_blocked(stdout)
        finally:
            Path(transcript_path).unlink()

    def test_agent_wildcard_fallback(self, test_dir, hooks_dir):
        """Wildcard (*) should be used as fallback for unknown agents."""
        project_dir = test_dir / "project"
        config = {
            "agents": {
                "specific-agent": {"allowed": ["docs/**"]},
                "*": {"blocked": ["*.secret"]},
            }
        }
        create_block_file(project_dir, json.dumps(config))

        # Use an agent not in the config
        transcript_path = create_transcript_with_agent("unknown-agent")

        try:
            # Secret file should be blocked (via wildcard)
            input_json = make_edit_input(str(project_dir / "api.secret"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert is_blocked(stdout)

            # Regular file should be allowed (via wildcard)
            input_json = make_edit_input(str(project_dir / "README.md"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert not is_blocked(stdout)
        finally:
            Path(transcript_path).unlink()

    def test_agent_empty_blocked_array_allows_all(self, test_dir, hooks_dir):
        """Empty blocked array should allow all files."""
        project_dir = test_dir / "project"
        config = {"agents": {"*": {"blocked": []}}}
        create_block_file(project_dir, json.dumps(config))

        transcript_path = create_transcript_with_agent("any-agent")

        try:
            # Any file should be allowed
            input_json = make_edit_input(str(project_dir / "any-file.txt"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert not is_blocked(stdout)
        finally:
            Path(transcript_path).unlink()

    def test_agent_no_matching_rule_blocks_all(self, test_dir, hooks_dir):
        """If no agent rule matches (no wildcard), block everything."""
        project_dir = test_dir / "project"
        config = {"agents": {"specific-agent-only": {"allowed": ["docs/**"]}}}
        create_block_file(project_dir, json.dumps(config))

        # Use a different agent that's not in the config
        transcript_path = create_transcript_with_agent("other-agent")

        try:
            # Should block because no matching rule
            input_json = make_edit_input(str(project_dir / "any-file.txt"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert is_blocked(stdout)
        finally:
            Path(transcript_path).unlink()

    def test_agent_config_with_guide(self, test_dir, hooks_dir):
        """Agent-specific guide should be used."""
        project_dir = test_dir / "project"
        config = {
            "agents": {
                "test-agent": {
                    "blocked": ["*.config"],
                    "guide": "Config files are managed by CI",
                }
            },
            "guide": "Global guide",
        }
        create_block_file(project_dir, json.dumps(config))

        transcript_path = create_transcript_with_agent("test-agent")

        try:
            input_json = make_edit_input(str(project_dir / "app.config"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert is_blocked(stdout)
            assert "Config files are managed by CI" in stdout
        finally:
            Path(transcript_path).unlink()

    def test_no_transcript_uses_traditional_mode(self, test_dir, hooks_dir):
        """Without transcript, traditional allowed/blocked mode should work."""
        project_dir = test_dir / "project"
        config = {"blocked": ["*.secret"], "guide": "Traditional mode"}
        create_block_file(project_dir, json.dumps(config))

        # No transcript path - should use traditional mode
        input_json = make_edit_input(str(project_dir / "api.secret"))
        _, stdout, _ = run_hook_with_transcript(hooks_dir, input_json, "")
        assert is_blocked(stdout)
        assert "Traditional mode" in stdout

    def test_agent_config_error_both_allowed_and_blocked(self, test_dir, hooks_dir):
        """Agent config with both allowed and blocked should error."""
        project_dir = test_dir / "project"
        config = {
            "agents": {
                "bad-agent": {
                    "allowed": ["docs/**"],
                    "blocked": ["*.secret"],
                }
            }
        }
        create_block_file(project_dir, json.dumps(config))

        transcript_path = create_transcript_with_agent("bad-agent")

        try:
            input_json = make_edit_input(str(project_dir / "file.txt"))
            _, stdout, _ = run_hook_with_transcript(
                hooks_dir, input_json, transcript_path
            )
            assert is_blocked(stdout)
            assert "cannot specify both allowed and blocked" in stdout
        finally:
            Path(transcript_path).unlink()
