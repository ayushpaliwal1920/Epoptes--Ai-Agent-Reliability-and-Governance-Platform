
import json
import requests
from contextlib import nullcontext


class ToolAuthorizationError(PermissionError):
    """Raised when AgentGuard denies a tool operation."""


class ToolOutputBlockedError(RuntimeError):
    """Raised when AgentGuard blocks tool output."""


class SecurityServiceError(RuntimeError):
    """Raised when security validation cannot be completed."""


class SecurityClient:

    def __init__(
        self,
        base_url: str,
        api_key: str
    ):
        if not api_key:
            raise ValueError("API key is required")

        self.base_url = base_url.rstrip("/")

        self.session = requests.Session()

        self.session.headers.update({
            "X-Agent-Key": api_key,
            "Content-Type": "application/json",
        })

    def _post(self, endpoint, payload, timeout=10):
        try:
            response = self.session.post(
                f"{self.base_url}{endpoint}",
                json=payload,
                timeout=timeout,
            )

            response.raise_for_status()
            return response.json()

        except requests.RequestException as exc:
            raise SecurityServiceError(
                f"AgentGuard security request failed: {exc}"
            ) from exc

    def authorize(
    self,
    tool_name=None,
    action=None,
    resource=None,
    transaction_amount=None,
    run_id=None,
):
        result = self._post(
            "/api/v1/security/authorize",
            {
                "tool_name": tool_name,
                "action": action,
                "resource": resource,
                "transaction_amount": transaction_amount,
                "run_id": run_id,
            },
        )

        if not result.get("authorized", False):
            raise ToolAuthorizationError(
                result.get(
                    "reason",
                    "Agent operation not authorized",
                )
            )

        return result

    def scan(
        self,
        content: str,
        scan_type: str = "input",
        run_id=None,
    ):
        return self._post(
            "/api/v1/security/scan",
            {
                "content": content,
                "scan_type": scan_type,
                "run_id": run_id,
            },
            timeout=30,
        )

    def execute_tool(
        self,
        tool,
        tool_name: str,
        action: str,
        resource: str,
        run_context=None,
        transaction_amount=None,
        *args,
        **kwargs,
    ):
        """
        Authorize, execute and scan a tool operation.

        The tool is never called if authorization fails.
        Its output is never returned if output scanning blocks it.
        """

        if not callable(tool):
            raise TypeError("tool must be callable")

        if not tool_name or not action or not resource:
            raise ValueError(
                "tool_name, action and resource are required"
            )

        trace_context = (
            run_context.trace(
                name=tool_name,
                trace_type="tool",
                tool_name=tool_name,
                input_data={
                    "action": action,
                    "resource": resource,
                },
            )
            if run_context is not None
            else nullcontext()
        )

        with trace_context:

            # 1. Authorization must happen before tool execution.
            authorization = self.authorize(
                            tool_name=tool_name,
                            action=action,
                            resource=resource,
                            transaction_amount=transaction_amount,
                            run_id=(
                                run_context.run_id
                                if run_context is not None
                                else None
                            ),
                        )

            # 2. Execute the actual tool only after authorization.
            result = tool(*args, **kwargs)

            # 3. Scan the tool output before returning it.
            try:
                serialized_output = json.dumps(
                    result,
                    default=str,
                    ensure_ascii=False,
                )

                scan_result = self.scan(
                    content=serialized_output,
                    scan_type="output",
                    run_id=(
                        run_context.run_id
                        if run_context is not None
                        else None
                    ),
                )

            except Exception as exc:
                raise SecurityServiceError(
                    "Tool output security validation failed; "
                    "output will not be returned."
                ) from exc

            if scan_result.get("blocked", False):
                raise ToolOutputBlockedError(
                    "AgentGuard blocked the tool output."
                )

            return {
                "result": result,
                "authorization": authorization,
                "output_scan": scan_result,
            }

    def close(self):
        self.session.close()
