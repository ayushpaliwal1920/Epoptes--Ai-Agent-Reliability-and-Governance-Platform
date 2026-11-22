import re


class PromptInjectionDetector:

    PATTERNS = [
        r"ignore\s+(all\s+)?previous\s+instructions",
        r"disregard\s+(all\s+)?(previous\s+)?instructions",
        r"override\s+(your\s+)?system\s+prompt",
        r"reveal\s+(your\s+)?system\s+prompt",
        r"ignore\s+your\s+system\s+message",
        r"follow\s+these\s+instructions\s+instead",
        r"bypass\s+(all\s+)?security",
        r"disable\s+(all\s+)?safety\s+rules",
        r"send\s+(all\s+)?(the\s+)?(secrets|credentials|passwords)",
    ]

    @classmethod
    def scan(cls, content: str) -> dict:

        detected = []

        normalized = content.lower()

        for pattern in cls.PATTERNS:

            if re.search(pattern, normalized, re.IGNORECASE):

                detected.append(pattern)

        return {
            "detected": len(detected) > 0,
            "severity": "high" if detected else "low",
            "matches": detected,
            "method": "rule_based"
        }