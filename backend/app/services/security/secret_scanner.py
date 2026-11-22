import re


class SecretScanner:

    PATTERNS = {

        "openai_api_key":
            r"\bsk-[A-Za-z0-9_-]{20,}\b",

        "github_token":
            r"\bgh[pousr]_[A-Za-z0-9]{20,}\b",

        "aws_access_key":
            r"\bAKIA[0-9A-Z]{16}\b",

        "jwt_token":
            r"\beyJ[A-Za-z0-9_-]+\."
            r"[A-Za-z0-9_-]+\."
            r"[A-Za-z0-9_-]+\b",

        "password":
            r"(?i)(password|passwd|pwd)\s*[:=]\s*"
            r"['\"]?[^,\s'\"]{4,}",

        "api_key":
            r"(?i)(api[_-]?key|access[_-]?token)"
            r"\s*[:=]\s*['\"]?[A-Za-z0-9_\-]{12,}",

        "database_url":
            r"(?i)(postgres|mysql|mongodb)"
            r"://[^:\s]+:[^@\s]+@[^/\s]+",

    }

    @classmethod
    def scan(cls, content: str) -> dict:

        findings = []

        for secret_type, pattern in cls.PATTERNS.items():

            matches = re.findall(
                pattern,
                content
            )

            if matches:

                findings.append({
                    "secret_type": secret_type,
                    "count": len(matches)
                })

        return {
            "detected": len(findings) > 0,
            "findings": findings,
            "severity": "critical" if findings else "low",
            "method": "regex"
        }


    @classmethod
    def redact(cls, content: str) -> str:
        redacted = content

        for pattern in cls.PATTERNS.values():
            redacted = re.sub(
                pattern,
                "<SECRET_REDACTED>",
                redacted
            )

        return redacted