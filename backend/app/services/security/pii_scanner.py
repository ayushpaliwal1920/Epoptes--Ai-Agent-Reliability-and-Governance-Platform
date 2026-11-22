from presidio_analyzer import AnalyzerEngine
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import OperatorConfig


class PIIScanner:

    def __init__(self):

        self.analyzer = AnalyzerEngine()

        self.anonymizer = AnonymizerEngine()

    def scan(self, content: str) -> dict:

        results = self.analyzer.analyze(
            text=content,
            language="en"
        )

        entities = [
            {
                "entity_type": result.entity_type,
                "start": result.start,
                "end": result.end,
                "score": result.score
            }
            for result in results
        ]

        return {
            "detected": len(entities) > 0,
            "entities": entities,
            "severity": "high" if entities else "low",
            "method": "presidio"
        }

    def redact(self, content: str) -> str:

        results = self.analyzer.analyze(
            text=content,
            language="en"
        )

        anonymized = self.anonymizer.anonymize(
            text=content,
            analyzer_results=results,
            operators={
                "DEFAULT": OperatorConfig(
                    "replace",
                    {"new_value": "<REDACTED>"}
                )
            }
        )

        return anonymized.text