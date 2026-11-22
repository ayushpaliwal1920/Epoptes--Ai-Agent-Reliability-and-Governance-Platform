
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api import security as security_api
from app.db.model import Agent, SecurityEvent


@pytest.fixture
def current_user():
    return SimpleNamespace(
        id=10,
        organization_id=6,
    )


def make_query():
    query = Mock()
    query.filter.return_value = query
    query.order_by.return_value = query
    query.limit.return_value = query
    return query


# --------------------------------------------------
# GET /events
# --------------------------------------------------

def test_list_security_events_returns_organization_events(
    current_user,
):
    expected_events = [
        SimpleNamespace(id=1, severity="high"),
        SimpleNamespace(id=2, severity="critical"),
    ]

    query = make_query()
    query.all.return_value = expected_events

    db = Mock()
    db.query.return_value = query

    result = security_api.list_security_events(
        severity=None,
        event_type=None,
        db=db,
        current_user=current_user,
    )

    assert result == expected_events
    db.query.assert_called_once_with(SecurityEvent)
    query.filter.assert_called_once()
    query.order_by.assert_called_once()
    query.limit.assert_called_once_with(100)
    query.all.assert_called_once()


def test_list_security_events_filters_by_severity_and_type(
    current_user,
):
    expected_events = [
        SimpleNamespace(
            id=3,
            severity="critical",
            event_type="SECRET_DETECTED",
        )
    ]

    query = make_query()
    query.all.return_value = expected_events

    db = Mock()
    db.query.return_value = query

    result = security_api.list_security_events(
        severity="critical",
        event_type="SECRET_DETECTED",
        db=db,
        current_user=current_user,
    )

    assert result == expected_events

    # Organization + severity + event type.
    assert query.filter.call_count == 3


def test_list_security_events_returns_empty_list(
    current_user,
):
    query = make_query()
    query.all.return_value = []

    db = Mock()
    db.query.return_value = query

    result = security_api.list_security_events(
        db=db,
        current_user=current_user,
    )

    assert result == []


# --------------------------------------------------
# GET /events/{event_id}
# --------------------------------------------------

def test_get_security_event_returns_matching_event(
    current_user,
):
    expected_event = SimpleNamespace(
        id=25,
        organization_id=6,
        severity="high",
    )

    query = make_query()
    query.first.return_value = expected_event

    db = Mock()
    db.query.return_value = query

    result = security_api.get_security_event(
        event_id=25,
        db=db,
        current_user=current_user,
    )

    assert result == expected_event
    db.query.assert_called_once_with(SecurityEvent)
    query.filter.assert_called_once()
    query.first.assert_called_once()


def test_get_security_event_returns_404_when_not_found(
    current_user,
):
    query = make_query()
    query.first.return_value = None

    db = Mock()
    db.query.return_value = query

    with pytest.raises(HTTPException) as exc_info:
        security_api.get_security_event(
            event_id=999,
            db=db,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Security event not found"


def test_get_security_event_rejects_other_organization_event(
    current_user,
):
    # A cross-organization event must not be returned.
    query = make_query()
    query.first.return_value = None

    db = Mock()
    db.query.return_value = query

    with pytest.raises(HTTPException) as exc_info:
        security_api.get_security_event(
            event_id=500,
            db=db,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    query.filter.assert_called_once()


# --------------------------------------------------
# GET /agents/{agent_id}/security-summary
# --------------------------------------------------

def test_agent_security_summary_returns_event_counts(
    current_user,
):
    agent = SimpleNamespace(
        id=7,
        organization_id=6,
    )

    agent_query = make_query()
    agent_query.first.return_value = agent

    event_query = make_query()
    event_query.count.side_effect = [
        10,  # total
        2,   # critical
        3,   # high
        4,   # blocked
        5,   # open
    ]

    db = Mock()
    db.query.side_effect = [
        agent_query,
        event_query,
    ]

    result = security_api.get_agent_security_summary(
        agent_id=7,
        db=db,
        current_user=current_user,
    )

    assert result == {
        "agent_id": 7,
        "total_events": 10,
        "critical_events": 2,
        "high_events": 3,
        "blocked_events": 4,
        "open_events": 5,
    }

    assert db.query.call_count == 2
    agent_query.filter.assert_called_once()
    agent_query.first.assert_called_once()

    assert event_query.filter.call_count == 5
    assert event_query.count.call_count == 5


def test_agent_security_summary_returns_zero_counts(
    current_user,
):
    agent = SimpleNamespace(
        id=7,
        organization_id=6,
    )

    agent_query = make_query()
    agent_query.first.return_value = agent

    event_query = make_query()
    event_query.count.return_value = 0

    db = Mock()
    db.query.side_effect = [
        agent_query,
        event_query,
    ]

    result = security_api.get_agent_security_summary(
        agent_id=7,
        db=db,
        current_user=current_user,
    )

    assert result["total_events"] == 0
    assert result["critical_events"] == 0
    assert result["high_events"] == 0
    assert result["blocked_events"] == 0
    assert result["open_events"] == 0


def test_agent_security_summary_rejects_other_organization_agent(
    current_user,
):
    # Agent from another organization is invisible to this user.
    agent_query = make_query()
    agent_query.first.return_value = None

    db = Mock()
    db.query.return_value = agent_query

    with pytest.raises(HTTPException) as exc_info:
        security_api.get_agent_security_summary(
            agent_id=999,
            db=db,
            current_user=current_user,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Agent not found"

    # No event queries should run after rejecting the agent.
    db.query.assert_called_once_with(Agent)
