
import uuid
import requests

from contextlib import contextmanager

from agentguard.context import RunContext
from agentguard.exception import (
    APIError,
    AuthenticationError,
)


class AgentGuardClient:

    def __init__(
        self,
        api_key,
        base_url="http://127.0.0.1:8000",
        timeout=10,
    ):
        if not api_key:
            raise ValueError("API key is required")

        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

        self.session = requests.Session()

        # Reuse M1 agent authentication.
        self.session.headers.update({
            "X-Agent-Key": api_key,
            "Content-Type": "application/json",
        })

    def request(self, method, endpoint, data=None):
        try:
            response = self.session.request(
                method,
                f"{self.base_url}{endpoint}",
                json=data,
                timeout=self.timeout,
            )

            if response.status_code == 401:
                raise AuthenticationError(
                    "Invalid or inactive agent API key"
                )

            if not response.ok:
                raise APIError(
                    f"HTTP {response.status_code}: "
                    f"{response.text[:1000]}"
                )

            return (
                response.json()
                if response.content
                else {}
            )

        except requests.RequestException as exc:
            raise APIError(
                f"AgentGuard connection failed: {exc}"
            ) from exc

    @contextmanager
    def run(self, name, metadata=None):

        external_run_id = str(uuid.uuid4())

        result = self.request(
            "POST",
            "/api/v1/runs/start",
            {
                "external_run_id": external_run_id,
                "name": name,
                "metadata": metadata or {},
            },
        )

        context = RunContext(
            self,
            result["run_id"],
        )

        try:
            yield context

        except Exception as exc:
            try:
                context.finish(
                    status="error",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            except Exception:
                # Preserve the original agent exception.
                pass

            raise

        else:
            context.finish(status="success")

    def close(self):
        self.session.close()
