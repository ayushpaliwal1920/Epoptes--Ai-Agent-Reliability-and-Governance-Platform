from fastapi import FastAPI

from .api import (
    auth,
    agents,
    runs,
    traces,
    events,
    metrics,
    scopes,
    security,
)

app = FastAPI(
    title="AgentGuard",
    description=(
        "AI Agent Reliability and Governance Platform"
    ),
    version="0.2.0",
)


# M1 routes
app.include_router(auth.router)
app.include_router(agents.router)


# M2 routes
app.include_router(runs.router)
app.include_router(traces.router)
app.include_router(events.router)
app.include_router(metrics.router)


app.include_router(scopes.router)
app.include_router(security.router)

@app.get("/")
def root():
    return {
        "name": "AgentGuard",
        "version": "0.2.0",
        "status": "running",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
    }