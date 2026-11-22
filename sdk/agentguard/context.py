
import uuid
import time
from contextlib import contextmanager


class TraceContext:
    """Tracks usage and lifecycle information for an individual trace."""

    def __init__(self, run_context, trace_id, trace_type):
        self.run_context = run_context
        self.trace_id = trace_id
        self.trace_type = trace_type

        self.input_tokens = 0
        self.output_tokens = 0
        self.estimated_cost = 0.0
        self.retries = 0

    def record_usage(self, input_tokens=0, output_tokens=0, cost=0.0):
        if input_tokens < 0 or output_tokens < 0 or cost < 0:
            raise ValueError("Usage values cannot be negative")

        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.estimated_cost += cost

        # Aggregate trace usage into the parent run.
        self.run_context.record_usage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
        )

    def record_retry(self):
        self.retries += 1
        self.run_context.record_retry()

    def finish(self, status="success", error_type=None, error_message=None):
        payload = {
            "status": status,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost": self.estimated_cost,
            "retry_count": self.retries,
            "error_type": error_type,
            "error_message": error_message,
        }

        return self.run_context.client.request(
            "POST",
            f"/api/v1/runs/{self.run_context.run_id}/traces/{self.trace_id}/finish",
            payload,
        )


class RunContext:
    def __init__(self, client, run_id):
        self.client = client
        self.run_id = run_id
        self.finished = False

        self.input_tokens = 0
        self.output_tokens = 0
        self.estimated_cost = 0.0

        self.llm_calls = 0
        self.tool_calls = 0
        self.steps = 0
        self.retries = 0

    def record_usage(self, input_tokens=0, output_tokens=0, cost=0.0):
        if input_tokens < 0 or output_tokens < 0 or cost < 0:
            raise ValueError("Usage values cannot be negative")

        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.estimated_cost += cost

    def record_retry(self):
        self.retries += 1

    @contextmanager
    def trace(
        self,
        name,
        trace_type="custom",
        provider=None,
        model_name=None,
        tool_name=None,
        input_data=None,
        metadata=None,
        parent_trace_id=None,
    ):
        trace_id = str(uuid.uuid4())

        self.client.request(
            "POST",
            f"/api/v1/runs/{self.run_id}/traces/",
            {
                "external_trace_id": trace_id,
                "parent_trace_id": parent_trace_id,
                "name": name,
                "trace_type": trace_type,
                "provider": provider,
                "model_name": model_name,
                "tool_name": tool_name,
                "input_data": input_data,
                "metadata": metadata or {},
            },
        )

        trace_context = TraceContext(
            run_context=self,
            trace_id=trace_id,
            trace_type=trace_type,
        )

        started = time.perf_counter()

        try:
            yield trace_context

        except Exception as exc:
            try:
                trace_context.finish(
                    status="error",
                    error_type=type(exc).__name__,
                    error_message=str(exc),
                )
            except Exception:
                # Do not replace the original agent exception.
                pass

            raise

        else:
            trace_context.finish(status="success")

        finally:
            self.steps += 1

            if trace_type == "llm":
                self.llm_calls += 1
            elif trace_type == "tool":
                self.tool_calls += 1

    def log(self, event_type, message, severity="info", payload=None):
        return self.client.request(
            "POST",
            f"/api/v1/runs/{self.run_id}/events/",
            {
                "event_type": event_type,
                "message": message,
                "severity": severity,
                "payload": payload or {},
            },
        )

    def finish(
        self,
        status="success",
        error_type=None,
        error_message=None,
        task_completed=None,
        timed_out=False,
    ):
        if self.finished:
            return

        result = self.client.request(
            "POST",
            f"/api/v1/runs/{self.run_id}/finish",
            {
                "status": status,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "llm_call_count": self.llm_calls,
                "tool_call_count": self.tool_calls,
                "step_count": self.steps,
                "retry_count": self.retries,
                "estimated_cost": self.estimated_cost,
                "task_completed": task_completed,
                "timed_out": timed_out,
                "error_type": error_type,
                "error_message": error_message,
            },
        )

        self.finished = True
        return result
