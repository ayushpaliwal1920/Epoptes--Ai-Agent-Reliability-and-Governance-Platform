from app.services.security.pii_scanner import PIIScanner
from app.services.security.secret_scanner import SecretScanner


class OutputChecker:

    def __init__(self):

        self.pii_scanner = PIIScanner()

    def scan(self, content: str) -> dict:

        pii_result = self.pii_scanner.scan(content)

        secret_result = SecretScanner.scan(content)

        findings = []

        if pii_result["detected"]:

            findings.append({
                "type": "PII_EXPOSURE",
                "severity": "high",
                "description": "Personal information detected in output"
            })

        if secret_result["detected"]:

            findings.append({
                "type": "SECRET_EXPOSURE",
                "severity": "critical",
                "description": "Sensitive credentials detected in output"
            })

        return {
            "passed": len(findings) == 0,
            "findings": findings,
            "risk_level": (
                "critical"
                if any(
                    f["severity"] == "critical"
                    for f in findings
                )
                else "high"
                if findings
                else "low"
            )
        }