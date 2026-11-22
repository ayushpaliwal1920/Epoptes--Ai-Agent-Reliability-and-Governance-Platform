
import pytest
from unittest.mock import Mock

from agentguard.agent_governance.security import (
    SecurityClient,
    ToolAuthorizationError,
    ToolOutputBlockedError,
)


def make_client():
    return SecurityClient(
        base_url="http://localhost:8000",
        api_key="test-key",
    )


def test_tool_executes_when_authorized(monkeypatch):
    client = make_client()

    monkeypatch.setattr(
        client,
        "authorize",
        Mock(return_value={"authorized": True}),
    )

    monkeypatch.setattr(
        client,
        "scan",
        Mock(return_value={"blocked": False}),
    )

    tool = Mock(return_value={"total": 5000})

    result = client.execute_tool(
        tool=tool,
        tool_name="get_invoice",
        action="read_invoice",
        resource="invoice_records",
        invoice_id=101,
    )

    tool.assert_called_once_with(invoice_id=101)
    assert result["result"] == {"total": 5000}

    client.close()


def test_tool_does_not_execute_when_denied(monkeypatch):
    client = make_client()

    monkeypatch.setattr(
        client,
        "authorize",
        Mock(
            side_effect=ToolAuthorizationError("Not permitted")
        ),
    )

    tool = Mock()

    with pytest.raises(ToolAuthorizationError):
        client.execute_tool(
            tool=tool,
            tool_name="delete_employee",
            action="delete_employee",
            resource="employee_records",
        )

    tool.assert_not_called()
    client.close()


def test_blocked_output_is_not_returned(monkeypatch):
    client = make_client()

    monkeypatch.setattr(
        client,
        "authorize",
        Mock(return_value={"authorized": True}),
    )

    monkeypatch.setattr(
        client,
        "scan",
        Mock(return_value={"blocked": True}),
    )

    tool = Mock(return_value={"secret": "sensitive-value"})

    with pytest.raises(ToolOutputBlockedError):
        client.execute_tool(
            tool=tool,
            tool_name="get_invoice",
            action="read_invoice",
            resource="invoice_records",
        )

    tool.assert_called_once()
    client.close()

