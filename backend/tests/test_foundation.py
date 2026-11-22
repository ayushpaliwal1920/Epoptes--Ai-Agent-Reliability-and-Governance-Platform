
def test_model_metadata_tables_can_be_sorted():
    from backend.app.db import model
    from backend.app.db.database import Base

    tables = Base.metadata.sorted_tables

    assert model.Organization.__table__ in tables
    assert model.Agent.__table__ in tables
    assert model.AgentMetricSnapshot.__table__ in tables


def test_start_run_accepts_run_payload(client):
    from backend.app.core.security import hash_agent_api_key
    from backend.app.db.model import Agent, AgentCredential, Organization

    api_key = "test-agent-key"
    with client.test_db_session() as db:
        organization = Organization(name="Run test organization")
        db.add(organization)
        db.flush()

        agent = Agent(
            organization_id=organization.id,
            name="Run test agent",
            framework="test",
            integration_type="sdk",
            environment="test",
            risk_level="low",
        )
        db.add(agent)
        db.flush()
        db.add(
            AgentCredential(
                agent_id=agent.id,
                key_hash=hash_agent_api_key(api_key),
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/runs/start",
        headers={"X-Agent-Key": api_key},
        json={
            "external_run_id": "test-run",
            "name": "Run signature regression",
            "metadata": {},
        },
    )

    assert response.status_code == 201
    assert response.json()["external_run_id"] == "test-run"


def register_organization(client, name, email):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": name,
            "email": email,
            "password": "Admin@12345"
        }
    )

    assert response.status_code == 201
    return response.json()


def login(client, email):
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": email,
            "password": "Admin@12345"
        }
    )

    assert response.status_code == 200
    return response.json()["access_token"]


def admin_headers(token):
    return {"Authorization": f"Bearer {token}"}


def register_agent(client, token, name):
    response = client.post(
        "/api/v1/agents",
        headers=admin_headers(token),
        json={
            "name": name,
            "description": "Test agent",
            "framework": "LangGraph",
            "integration_type": "sdk",
            "environment": "development",
            "risk_level": "medium",
            "owner": "Testing Team"
        }
    )

    assert response.status_code == 201
    return response.json()


def test_complete_m1_flow(client):
    # 1. Health check
    response = client.get("/health")
    assert response.status_code == 200

    # 2. Organization A registration
    register_organization(
        client,
        "Organization A",
        "admin_a@example.com"
    )

    # 3. Duplicate email must be rejected
    duplicate = client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Duplicate",
            "email": "admin_a@example.com",
            "password": "Admin@12345"
        }
    )
    assert duplicate.status_code == 409

    # 4. Admin A login
    token_a = login(client, "admin_a@example.com")
    headers_a = admin_headers(token_a)

    # 5. Register an agent
    created = register_agent(
        client,
        token_a,
        "Finance Invoice Agent"
    )

    agent = created["agent"]
    old_key = created["api_key"]
    agent_id = agent["id"]

    # 6. List agents
    response = client.get(
        "/api/v1/agents",
        headers=headers_a
    )
    assert response.status_code == 200
    assert len(response.json()) == 1

    # 7. Get agent details
    response = client.get(
        f"/api/v1/agents/{agent_id}",
        headers=headers_a
    )
    assert response.status_code == 200

    # 8. Agent API-key authentication
    response = client.get(
        "/api/v1/agents/me",
        headers={"X-Agent-Key": old_key}
    )
    assert response.status_code == 200

    # 9. Register Organization B
    register_organization(
        client,
        "Organization B",
        "admin_b@example.com"
    )

    token_b = login(client, "admin_b@example.com")
    headers_b = admin_headers(token_b)

    # 10. Organization B must not see Organization A's agent
    response = client.get(
        f"/api/v1/agents/{agent_id}",
        headers=headers_b
    )
    assert response.status_code == 404

    response = client.get(
        "/api/v1/agents",
        headers=headers_b
    )
    assert response.status_code == 200
    assert response.json() == []

    # 11. Rotate the API key
    response = client.post(
        f"/api/v1/agents/{agent_id}/rotate-key",
        headers=headers_a
    )
    assert response.status_code == 200

    new_key = response.json()["api_key"]

    # Old key must no longer work
    response = client.get(
        "/api/v1/agents/me",
        headers={"X-Agent-Key": old_key}
    )
    assert response.status_code == 401

    # New key must work
    response = client.get(
        "/api/v1/agents/me",
        headers={"X-Agent-Key": new_key}
    )
    assert response.status_code == 200

    # 12. Deactivate agent
    response = client.patch(
        f"/api/v1/agents/{agent_id}/deactivate",
        headers=headers_a
    )
    assert response.status_code == 200

    # New key must also fail after deactivation
    response = client.get(
        "/api/v1/agents/me",
        headers={"X-Agent-Key": new_key}
    )
    assert response.status_code == 401

    # 13. Check audit events in the test database
    from backend.app.db.model import AuditEvent

    with client.test_db_session() as db:
        actions = {
            event.action
            for event in db.query(AuditEvent).all()
        }

        assert "organization.registered" in actions
        assert "agent.created" in actions
        assert "agent.key_rotated" in actions
        assert "agent.deactivated" in actions


def test_invalid_access_token_returns_401(client):
    response = client.get(
        "/api/v1/auth/organization",
        headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401


def test_start_run_accepts_run_start_payload(client):
    register_organization(
        client,
        "Run Test Organization",
        "run_test@example.com"
    )
    token = login(client, "run_test@example.com")
    created = register_agent(client, token, "Run Test Agent")

    response = client.post(
        "/api/v1/runs/start",
        headers={"X-Agent-Key": created["api_key"]},
        json={
            "external_run_id": "external-run-1",
            "name": "Regression test run",
            "metadata": {"source": "test"}
        }
    )

    assert response.status_code == 201
    assert response.json()["external_run_id"] == "external-run-1"
    assert response.json()["status"] == "running"
