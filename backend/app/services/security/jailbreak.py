import re


class JailbreakDetector:

    PATTERNS = [

        r"act\s+as\s+an?\s+unrestricted\s+ai",

        r"you\s+have\s+no\s+restrictions",

        r"pretend\s+you\s+are\s+not\s+an\s+ai",

        r"developer\s+mode",

        r"do\s+anything\s+now",

        r"ignore\s+your\s+safety\s+guidelines",

        r"bypass\s+your\s+content\s+policy",

        r"never\s+refuse\s+any\s+request",

        r"disable\s+your\s+ethical\s+constraints",

    ]

    @classmethod
    def scan(cls, content: str) -> dict:

        matches = []

        for pattern in cls.PATTERNS:

            if re.search(
                pattern,
                content,
                re.IGNORECASE
            ):
                matches.append(pattern)

        return {
            "detected": bool(matches),
            "severity": "high" if matches else "low",
            "matches": matches,
            "method": "rule_based"
        }