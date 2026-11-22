from app.services.security.scope_checker import ScopeChecker
from app.services.security.injection import PromptInjectionDetector
from app.services.security.jailbreak import JailbreakDetector
from app.services.security.pii_scanner import PIIScanner
from app.services.security.secret_scanner import SecretScanner
from app.services.security.output_checker import OutputChecker


class SecurityEngine:

    def __init__(self):

        self.pii_scanner = PIIScanner()

        self.output_checker = OutputChecker()

    def scan_content(
        self,
        content: str,
        scan_type: str = "input"
    ) -> dict:

        findings = []

        injection = PromptInjectionDetector.scan(content)

        jailbreak = JailbreakDetector.scan(content)

        pii = self.pii_scanner.scan(content)

        secrets = SecretScanner.scan(content)

        if injection["detected"]:

            findings.append({
                "event_type": "PROMPT_INJECTION",
                "severity": "high",
                "description": "Suspicious prompt instructions detected",
                "detection_method": injection["method"],
                "blocked": True
            })

        if jailbreak["detected"]:

            findings.append({
                "event_type": "JAILBREAK_ATTEMPT",
                "severity": "high",
                "description": "Potential jailbreak attempt detected",
                "detection_method": jailbreak["method"],
                "blocked": True
            })

        if pii["detected"] and scan_type == "input":

            findings.append({
                "event_type": "PII_DETECTED",
                "severity": "high",
                "description": "Personal information detected",
                "detection_method": "presidio",
                "blocked": False
            })

        if secrets["detected"] and scan_type == "input":

            findings.append({
                "event_type": "SECRET_DETECTED",
                "severity": "critical",
                "description": "Potential secret exposure detected",
                "detection_method": "regex",
                "blocked": True
            })

        if scan_type == "output":

            output = self.output_checker.scan(content)

            for finding in output["findings"]:

                findings.append({
                    "event_type": finding["type"],
                    "severity": finding["severity"],
                    "description": finding["description"],
                    "detection_method": "output_checker",
                    "blocked": True
                })

        blocked = any(
            finding["blocked"]
            for finding in findings
        )

        risk_order = {
            "low": 0,
            "medium": 1,
            "high": 2,
            "critical": 3
        }

        risk_level = max(
            (
                finding["severity"]
                for finding in findings
            ),
            key=lambda level: risk_order[level],
            default="low"
        )

        return {
            "passed": not blocked,
            "blocked": blocked,
            "risk_level": risk_level,
            "findings": findings
        }