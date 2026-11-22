
from app.services.security.secret_scanner import SecretScanner


def test_safe_text_has_no_secrets():
    result = SecretScanner.scan(
        "This is a normal research document."
    )

    assert result["detected"] is False
    assert result["findings"] == []
    assert result["severity"] == "low"


def test_openai_api_key_is_detected():
    result = SecretScanner.scan(
        "api credential: sk-123456789012345678901234"
    )

    assert result["detected"] is True
    assert any(
        item["secret_type"] == "openai_api_key"
        for item in result["findings"]
    )
    assert result["severity"] == "critical"


def test_multiple_secret_types_are_detected():
    content = (
        "AWS key: AKIA1234567890ABCDEF "
        "Password: mySecretPassword123 "
        "GitHub: ghp_123456789012345678901234"
    )

    result = SecretScanner.scan(content)

    detected_types = {
        item["secret_type"]
        for item in result["findings"]
    }

    assert result["detected"] is True
    assert "aws_access_key" in detected_types
    assert "password" in detected_types
    assert "github_token" in detected_types


def test_api_key_and_database_url_are_detected():
    content = (
        "api_key=abcdef123456789012345 "
        "postgres://admin:secret123@localhost:5432/mydb"
    )

    result = SecretScanner.scan(content)

    detected_types = {
        item["secret_type"]
        for item in result["findings"]
    }

    assert "api_key" in detected_types
    assert "database_url" in detected_types


def test_jwt_token_is_detected():
    content = (
        "Token: "
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )

    result = SecretScanner.scan(content)

    assert result["detected"] is True
    assert any(
        item["secret_type"] == "jwt_token"
        for item in result["findings"]
    )


def test_all_supported_secret_patterns_are_redacted():
    content = (
        "OpenAI: sk-123456789012345678901234 "
        "GitHub: ghp_123456789012345678901234 "
        "AWS: AKIA1234567890ABCDEF "
        "JWT: eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.signature123 "
        "Password: mySecretPassword123 "
        "api_key=abcdef123456789012345 "
        "DB: postgres://admin:secret123@localhost:5432/mydb"
    )

    redacted = SecretScanner.redact(content)

    assert "<SECRET_REDACTED>" in redacted
    assert "sk-123456789012345678901234" not in redacted
    assert "ghp_123456789012345678901234" not in redacted
    assert "AKIA1234567890ABCDEF" not in redacted
    assert "mySecretPassword123" not in redacted
    assert "abcdef123456789012345" not in redacted
    assert "postgres://admin:secret123@localhost:5432/mydb" not in redacted
