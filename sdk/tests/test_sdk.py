import pytest
import requests
from types import SimpleNamespace
from unittest.mock import Mock

from agentguard import AgentGuardClient
from agentguard.context import RunContext
from agentguard.exception import (
    APIError,
    AuthenticationError,
)


# ---------------------------------------------------------
# CLIENT INITIALIZATION
# ---------------------------------------------------------

def test_client_initialization():
    client = AgentGuardClient(
        api_key="test-api-key",
        base_url="http://localhost:8000/"
    )

    assert client.base_url == "http://localhost:8000"
    assert client.session.headers["X-Agent-Key"] == "test-api-key"
    assert client.session.headers["Content-Type"] == "application/json"

    client.close()


def test_client_requires_api_key():
    with pytest.raises(ValueError, match="API key is required"):
        AgentGuardClient(api_key="")


# ---------------------------------------------------------
# HTTP REQUEST HANDLING
# ---------------------------------------------------------

def test_successful_api_request():
    client = AgentGuardClient(api_key="test-key")

    mock_response = SimpleNamespace(
        status_code=200,
        ok=True,
        content=b'{"message": "success"}',
        json=lambda: {"message": "success"},
    )

    client.session.request = Mock(return_value=mock_response)

    result = client.request("GET", "/test")

    assert result == {"message": "success"}

    client.close()


def test_authentication_error():
    client = AgentGuardClient(api_key="invalid-key")

    mock_response = SimpleNamespace(
        status_code=401,
        ok=False,
        content=b"Unauthorized",
        text="Unauthorized",
    )

    client.session.request = Mock(return_value=mock_response)

    with pytest.raises(AuthenticationError):
        client.request("GET", "/test")

    client.close()


def test_api_error_for_failed_request():
    client = AgentGuardClient(api_key="test-key")

    mock_response = SimpleNamespace(
        status_code=500,
        ok=False,
        content=b"Internal Server Error",
        text="Internal Server Error",
    )

    client.session.request = Mock(return_value=mock_response)

    with pytest.raises(APIError, match="HTTP 500"):
        client.request("GET", "/test")

    client.close()


def test_connection_error():
    client = AgentGuardClient(api_key="test-key")

    client.session.request = Mock(
        side_effect=requests.ConnectionError("Server unavailable")
    )

    with pytest.raises(APIError, match="AgentGuard connection failed"):
        client.request("GET", "/test")

    client.close()


# ---------------------------------------------------------
# RUN LIFECYCLE
# ---------------------------------------------------------

def test_run_context_success():
    client = AgentGuardClient(api_key="test-key")

    client.request = Mock(side_effect=[
        {"run_id": 101},
        {"status": "success"},
    ])

    with client.run("Test Agent") as run:
        assert isinstance(run, RunContext)
        assert run.run_id == 101

    assert run.finished is True

    assert client.request.call_count == 2

    start_call = client.request.call_args_list[0]
    finish_call = client.request.call_args_list[1]

    assert start_call.args[0] == "POST"
    assert start_call.args[1] == "/api/v1/runs/start"

    assert finish_call.args[0] == "POST"
    assert finish_call.args[1] == "/api/v1/runs/101/finish"

    client.close()


def test_run_context_preserves_agent_exception():
    client = AgentGuardClient(api_key="test-key")

    client.request = Mock(side_effect=[
        {"run_id": 102},
        {"status": "error"},
    ])

    with pytest.raises(ValueError, match="Agent failed"):
        with client.run("Failing Agent") as run:
            raise ValueError("Agent failed")

    finish_payload = client.request.call_args_list[1].args[2]
    assert finish_payload["status"] == "error"
    assert finish_payload["error_type"] == "ValueError"
    assert finish_payload["error_message"] == "Agent failed"

    client.close()


# ---------------------------------------------------------
# TRACE LIFECYCLE
# ---------------------------------------------------------

def test_trace_success():
    mock_client = Mock()

    run = RunContext(mock_client, run_id=201)

    with run.trace(
        name="Test LLM Call",
        trace_type="llm",
        provider="test-provider",
        model_name="test-model",
    ):
        pass

    assert mock_client.request.call_count == 2

    start_call = mock_client.request.call_args_list[0]
    finish_call = mock_client.request.call_args_list[1]

    assert start_call.args[0] == "POST"
    assert "/traces/" in start_call.args[1]

    assert finish_call.args[0] == "POST"
    assert "/finish" in finish_call.args[1]
    assert finish_call.args[2]["status"] == "success"

    assert run.steps == 1
    assert run.llm_calls == 1
    assert run.tool_calls == 0


def test_trace_records_error():
    mock_client = Mock()

    run = RunContext(mock_client, run_id=202)

    with pytest.raises(RuntimeError, match="Trace failed"):
        with run.trace(
            name="Failing Tool",
            trace_type="tool",
            tool_name="test_tool",
        ):
            raise RuntimeError("Trace failed")

    assert mock_client.request.call_count == 2

    finish_payload = mock_client.request.call_args_list[1].args[2]

    assert finish_payload["status"] == "error"
    assert finish_payload["error_type"] == "RuntimeError"
    assert finish_payload["error_message"] == "Trace failed"

    assert run.steps == 1
    assert run.tool_calls == 1


# ---------------------------------------------------------
# EVENT LOGGING
# ---------------------------------------------------------

def test_event_logging():
    mock_client = Mock()
    mock_client.request.return_value = {"message": "Event created"}

    run = RunContext(mock_client, run_id=301)

    result = run.log(
        event_type="agent.started",
        message="Agent execution started",
        severity="info",
        payload={"source": "unit-test"},
    )

    assert result == {"message": "Event created"}

    call = mock_client.request.call_args

    assert call.args[0] == "POST"
    assert call.args[1] == "/api/v1/runs/301/events/"
    assert call.args[2]["event_type"] == "agent.started"
    assert 	call.args[2]["severity"] == "info"


# ---------------------------------------------------------
# TOKEN AND COST TRACKING
# ---------------------------------------------------------

def test_usage_tracking():
    mock_client = Mock()

    run = RunContext(mock_client, run_id=401)

    run.record_usage(
        input_tokens=500,
        output_tokens=250,
        cost=0.002,
    )

    run.record_usage(
        input_tokens=100,
        output_tokens=50,
        cost=0.001,
    )

    run.record_retry()

    assert run.input_tokens == 600
    assert run.output_tokens == 300
    assert run.estimated_cost == pytest.approx(0.003)
    assert run.retries == 1


def test_run_finish_sends_usage_metrics():
    mock_client = Mock()
    mock_client.request.return_value = {"status": "success"}

    run = RunContext(mock_client, run_id=402)

    run.record_usage(
        input_tokens=1000,
        output_tokens=500,
        cost=0.005,
    )

    run.record_retry()

    result = run.finish(status="success")

    assert result == {"status": "success"}
    assert run.finished is True

    call = mock_client.request.call_args

    assert call.args[0] == "POST"
    assert call.args[1] == "/api/v1/runs/402/finish"

    payload = call.args[2]

    assert payload["status"] == "success"
    assert payload["input_tokens"] == 1000
    assert payload["output_tokens"] == 500
    assert payload["retry_count"] == 1
    assert payload["estimated_cost"] == pytest.approx(0.005)


def test_run_finish_is_idempotent():
    mock_client = Mock()
    mock_client.request.return_value = {"status": "success"}

    run = RunContext(mock_client, run_id=403)

    run.finish()
    run.finish()

    assert mock_client.request.call_count == 1


def test_trace_usage_is_aggregated_into_run():
    mock_client = Mock()
    mock_client.request.return_value = {"status": "success"}

    run = RunContext(mock_client, run_id=501)

    with run.trace(
        name="LLM Call",
        trace_type="llm",
        provider="test",
        model_name="test-model",
    ) as trace:

        trace.record_usage(
            input_tokens=300,
            output_tokens=150,
            cost=0.001,
        )

    assert run.input_tokens == 300
    assert run.output_tokens == 150
    assert run.estimated_cost == pytest.approx(0.001)

    finish_payload = mock_client.request.call_args_list[1].args[2]

    assert finish_payload["input_tokens"] == 300
    assert finish_payload["output_tokens"] == 150
    assert finish_payload["estimated_cost"] == pytest.approx(0.001)


def test_multiple_trace_usage_aggregation():
    mock_client = Mock()
    mock_client.request.return_value = {"status": "success"}

    run = RunContext(mock_client, run_id=502)

    with run.trace("LLM Call 1", trace_type="llm") as trace:
        trace.record_usage(300, 150, 0.001)

    with run.trace("LLM Call 2", trace_type="llm") as trace:
        trace.record_usage(200, 100, 0.001)

    assert run.input_tokens == 500
    assert run.output_tokens == 250
    assert run.estimated_cost == pytest.approx(0.002)

    run.finish()

    run_payload = mock_client.request.call_args.args[2]

    assert run_payload["input_tokens"] == 500
    assert run_payload["output_tokens"] == 250
    assert run_payload["estimated_cost"] == pytest.approx(0.002)


def test_trace_retry_tracking():
    mock_client = Mock()
    mock_client.request.return_value = {"status": "success"}

    run = RunContext(mock_client, run_id=503)

    with run.trace("LLM Retry Test", trace_type="llm") as trace:
        trace.record_retry()
        trace.record_retry()

    assert trace.retries == 2
    assert run.retries == 2

    finish_payload = mock_client.request.call_args_list[1].args[2]

    assert finish_payload["retry_count"] == 2


def test_trace_rejects_negative_usage():
    mock_client = Mock()

    run = RunContext(mock_client, run_id=504)

    with run.trace("Invalid Usage", trace_type="llm") as trace:
        with pytest.raises(ValueError):
            trace.record_usage(input_tokens=-10)

