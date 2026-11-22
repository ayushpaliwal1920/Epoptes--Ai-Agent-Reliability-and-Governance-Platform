
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.api import security as security_api
from app.db.model import AgentRun, SecurityScanResult
from app.schemas.security import SecurityScanRequest


@pytest.fixture
def agent():
    return SimpleNamespace(
        id=7,
        organization_id=6,
    )


def make_payload():
    return SecurityScanRequest(
        content="Explain how AI agents improve research.",
        scan_type="input",
        run_id=42,
    )


def test_scan_rejects_run_not_owned_by_agent(agent, monkeypatch):
    query = Mock()
    query.filter.return_value = query
    query.first.return_value = None

    db = Mock()
    db.query.return_value = query

    engine_mock = Mock()
    monkeypatch.setattr(
        security_api,
        "engine",
        engine_mock,
    )

    with pytest.raises(HTTPException) as exc_info:
        security_api.scan_content(
            payload=make_payload(),
            db=db,
            agent=agent,
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Run not found for this agent"

    db.query.assert_called_once_with(AgentRun)
    engine_mock.scan_content.assert_not_called()
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_scan_accepts_run_owned_by_agent(agent, monkeypatch):
    run = SimpleNamespace(
        id=42,
        agent_id=7,
        organization_id=6,
    )

    query = Mock()
    query.filter.return_value = query
    query.first.return_value = run

    db = Mock()
    db.query.return_value = query

    engine_mock = Mock()
    engine_mock.scan_content.return_value = {
        "passed": True,
        "blocked": False,
        "risk_level": "low",
        "findings": [],
    }

    monkeypatch.setattr(
        security_api,
        "engine",
        engine_mock,
    )

    monkeypatch.setattr(
        security_api.event_manager,
        "record_findings",
        lambda **kwargs: [],
    )

    def assign_scan_id(record):
        if isinstance(record, SecurityScanResult):
            record.id = 501

    db.add.side_effect = assign_scan_id

    result = security_api.scan_content(
        payload=make_payload(),
        db=db,
        agent=agent,
    )

    assert result["passed"] is True
    assert result["blocked"] is False
    assert result["scan_id"] == 501
    assert result["event_ids"] == []

    engine_mock.scan_content.assert_called_once()
    db.add.assert_called_once()
    db.commit.assert_called_once()
