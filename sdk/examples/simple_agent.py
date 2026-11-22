
import os
import time

from agentguard import AgentGuardClient

from agentguard.agent_governance.security import (
    SecurityClient,
    ToolAuthorizationError,
    ToolOutputBlockedError,
)

client = AgentGuardClient(
    api_key=os.environ["AGENTGUARD_API_KEY"],
    base_url="http://127.0.0.1:8000",
)

security = SecurityClient(
    api_key=os.environ["AGENTGUARD_API_KEY"],
    base_url="http://127.0.0.1:8000",
)


def search_tool(query):
    time.sleep(1)

    return {
        "results": [
            "AI agents automate workflows",
            "Agent observability helps debugging",
            "Execution traces improve reliability",
        ]
    }


def generate_response(results):
    time.sleep(1.5)

    return (
        "AI agents automate workflows. "
        "Observability helps monitor their execution."
    )


def main():

    try:
        with client.run(
            "Research Agent",
            metadata={"framework": "custom"},
        ) as run:

            run.log(
                "agent.initialized",
                "Research agent started",
            )

            # Tool execution is governed by AgentGuard.
            tool_response = security.execute_tool(
                tool=search_tool,
                tool_name="get_invoice",
                action="read_invoice",
                resource="invoice_records",
                run_context=run,
                query="AI agent observability",
            )

            results = tool_response["result"]

            with run.trace(
                name="LLM Generation",
                trace_type="llm",
                provider="example",
                model_name="demo-model",
            ) as trace:

                answer = generate_response(results)

                trace.record_usage(
                    input_tokens=500,
                    output_tokens=250,
                    cost=0.002,
                )

            print(answer)

    finally:
        security.close()
        client.close()


if __name__ == "__main__":
    main()
