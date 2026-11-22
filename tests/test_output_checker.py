
from unittest.mock import Mock

import pytest

from app.services.security.output_checker import OutputChecker
from app.services.security.secret_scanner import SecretScanner


@pytest.fixture
def checker(monkeypatch):
    instance = OutputChecker.__new__(OutputChecker)

    instance.pii_scanner = Mock()
    instance.pii_scanner.scan.return_value = {
        "detected": False,
        "entities": [],
        "severity": "low",
        "method": "presidio",
    }

    monkeypatch.setattr(
        SecretScanner,
        "scan",
        lambda content: {
            "detected": False,
            "findings": [],
            "severity": "low",
            "method": "regex",
        },
    )

    return instance


def test_safe_output_passes(checker):
    result = checker.scan("The weather is pleasant today.")

    assert result["passed"] is True
    assert result["findings"] == []
    assert result["risk_level"] == "low"


def test_pii_in_output_is_blocked(checker):
    checker.pii_scanner.scan.return_value = {
        "detected": True,
        "entities": [
            {"entity_type": "EMAIL_ADDRESS"}
        ],
        "severity": "high",
        "method": "presidio",
    }

    result = checker.scan("Contact user@example.com")

    assert result["passed"] is False
    assert result["risk_level"] == "high"
    assert len(result["findings"]) == 1
    assert result["findings"][0]["type"] == "PII_EXPOSURE"


def test_secret_in_output_is_blocked(checker, monkeypatch):
    monkeypatch.setattr(
        SecretScanner,
        "scan",
        lambda content: {
            "detected": True,
            "findings": [
                {"secret_type": "openai_api_key", "count": 1}
            ],
            "severity": "critical",
            "method": "regex",
        },
    )

    result = checker.scan("Sensitive credential output")

    assert result["passed"] is False
    assert result["risk_level"] == "critical"
    assert result["findings"][0]["type"] == "SECRET_EXPOSURE"


def test_combined_pii_and_secret_findings_are_blocked(
    checker,
    monkeypatch,
):
    checker.pii_scanner.scan.return_value = {
        "detected": True,
        "entities": [
            {"entity_type": "EMAIL_ADDRESS"}
        ],
        "severity": "high",
        "method": "presidio",
    }

    monkeypatch.setattr(
        SecretScanner,
        "scan",
        lambda content: {
            "detected": True,
            "findings": [
                {"secret_type": "api_key", "count": 1}
            ],
            "severity": "critical",
            "method": "regex",
        },
    )

    result = checker.scan("Sensitive output")

    assert result["passed"] is False
    assert result["risk_level"] == "critical"
    assert len(result["findings"]) == 2

    finding_types = {
        finding["type"]
        for finding in result["findings"]
    }

    assert finding_types == {
        "PII_EXPOSURE",
        "SECRET_EXPOSURE",
    }
