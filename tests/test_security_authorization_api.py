
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.api import security as security_api
from app.schemas.security import AuthorizationRequest


from fastapi import HTTPException

from app.db.model import AgentRun

@pytest.fixture
def agent():
    return SimpleNamespace(
        id=7,
        organization_id=6,
    )




@pytest.fixture
def allowed_scope():
    return SimpleNamespace(
        enabled=True,
        allowed_tools=["get_invoice"],
        allowed_actions=["read_invoice"],
        restricted_actions=["delete", "transfer_funds"],
        allowed_resources=["invoice_records"],
        allowed_topics=["research"],
        resource_limits={
            "max_requests_per_minute": 60,
            "max_tool_calls_per_run": 20,
            "max_transaction_amount": 1000.0,
        },
    )


def make_payload(
    tool_name="get_invoice",
    action="read_invoice",
    resource="invoice_records",
):
    return AuthorizationRequest(
        tool_name=tool_name,
        action=action,
        resource=resource,
    )


def make_scope_query(scope):
    query = Mock()
    query.filter.return_value = query
    query.with_for_update.return_value = query
    query.first.return_value = scope
    return query


def make_count_query(count):
    query = Mock()
    query.filter.return_value = query
    query.scalar.return_value = count
    return query


def make_db(scope, recent_requests=0):
    db = Mock()

    scope_query = make_scope_query(scope)
    rate_query = make_count_query(recent_requests)

    db.query.side_effect = [
        scope_query,
        rate_query,
    ]

    # Simulate the database assigning an event ID.
    db.refresh.side_effect = (
        lambda event: setattr(event, "id", 900)
    )

    return db


def test_missing_scope_denies_authorization(agent):
    db = make_db(scope=None)

    result = security_api.authorize_operation(
        payload=make_payload(),
        db=db,
        agent=agent,
    )

    assert result["authorized"] is False
    assert result["reason"] == "Agent scope missing or disabled"
    assert result["event_id"] == 900

    event = db.add.call_args.args[0]

    assert event.event_type == "TOOL_AUTHORIZATION_DENIED"
    assert event.blocked is True

    db.commit.assert_called_once()


def test_disabled_scope_denies_authorization(agent):
    disabled_scope = SimpleNamespace(
        enabled=False,
    )

    db = make_db(scope=disabled_scope)

    result = security_api.authorize_operation(
        payload=make_payload(),
        db=db,
        agent=agent,
    )

    assert result["authorized"] is False
    assert result["event_id"] == 900

    event = db.add.call_args.args[0]

    assert event.event_type == "TOOL_AUTHORIZATION_DENIED"
    assert event.blocked is True


def test_valid_operation_is_authorized(agent, allowed_scope):
    db = make_db(scope=allowed_scope)

    result = security_api.authorize_operation(
        payload=make_payload(),
        db=db,
        agent=agent,
    )

    assert result["authorized"] is True
    assert result["agent_id"] == agent.id
    assert result["run_id"] is None
    assert result["reason"] == "All permission checks passed"

    assert all(
        check["allowed"]
        for check in result["checks"]
    )

    event = db.add.call_args.args[0]

    assert event.event_type == "TOOL_AUTHORIZATION_ALLOWED"
    assert event.blocked is False

    db.commit.assert_called_once()


def test_unauthorized_tool_is_denied(agent, allowed_scope):
    db = make_db(scope=allowed_scope)

    result = security_api.authorize_operation(
        payload=make_payload(tool_name="delete_employee"),
        db=db,
        agent=agent,
    )

    assert result["authorized"] is False

    assert any(
        not check["allowed"]
        for check in result["checks"]
    )

    event = db.add.call_args.args[0]

    assert event.event_type == "TOOL_AUTHORIZATION_DENIED"
    assert event.blocked is True


def test_rate_limit_exceeded_is_denied(agent, allowed_scope):
    allowed_scope.resource_limits["max_requests_per_minute"] = 1

    db = make_db(
        scope=allowed_scope,
        recent_requests=1,
    )

    result = security_api.authorize_operation(
        payload=make_payload(),
        db=db,
        agent=agent,
    )

    assert result["authorized"] is False
    assert "requests-per-minute" in result["reason"]

    event = db.add.call_args.args[0]

    assert event.event_type == "TOOL_RATE_LIMIT_EXCEEDED"
    assert event.blocked is True

    # Rate-limit events are audited and committed.
    db.commit.assert_called_once()



def test_per_run_limit_exceeded_is_denied(agent, allowed_scope):
    allowed_scope.resource_limits["max_tool_calls_per_run"] = 2

    run_query = make_scope_query(
        SimpleNamespace(
            id=42,
            agent_id=agent.id,
            organization_id=agent.organization_id,
        )
    )

    scope_query = make_scope_query(allowed_scope)
    rate_query = make_count_query(0)

    # Two previously authorized operations in this run.
    run_count_query = make_count_query(2)

    db = Mock()
    db.query.side_effect = [
        run_query,       # Validate run ownership
        scope_query,     # Load and lock scope
        rate_query,      # Requests per minute
        run_count_query, # Authorized operations in this run
    ]

    db.refresh.side_effect = (
        lambda event: setattr(event, "id", 901)
    )

    payload = AuthorizationRequest(
        tool_name="get_invoice",
        action="read_invoice",
        resource="invoice_records",
        run_id=42,
    )

    result = security_api.authorize_operation(
        payload=payload,
        db=db,
        agent=agent,
    )

    assert result["authorized"] is False
    assert "maximum tool calls" in result["reason"]
    assert result["event_id"] == 901

    event = db.add.call_args.args[0]

    assert event.event_type == "TOOL_RUN_LIMIT_EXCEEDED"
    assert event.blocked is True
    assert event.run_id == 42

    db.commit.assert_called_once()


def test_other_agents_run_is_rejected(agent):
    # Simulate a run that does not belong to this agent.
    run_query = make_scope_query(None)

    db = Mock()
    db.query.side_effect = [run_query]

    payload = AuthorizationRequest(
        tool_name="get_invoice",
        action="read_invoice",
        resource="invoice_records",
        run_id=999,
    )

    with pytest.raises(HTTPException) as exc_info:
        security_api.authorize_operation(
            payload=payload,
            db=db,
            agent=agent,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Run not found for this agent"

    # Authorization must stop before loading the scope.
    db.query.assert_called_once()

    # No authorization event should be recorded for an invalid run.
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_transaction_amount_is_checked_when_provided(
    agent,
    allowed_scope,
):
    payload = AuthorizationRequest(
        tool_name="get_invoice",
        action="read_invoice",
        resource="invoice_records",
        transaction_amount=100.0,
    )

    db = make_db(scope=allowed_scope)

    result = security_api.authorize_operation(
        payload=payload,
        db=db,
        agent=agent,
    )

    assert result["authorized"] is True

    # The transaction-limit check is the fourth check.
    assert len(result["checks"]) == 4
    assert result["checks"][3]["allowed"] is True


def test_financial_action_without_amount_is_denied(
    agent,
    allowed_scope,
):
    allowed_scope.restricted_actions = []
    allowed_scope.allowed_actions = ["transfer_funds"]

    payload = AuthorizationRequest(
        tool_name="get_invoice",
        action="transfer_funds",
        resource="invoice_records",
    )

    db = make_db(scope=allowed_scope)

    result = security_api.authorize_operation(
        payload=payload,
        db=db,
        agent=agent,
    )

    assert result["authorized"] is False
    assert len(result["checks"]) == 4
    assert result["checks"][3]["allowed"] is False
    assert (
        result["checks"][3]["reason"]
        == "Transaction amount is required for this action"
    )


