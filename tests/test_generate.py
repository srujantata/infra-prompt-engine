"""
Unit tests for prompt_engine.generate.
Run: pytest tests/
"""

import json
import pytest
from unittest.mock import MagicMock, patch


VALID_TERRAFORM = {
    "main_tf": 'terraform { required_version = ">= 1.8" }',
    "variables_tf": 'variable "region" { default = "us-east-1" }',
    "outputs_tf": 'output "vpc_id" { value = module.vpc.vpc_id }',
}


class TestGenerateTerraform:
    """Tests for generate_terraform()"""

    @patch("prompt_engine.generate.anthropic.Anthropic")
    def test_returns_three_files(self, mock_anthropic_cls):
        """generate_terraform returns dict with main_tf, variables_tf, outputs_tf"""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [
            MagicMock(text=json.dumps(VALID_TERRAFORM))
        ]

        import os
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.generate import generate_terraform
        result = generate_terraform("Create a VPC")

        assert set(result.keys()) == {"main_tf", "variables_tf", "outputs_tf"}

    @patch("prompt_engine.generate.anthropic.Anthropic")
    def test_strips_markdown_fences(self, mock_anthropic_cls):
        """generate_terraform strips ```json fences if model adds them"""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        fenced = f"```json\n{json.dumps(VALID_TERRAFORM)}\n```"
        mock_client.messages.create.return_value.content = [MagicMock(text=fenced)]

        import os
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.generate import generate_terraform
        result = generate_terraform("Create a VPC")
        assert "main_tf" in result

    @patch("prompt_engine.generate.anthropic.Anthropic")
    def test_raises_on_invalid_json(self, mock_anthropic_cls):
        """generate_terraform raises ValueError on non-JSON response"""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        mock_client.messages.create.return_value.content = [MagicMock(text="not json")]

        import os
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.generate import generate_terraform
        with pytest.raises(ValueError, match="invalid JSON"):
            generate_terraform("Create a VPC")

    @patch("prompt_engine.generate.anthropic.Anthropic")
    def test_raises_on_missing_keys(self, mock_anthropic_cls):
        """generate_terraform raises ValueError if required keys missing"""
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        incomplete = json.dumps({"main_tf": "content"})
        mock_client.messages.create.return_value.content = [MagicMock(text=incomplete)]

        import os
        os.environ["ANTHROPIC_API_KEY"] = "test-key"

        from prompt_engine.generate import generate_terraform
        with pytest.raises(ValueError, match="missing required keys"):
            generate_terraform("Create a VPC")
