from unittest.mock import MagicMock, patch

import pytest
from arcade_tdk import ToolContext, ToolSecretItem
from arcade_tdk.errors import ToolExecutionError

import arcade_e2b.tools.create_chart
import arcade_e2b.tools.run_code
from arcade_e2b.enums import E2BSupportedLanguage


@pytest.fixture
def mock_run_code_sandbox():
    with patch("arcade_e2b.tools.run_code.Sandbox") as mock:
        yield mock.return_value.__enter__.return_value


@pytest.fixture
def mock_create_chart_sandbox():
    with patch("arcade_e2b.tools.create_chart.Sandbox") as mock:
        yield mock.return_value.__enter__.return_value


@pytest.fixture
def mock_context():
    return ToolContext(secrets=[ToolSecretItem(key="e2b_api_key", value="fake_api_key")])


def test_run_code_success(mock_run_code_sandbox, mock_context):
    mock_execution = MagicMock()
    mock_execution.to_json.return_value = '{"result": "success"}'
    mock_run_code_sandbox.run_code.return_value = mock_execution

    result = arcade_e2b.tools.run_code(
        mock_context, "print('Hello, World!')", E2BSupportedLanguage.PYTHON
    )
    assert result == '{"result": "success"}'


def test_run_code_error(mock_run_code_sandbox, mock_context):
    mock_execution = MagicMock()
    mock_execution.to_json.side_effect = ToolExecutionError("Execution failed")
    mock_run_code_sandbox.run_code.return_value = mock_execution

    with pytest.raises(ToolExecutionError, match="Execution failed"):
        arcade_e2b.tools.run_code(
            mock_context, "print('Hello, World!')", E2BSupportedLanguage.PYTHON
        )


def test_create_static_matplotlib_chart_success(mock_create_chart_sandbox, mock_context):
    mock_execution = MagicMock()
    mock_execution.results = [MagicMock(png="base64encodedimage")]
    mock_execution.logs.to_json.return_value = '{"logs": "log data"}'
    mock_execution.error = None
    mock_create_chart_sandbox.run_code.return_value = mock_execution

    result = arcade_e2b.tools.create_chart.create_static_matplotlib_chart(
        mock_context, "import matplotlib.pyplot as plt"
    )
    assert result == {
        "base64_image": "base64encodedimage",
        "logs": '{"logs": "log data"}',
        "error": None,
    }


def test_create_static_matplotlib_chart_error(mock_create_chart_sandbox, mock_context):
    mock_execution = MagicMock()
    mock_execution.results = []
    mock_execution.logs.to_json.return_value = '{"logs": "log data"}'
    mock_execution.error.to_json.return_value = '{"error": "some error"}'
    mock_create_chart_sandbox.run_code.return_value = mock_execution

    result = arcade_e2b.tools.create_chart.create_static_matplotlib_chart(
        mock_context, "import matplotlib.pyplot as plt"
    )
    assert result == {
        "base64_image": None,
        "logs": '{"logs": "log data"}',
        "error": '{"error": "some error"}',
    }
