"""
Unit tests for prompt_engine.kubectl_exec.
Run: pytest tests/test_kubectl_exec.py -v
"""

import json
import os
import pytest
from unittest.mock import MagicMock, patch


# ── shared fixtures ────────────────────────────────────────────────────────────

VALID_KUBECTL_RESPONSE = {
    "commands": [
        "kubectl scale deployment jenkins --replicas=3 -n jenkins",
    ],
    "explanation": "Scales the Jenkins deployment in the jenkins namespace to 3 replicas.",
    "risk": "low",
    "warning": None,
}


def _make_mock_client(response_dict: dict):
    """Return a mock Anthropic client whose messages.create returns response_dict as JSON."""
    mock_client = MagicMock()
    mock_client.messages.create.return_value.content = [
        MagicMock(text=json.dumps(response_dict))
    ]
    return mock_client


# ── tests ──────────────────────────────────────────────────────────────────────

class TestTranslateToKubectl:
    """Tests for translate_to_kubectl()"""

    @patch("prompt_engine.kubectl_exec.anthropic.Anthropic")
    def test_translate_returns_commands(self, mock_anthropic_cls):
        """Happy path: translate_to_kubectl returns expected keys and command list."""
        mock_anthropic_cls.return_value = _make_mock_client(VALID_KUBECTL_RESPONSE)
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.kubectl_exec import translate_to_kubectl

        result = translate_to_kubectl("scale Jenkins to 3 replicas")

        assert isinstance(result["commands"], list)
        assert len(result["commands"]) == 1
        assert result["commands"][0].startswith("kubectl scale")
        assert result["risk"] == "low"
        assert result["warning"] is None
        assert "explanation" in result
        # dry_run flag should default to True and be stored in result
        assert result["dry_run"] is True

    @patch("prompt_engine.kubectl_exec.anthropic.Anthropic")
    def test_dry_run_does_not_execute(self, mock_anthropic_cls):
        """run_kubectl_prompt with execute=False must return results=None."""
        mock_anthropic_cls.return_value = _make_mock_client(VALID_KUBECTL_RESPONSE)
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.kubectl_exec import run_kubectl_prompt

        result = run_kubectl_prompt("scale Jenkins to 3 replicas", execute=False)

        # results should be None — no subprocess was spawned
        assert result["results"] is None
        # commands should still be populated from the translation
        assert len(result["commands"]) >= 1

    @patch("prompt_engine.kubectl_exec.anthropic.Anthropic")
    def test_invalid_json_raises(self, mock_anthropic_cls):
        """translate_to_kubectl raises ValueError when Claude returns non-JSON."""
        mock_client = MagicMock()
        mock_client.messages.create.return_value.content = [
            MagicMock(text="Sorry, I cannot help with that.")
        ]
        mock_anthropic_cls.return_value = mock_client
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.kubectl_exec import translate_to_kubectl

        with pytest.raises(ValueError, match="invalid JSON"):
            translate_to_kubectl("scale Jenkins to 3 replicas")


class TestExecuteKubectl:
    """Tests for execute_kubectl() safety gate."""

    def test_safety_blocks_delete_node(self):
        """execute_kubectl raises ValueError for 'kubectl delete node' commands."""
        from prompt_engine.kubectl_exec import execute_kubectl

        dangerous_commands = ["kubectl delete node ip-10-0-1-219"]

        with pytest.raises(ValueError, match="Execution blocked"):
            execute_kubectl(dangerous_commands)

    def test_safety_blocks_delete_cluster(self):
        """execute_kubectl raises ValueError for 'delete cluster' commands."""
        from prompt_engine.kubectl_exec import execute_kubectl

        with pytest.raises(ValueError, match="Execution blocked"):
            execute_kubectl(["eksctl delete cluster --name devops-poc"])

    def test_safety_blocks_destroy(self):
        """execute_kubectl raises ValueError for any command containing 'destroy'."""
        from prompt_engine.kubectl_exec import execute_kubectl

        with pytest.raises(ValueError, match="Execution blocked"):
            execute_kubectl(["terraform destroy -auto-approve"])

    def test_safety_blocks_drain_without_dry_run(self):
        """execute_kubectl raises ValueError for drain commands without --dry-run."""
        from prompt_engine.kubectl_exec import execute_kubectl

        with pytest.raises(ValueError, match="Execution blocked"):
            execute_kubectl(["kubectl drain ip-10-0-1-219 --ignore-daemonsets"])

    def test_safety_allows_drain_with_dry_run(self):
        """execute_kubectl does NOT block drain when --dry-run is present."""
        from prompt_engine.kubectl_exec import execute_kubectl

        # subprocess.run will fail because kubectl isn't in the test env,
        # but the safety gate must NOT raise — it should proceed to execution.
        try:
            execute_kubectl(["kubectl drain ip-10-0-1-219 --dry-run=client"])
        except ValueError as e:
            pytest.fail(f"Safety gate incorrectly blocked a --dry-run drain: {e}")
        except Exception:
            # subprocess failure is expected in a test environment — that's fine
            pass
