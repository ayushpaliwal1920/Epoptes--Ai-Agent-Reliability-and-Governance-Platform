
from app.services.security.pii_scanner import PIIScanner


def test_email_is_detected():
    scanner = PIIScanner()

    result = scanner.scan(
        "Contact john.doe@example.com for more information."
    )

    assert result["detected"] is True
    assert len(result["entities"]) > 0
    assert result["severity"] == "high"
    assert result["method"] == "presidio"


def test_safe_text_has_no_pii():
    scanner = PIIScanner()

    result = scanner.scan(
        "AI agents can improve research productivity."
    )

    assert result["detected"] is False
    assert result["entities"] == []
    assert result["severity"] == "low"


def test_email_is_redacted():
    scanner = PIIScanner()

    original = "Contact john.doe@example.com for assistance."

    redacted = scanner.redact(original)

    assert "john.doe@example.com" not in redacted
    assert "<REDACTED>" in redacted


def test_redaction_preserves_safe_text():
    scanner = PIIScanner()

    original = "Please review this research document."

    redacted = scanner.redact(original)

    assert redacted == original
