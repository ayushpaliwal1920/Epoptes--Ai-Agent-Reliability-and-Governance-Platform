import { useEffect, useMemo, useState } from "react";
import {
  createAgent,
  deactivateAgent,
  getAgentRuns,
  listAgents,
  listSecurityEvents,
  login,
  register,
  rotateAgentKey,
} from "./services/api";
import Observability from "./pages/Observability";
import RunTable from "../components/observability/RunTable";

const TOKEN_STORAGE_KEY = "agentguard.token";
const KEYS_STORAGE_KEY = "agentguard.agent-keys";
const SELECTED_AGENT_KEY = "agentguard.selected-agent";

const NAV_ITEMS = [
  { id: "overview", label: "Overview", icon: "overview" },
  { id: "agents", label: "Agents", icon: "agents" },
  { id: "runs", label: "Runs", icon: "runs" },
  { id: "security", label: "Security", icon: "security" },
];

function readStoredKeys() {
  const raw = sessionStorage.getItem(KEYS_STORAGE_KEY);
  if (!raw) return {};

  try {
    return JSON.parse(raw);
  } catch (error) {
    console.error("Could not read saved agent keys.", error);
    sessionStorage.removeItem(KEYS_STORAGE_KEY);
    return {};
  }
}

function App() {
  const [token, setToken] = useState(
    () => sessionStorage.getItem(TOKEN_STORAGE_KEY) || "",
  );
  const [agentReload, setAgentReload] = useState(0);
  const [agents, setAgents] = useState([]);
  const [agentsLoading, setAgentsLoading] = useState(false);
  const [agentKeys, setAgentKeys] = useState(readStoredKeys);
  const [selectedAgentId, setSelectedAgentId] = useState(
    () => sessionStorage.getItem(SELECTED_AGENT_KEY) || "",
  );
  const [activePage, setActivePage] = useState("overview");
  const [authMessage, setAuthMessage] = useState("");
  const [appMessage, setAppMessage] = useState("");
  const [isKeyModalOpen, setIsKeyModalOpen] = useState(false);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [oneTimeKey, setOneTimeKey] = useState(null);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  const selectedAgent = useMemo(
    () => agents.find((agent) => String(agent.id) === selectedAgentId),
    [agents, selectedAgentId],
  );
  const activeAgents = useMemo(
    () => agents.filter((agent) => agent.is_active),
    [agents],
  );
  const selectedAgentKey = agentKeys[selectedAgentId] || "";

  useEffect(() => {
    if (!token) {
      setAgents([]);
      return undefined;
    }

    const controller = new AbortController();
    setAgentsLoading(true);
    setAppMessage("");

    listAgents(token, controller.signal)
      .then((result) => {
        setAgents(result);
        const selectedExists = result.some(
          (agent) => String(agent.id) === selectedAgentId && agent.is_active,
        );
        if (!selectedExists) {
          const firstActiveAgent = result.find((agent) => agent.is_active);
          setSelectedAgentId(firstActiveAgent ? String(firstActiveAgent.id) : "");
        }
      })
      .catch((error) => {
        if (error.name === "AbortError") return;
        if (error.status === 401) {
          signOut();
          setAppMessage("Your session expired. Please sign in again.");
          return;
        }
        setAppMessage(error.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setAgentsLoading(false);
      });

    return () => controller.abort();
  }, [token, agentReload]);

  useEffect(() => {
    sessionStorage.setItem(KEYS_STORAGE_KEY, JSON.stringify(agentKeys));
  }, [agentKeys]);

  useEffect(() => {
    if (selectedAgentId) {
      sessionStorage.setItem(SELECTED_AGENT_KEY, selectedAgentId);
    } else {
      sessionStorage.removeItem(SELECTED_AGENT_KEY);
    }
  }, [selectedAgentId]);

  function signOut() {
    sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    sessionStorage.removeItem(KEYS_STORAGE_KEY);
    sessionStorage.removeItem(SELECTED_AGENT_KEY);
    setToken("");
    setAgentKeys({});
    setSelectedAgentId("");
    setActivePage("overview");
    setOneTimeKey(null);
  }

  function handleAuthenticated(accessToken) {
    sessionStorage.setItem(TOKEN_STORAGE_KEY, accessToken);
    setToken(accessToken);
    setAuthMessage("");
  }

  function saveAgentKey(agentId, key) {
    setAgentKeys((current) => ({ ...current, [agentId]: key.trim() }));
  }

  async function handleCreateAgent(details) {
    const result = await createAgent(token, details);
    const agentId = String(result.agent.id);
    setAgents((current) => [result.agent, ...current]);
    saveAgentKey(agentId, result.api_key);
    setSelectedAgentId(agentId);
    setActivePage("agents");
    setOneTimeKey({
      agentName: result.agent.name,
      apiKey: result.api_key,
      message: "This key is shown once. Copy it now and store it securely.",
    });
    setIsCreateModalOpen(false);
  }

  async function handleRotateKey(agent) {
    const result = await rotateAgentKey(token, agent.id);
    saveAgentKey(String(agent.id), result.api_key);
    setOneTimeKey({
      agentName: agent.name,
      apiKey: result.api_key,
      message: result.message,
    });
  }

  async function handleDeactivate(agent) {
    await deactivateAgent(token, agent.id);
    setAgents((current) =>
      current.map((item) =>
        item.id === agent.id ? { ...item, is_active: false } : item,
      ),
    );
    setAgentKeys((current) => {
      const next = { ...current };
      delete next[String(agent.id)];
      return next;
    });
    if (selectedAgentId === String(agent.id)) {
      const nextAgent = agents.find(
        (item) => item.id !== agent.id && item.is_active,
      );
      setSelectedAgentId(nextAgent ? String(nextAgent.id) : "");
    }
    setAppMessage(`${agent.name} was deactivated and its keys were revoked.`);
  }

  if (!token) {
    return (
      <AuthScreen
        initialMessage={appMessage}
        message={authMessage}
        onMessage={setAuthMessage}
        onAuthenticated={handleAuthenticated}
      />
    );
  }

  return (
    <div className="app-shell">
      {mobileNavOpen && (
        <button
          className="mobile-nav-backdrop"
          aria-label="Close navigation"
          onClick={() => setMobileNavOpen(false)}
        />
      )}
      <aside className={`sidebar ${mobileNavOpen ? "sidebar-open" : ""}`}>
        <div className="brand-lockup">
          <div className="brand-mark">
            <BrandMark />
          </div>
          <div>
            <span className="brand-name">agentguard</span>
            <span className="brand-caption">CONTROL PLANE</span>
          </div>
          <button
            className="icon-button sidebar-close"
            aria-label="Close navigation"
            onClick={() => setMobileNavOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>

        <div className="workspace-switcher">
          <div className="workspace-avatar">A</div>
          <div className="workspace-copy">
            <strong>Workspace</strong>
            <span>Agent operations</span>
          </div>
          <Icon name="chevron" />
        </div>

        <nav className="main-nav" aria-label="Main navigation">
          <span className="nav-section-label">WORKSPACE</span>
          {NAV_ITEMS.map((item) => (
            <button
              className={`nav-item ${activePage === item.id ? "nav-item-active" : ""}`}
              key={item.id}
              onClick={() => {
                setActivePage(item.id);
                setMobileNavOpen(false);
              }}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
              {item.id === "agents" && agents.length > 0 && (
                <span className="nav-count">{agents.length}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <div className="system-status">
            <span className="sidebar-status-mark" />
            <span>Agent operations</span>
          </div>
          <button className="profile-button" onClick={signOut}>
            <div className="profile-avatar">AG</div>
            <div className="profile-copy">
              <strong>Administrator</strong>
              <span>Sign out</span>
            </div>
            <Icon name="logout" />
          </button>
        </div>
      </aside>

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-title">
            <button
              className="icon-button mobile-menu-button"
              aria-label="Open navigation"
              onClick={() => setMobileNavOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <div className="breadcrumbs">
              <span>AgentGuard</span>
              <Icon name="breadcrumb" />
              <strong>{pageTitle(activePage)}</strong>
            </div>
          </div>

          <div className="topbar-actions">
            <label className="agent-select-wrap">
              <span className="sr-only">Selected agent</span>
              <span className="agent-select-icon"><Icon name="agents" /></span>
              <select
                value={selectedAgentId}
                onChange={(event) => setSelectedAgentId(event.target.value)}
                disabled={activeAgents.length === 0}
                aria-label="Select agent"
              >
                {activeAgents.length === 0 && <option value="">No active agents</option>}
                {activeAgents.map((agent) => (
                  <option value={agent.id} key={agent.id}>{agent.name}</option>
                ))}
              </select>
              <Icon name="chevron" />
            </label>
            <button
              className={`key-status-button ${selectedAgentKey ? "key-connected" : ""}`}
              onClick={() => setIsKeyModalOpen(true)}
              disabled={!selectedAgent}
            >
              <Icon name="key" />
              <span>{selectedAgentKey ? "Agent connected" : "Connect key"}</span>
              <span className="key-status-dot" />
            </button>
            <button
              className="icon-button refresh-button"
              title="Refresh agents"
              aria-label="Refresh agents"
              onClick={() => setAgentReload((current) => current + 1)}
            >
              <Icon name="refresh" />
            </button>
          </div>
        </header>

        <div className="page-content">
          {appMessage && (
            <div className="notice-banner" role="status">
              <span>{appMessage}</span>
              <button onClick={() => setAppMessage("")} aria-label="Dismiss message">
                <Icon name="close" />
              </button>
            </div>
          )}

          {activePage === "overview" && (
            <OverviewPage
              agent={selectedAgent}
              apiKey={selectedAgentKey}
              loading={agentsLoading}
              onConnect={() => setIsKeyModalOpen(true)}
              onGoToAgents={() => setActivePage("agents")}
            />
          )}
          {activePage === "agents" && (
            <AgentsPage
              agents={agents}
              loading={agentsLoading}
              onCreate={() => setIsCreateModalOpen(true)}
              onRotate={handleRotateKey}
              onDeactivate={handleDeactivate}
              onConnect={(agent) => {
                setSelectedAgentId(String(agent.id));
                setIsKeyModalOpen(true);
              }}
              onError={setAppMessage}
            />
          )}
          {activePage === "runs" && (
            <RunsPage
              apiKey={selectedAgentKey}
              agent={selectedAgent}
              onConnect={() => setIsKeyModalOpen(true)}
            />
          )}
          {activePage === "security" && <SecurityPage token={token} />}
        </div>
      </main>

      {isKeyModalOpen && selectedAgent && (
        <AgentKeyModal
          agent={selectedAgent}
          initialKey={selectedAgentKey}
          onClose={() => setIsKeyModalOpen(false)}
          onSave={(key) => {
            saveAgentKey(selectedAgentId, key);
            setIsKeyModalOpen(false);
            setAppMessage("Agent key saved for this browser session.");
          }}
        />
      )}
      {isCreateModalOpen && (
        <CreateAgentModal
          onClose={() => setIsCreateModalOpen(false)}
          onCreate={handleCreateAgent}
        />
      )}
      {oneTimeKey && (
        <OneTimeKeyModal
          data={oneTimeKey}
          onClose={() => setOneTimeKey(null)}
        />
      )}
    </div>
  );
}

function AuthScreen({ initialMessage, message, onMessage, onAuthenticated }) {
  const [mode, setMode] = useState("login");
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({
    organization_name: "",
    email: "",
    password: "",
  });

  async function submit(event) {
    event.preventDefault();
    onMessage("");
    setBusy(true);
    try {
      if (mode === "register") {
        await register({
          organization_name: form.organization_name,
          email: form.email,
          password: form.password,
        });
      }
      const result = await login({
        email: form.email,
        password: form.password,
      });
      onAuthenticated(result.access_token);
    } catch (error) {
      onMessage(error.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-decoration auth-decoration-one" />
      <div className="auth-decoration auth-decoration-two" />
      <div className="auth-brand">
        <div className="brand-mark"><BrandMark /></div>
        <span className="brand-name">agentguard</span>
      </div>
      <div className="auth-layout">
        <section className="auth-story">
          <div className="eyebrow"><span className="live-dot" /> THE CONTROL PLANE FOR AI</div>
          <h1>Build with agents.<br /><span>Stay in control.</span></h1>
          <p>
            One calm place to see what your agents are doing, how they perform,
            and where they need guardrails.
          </p>
          <div className="auth-proof">
            <div className="proof-avatars"><span>AI</span><span>AG</span><span>+</span></div>
            <span>Observability and governance, together.</span>
          </div>
          <div className="auth-orbit auth-orbit-a" />
          <div className="auth-orbit auth-orbit-b" />
        </section>

        <section className="auth-card">
          <div className="auth-card-heading">
            <span className="auth-card-kicker">{mode === "login" ? "WELCOME BACK" : "GET STARTED"}</span>
            <h2>{mode === "login" ? "Sign in to your workspace" : "Create your workspace"}</h2>
            <p>
              {mode === "login"
                ? "Enter your details to continue to AgentGuard."
                : "Set up your organization and start protecting your agents."}
            </p>
          </div>

          {(message || initialMessage) && (
            <div className="form-alert" role="alert">{message || initialMessage}</div>
          )}

          <form onSubmit={submit} className="auth-form">
            {mode === "register" && (
              <label className="field">
                <span>Organization name</span>
                <input
                  autoComplete="organization"
                  required
                  minLength={2}
                  value={form.organization_name}
                  onChange={(event) => setForm({ ...form, organization_name: event.target.value })}
                  placeholder="Acme AI"
                />
              </label>
            )}
            <label className="field">
              <span>Work email</span>
              <input
                type="email"
                autoComplete="email"
                required
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                placeholder="you@company.com"
              />
            </label>
            <label className="field">
              <span>Password</span>
              <input
                type="password"
                autoComplete={mode === "login" ? "current-password" : "new-password"}
                required
                minLength={mode === "register" ? 8 : undefined}
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                placeholder="Enter your password"
              />
            </label>
            <button className="button button-primary auth-submit" disabled={busy}>
              {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create workspace"}
              {!busy && <Icon name="arrow" />}
            </button>
          </form>

          <div className="auth-toggle">
            {mode === "login" ? "New to AgentGuard?" : "Already have a workspace?"}
            <button
              type="button"
              onClick={() => {
                setMode(mode === "login" ? "register" : "login");
                onMessage("");
              }}
            >
              {mode === "login" ? "Create an account" : "Sign in"}
            </button>
          </div>
          <div className="auth-secure"><Icon name="lock" /> Your workspace is private and encrypted.</div>
        </section>
      </div>
      <div className="auth-footer"><span>AGENTGUARD</span><span>RESPONSIBLE AI, BUILT IN.</span></div>
    </div>
  );
}

function OverviewPage({ agent, apiKey, loading, onConnect, onGoToAgents }) {
  const [recentRuns, setRecentRuns] = useState([]);
  const [runsError, setRunsError] = useState("");

  useEffect(() => {
    if (!apiKey) {
      setRecentRuns([]);
      setRunsError("");
      return undefined;
    }
    const controller = new AbortController();
    getAgentRuns(apiKey, controller.signal)
      .then((data) => {
        setRecentRuns((data.runs || []).slice(0, 5));
        setRunsError("");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setRunsError(error.message);
      });
    return () => controller.abort();
  }, [apiKey]);

  return (
    <div className="page-stack">
      <div className="page-heading overview-heading">
        <div>
          <span className="eyebrow page-eyebrow">YOUR AI OPERATIONS, AT A GLANCE</span>
          <h1>Good to see you<span className="heading-period">.</span></h1>
          <p>
            {agent
              ? `Here’s what’s happening with ${agent.name}.`
              : "Connect an agent to start seeing what’s happening across your AI operations."}
          </p>
        </div>
        <div className="heading-actions">
          <span className="updated-label"><span className="workspace-status-mark" /> Workspace overview</span>
          <button className="button button-dark" onClick={onGoToAgents}>
            <Icon name="plus" /> Add agent
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingPanel label="Loading your workspace…" />
      ) : !agent ? (
        <EmptyState
          icon="agents"
          title="Your workspace is ready"
          description="Register your first agent to start tracking runs, usage, and security events."
          action={<button className="button button-primary" onClick={onGoToAgents}><Icon name="plus" /> Register an agent</button>}
        />
      ) : !apiKey ? (
        <div className="connect-banner">
          <div className="connect-banner-icon"><Icon name="key" /></div>
          <div className="connect-banner-copy">
            <strong>Connect {agent.name} to see live metrics</strong>
            <span>Paste the agent API key created with your agent. Keys are kept in this browser session only.</span>
          </div>
          <button className="button button-primary" onClick={onConnect}>Connect agent <Icon name="arrow" /></button>
        </div>
      ) : null}

      {agent && apiKey && (
        <>
          <Observability
            apiKey={apiKey}
            selectedAgent={agent.name}
            onConnect={onConnect}
          />
          {runsError ? (
            <div className="inline-error" role="alert">{runsError}</div>
          ) : (
            <RunTable runs={recentRuns} />
          )}
        </>
      )}
    </div>
  );
}

function AgentsPage({ agents, loading, onCreate, onRotate, onDeactivate, onConnect, onError }) {
  const [workingId, setWorkingId] = useState("");

  async function runAction(agent, action) {
    onError("");
    setWorkingId(String(agent.id));
    try {
      await action(agent);
    } catch (error) {
      onError(error.message);
    } finally {
      setWorkingId("");
    }
  }

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow page-eyebrow">YOUR AGENT FLEET</span>
          <h1>Agents<span className="heading-period">.</span></h1>
          <p>Register agents, manage credentials, and keep every integration in view.</p>
        </div>
        <button className="button button-dark" onClick={onCreate}><Icon name="plus" /> Register agent</button>
      </div>

      <div className="stat-strip">
        <div><span className="stat-strip-icon"><Icon name="agents" /></span><span><strong>{agents.length}</strong><small>Total agents</small></span></div>
        <div><span className="stat-strip-icon stat-green"><Icon name="check" /></span><span><strong>{agents.filter((agent) => agent.is_active).length}</strong><small>Active</small></span></div>
        <div><span className="stat-strip-icon stat-muted"><Icon name="pause" /></span><span><strong>{agents.filter((agent) => !agent.is_active).length}</strong><small>Inactive</small></span></div>
      </div>

      <section className="surface-card">
        <div className="section-heading section-heading-padded">
          <div>
            <h2>All agents</h2>
            <p>Manage your registered AI agents and their access keys.</p>
          </div>
          <span className="table-count">{agents.length} {agents.length === 1 ? "agent" : "agents"}</span>
        </div>
        {loading ? <LoadingPanel label="Loading agents…" compact /> : agents.length === 0 ? (
          <EmptyState
            icon="agents"
            title="No agents yet"
            description="Register an agent to issue its first API key and begin monitoring activity."
            action={<button className="button button-primary" onClick={onCreate}><Icon name="plus" /> Register your first agent</button>}
          />
        ) : (
          <div className="table-scroll">
            <table className="run-table agent-table">
              <thead>
                <tr><th>Agent</th><th>Framework</th><th>Environment</th><th>Risk</th><th>Status</th><th>Actions</th></tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <tr key={agent.id}>
                    <td>
                      <div className="agent-name-cell">
                        <div className={`agent-avatar agent-avatar-${agent.id % 5}`}>{(agent.name || "A").slice(0, 1).toUpperCase()}</div>
                        <div><strong>{agent.name}</strong><span className="table-subtext">{agent.owner || agent.description || `Agent #${agent.id}`}</span></div>
                      </div>
                    </td>
                    <td><span className="framework-tag">{agent.framework || "custom"}</span></td>
                    <td><span className="environment-tag">{agent.environment || "development"}</span></td>
                    <td><span className={`risk-label risk-${String(agent.risk_level || "medium").toLowerCase()}`}>{agent.risk_level || "medium"}</span></td>
                    <td><span className={`status-badge ${agent.is_active ? "status-success" : "status-inactive"}`}><span className="status-dot" />{agent.is_active ? "Active" : "Inactive"}</span></td>
                    <td>
                      <div className="table-actions">
                        {agent.is_active && <button className="text-action" onClick={() => onConnect(agent)} title="Connect or replace this agent's key"><Icon name="key" /> Key</button>}
                        {agent.is_active && (
                          <button
                            className="icon-button table-icon-button"
                            title="Rotate API key"
                            aria-label={`Rotate API key for ${agent.name}`}
                            disabled={workingId === String(agent.id)}
                            onClick={() => {
                              if (window.confirm(`Rotate the API key for ${agent.name}? Its current key will stop working.`)) {
                                runAction(agent, onRotate);
                              }
                            }}
                          >
                            <Icon name="refresh" />
                          </button>
                        )}
                        {agent.is_active && (
                          <button
                            className="icon-button table-icon-button danger-icon"
                            title="Deactivate agent"
                            aria-label={`Deactivate ${agent.name}`}
                            disabled={workingId === String(agent.id)}
                            onClick={() => {
                              if (window.confirm(`Deactivate ${agent.name}? Its API keys will be revoked.`)) {
                                runAction(agent, onDeactivate);
                              }
                            }}
                          >
                            <Icon name="ban" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
      <p className="privacy-note"><Icon name="lock" /> Agent keys are only available when created or rotated. This browser keeps keys in session storage.</p>
    </div>
  );
}

function RunsPage({ apiKey, agent, onConnect }) {
  const [runs, setRuns] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!apiKey) {
      setRuns([]);
      return undefined;
    }
    const controller = new AbortController();
    setLoading(true);
    setError("");
    getAgentRuns(apiKey, controller.signal)
      .then((result) => setRuns(result.runs || []))
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [apiKey]);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow page-eyebrow">EXECUTION HISTORY</span>
          <h1>Runs<span className="heading-period">.</span></h1>
          <p>Review run health, latency, token usage, and estimated cost.</p>
        </div>
        {agent && <span className="selected-agent-pill"><span className="live-dot" />{agent.name}</span>}
      </div>
      {!agent ? (
        <EmptyState icon="agents" title="No agent selected" description="Register an agent to start collecting run data." />
      ) : !apiKey ? (
        <EmptyState icon="key" title="Connect your agent" description={`Add the API key for ${agent.name} to load its run history.`} action={<button className="button button-primary" onClick={onConnect}>Connect agent</button>} />
      ) : loading ? (
        <LoadingPanel label="Loading run history…" />
      ) : error ? (
        <div className="inline-error" role="alert">{error}</div>
      ) : (
        <RunTable runs={runs} />
      )}
    </div>
  );
}

function SecurityPage({ token }) {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [severity, setSeverity] = useState("all");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    listSecurityEvents(token, controller.signal)
      .then((result) => setEvents(result))
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [token]);

  const visibleEvents = severity === "all"
    ? events
    : events.filter((event) => event.severity?.toLowerCase() === severity);

  return (
    <div className="page-stack">
      <div className="page-heading">
        <div>
          <span className="eyebrow page-eyebrow">GOVERNANCE &amp; SAFETY</span>
          <h1>Security events<span className="heading-period">.</span></h1>
          <p>Review detections and policy events across your organization.</p>
        </div>
        <label className="filter-select">
          <span>Severity</span>
          <select value={severity} onChange={(event) => setSeverity(event.target.value)}>
            <option value="all">All severities</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
          <Icon name="chevron" />
        </label>
      </div>
      <div className="security-summary">
        <div><span className="security-summary-icon"><Icon name="shield" /></span><strong>{events.length}</strong><span>Latest events</span></div>
        <div><span className="severity-mark severity-high" /><strong>{events.filter((event) => ["high", "critical"].includes(event.severity?.toLowerCase())).length}</strong><span>High priority</span></div>
        <div><span className="security-summary-icon security-summary-safe"><Icon name="check" /></span><strong>{events.filter((event) => event.blocked).length}</strong><span>Blocked</span></div>
      </div>
      <section className="surface-card">
        <div className="section-heading section-heading-padded">
          <div><h2>Event log</h2><p>Latest security activity from your organization.</p></div>
          <span className="table-count">{visibleEvents.length} events</span>
        </div>
        {loading ? <LoadingPanel label="Loading security events…" compact /> : error ? (
          <div className="inline-error security-error" role="alert">{error}</div>
        ) : visibleEvents.length === 0 ? (
          <EmptyState icon="shield" title="All clear" description={events.length === 0 ? "No security events have been recorded yet." : "No events match this severity filter."} />
        ) : (
          <div className="event-list">
            {visibleEvents.map((event) => (
              <article className="event-row" key={event.id}>
                <div className={`event-indicator event-${String(event.severity).toLowerCase()}`}><Icon name="shield" /></div>
                <div className="event-copy">
                  <div className="event-title-row">
                    <strong>{event.event_type?.replaceAll("_", " ") || "Security event"}</strong>
                    <span className={`severity-badge severity-${String(event.severity).toLowerCase()}`}>{event.severity}</span>
                  </div>
                  <p>{event.description || "No additional details were provided."}</p>
                  <span className="event-meta">Agent #{event.agent_id}{event.run_id ? ` · Run #${event.run_id}` : ""} · {formatDateTime(event.created_at)}</span>
                </div>
                {event.blocked && <span className="blocked-tag"><Icon name="check" /> Blocked</span>}
              </article>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function AgentKeyModal({ agent, initialKey, onClose, onSave }) {
  const [key, setKey] = useState(initialKey);
  const [showKey, setShowKey] = useState(false);

  function submit(event) {
    event.preventDefault();
    if (key.trim()) onSave(key);
  }

  return (
    <Modal onClose={onClose} labelledBy="key-modal-title">
      <div className="modal-icon"><Icon name="key" /></div>
      <span className="eyebrow page-eyebrow">AGENT CREDENTIAL</span>
      <h2 id="key-modal-title">Connect {agent.name}</h2>
      <p className="modal-description">Use the API key issued to this agent to load its run and usage metrics.</p>
      <form onSubmit={submit} className="modal-form">
        <label className="field">
          <span>Agent API key</span>
          <div className="password-input-wrap">
            <input
              autoFocus
              type={showKey ? "text" : "password"}
              value={key}
              onChange={(event) => setKey(event.target.value)}
              placeholder="Paste your agent key"
              required
            />
            <button type="button" className="password-toggle" onClick={() => setShowKey((value) => !value)}>
              {showKey ? "Hide" : "Show"}
            </button>
          </div>
        </label>
        <div className="modal-note"><Icon name="lock" /> Stored only for this browser session.</div>
        <div className="modal-actions">
          <button type="button" className="button button-quiet" onClick={onClose}>Cancel</button>
          <button className="button button-primary">Save key <Icon name="arrow" /></button>
        </div>
      </form>
    </Modal>
  );
}

function CreateAgentModal({ onClose, onCreate }) {
  const [form, setForm] = useState({
    name: "",
    description: "",
    framework: "custom",
    integration_type: "sdk",
    environment: "development",
    risk_level: "medium",
    owner: "",
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setBusy(true);
    try {
      await onCreate(form);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal onClose={onClose} labelledBy="create-agent-title" wide>
      <div className="modal-icon"><Icon name="agents" /></div>
      <span className="eyebrow page-eyebrow">NEW INTEGRATION</span>
      <h2 id="create-agent-title">Register an agent</h2>
      <p className="modal-description">Create an identity for your agent. We’ll issue its API key after registration.</p>
      {error && <div className="form-alert" role="alert">{error}</div>}
      <form onSubmit={submit} className="modal-form">
        <div className="form-grid">
          <label className="field field-span-two">
            <span>Agent name</span>
            <input required minLength={2} maxLength={150} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Customer support assistant" />
          </label>
          <label className="field">
            <span>Framework</span>
            <select value={form.framework} onChange={(event) => setForm({ ...form, framework: event.target.value })}>
              <option value="custom">Custom</option><option value="langchain">LangChain</option><option value="llamaindex">LlamaIndex</option><option value="crewai">CrewAI</option><option value="autogen">AutoGen</option><option value="openai">OpenAI</option>
            </select>
          </label>
          <label className="field">
            <span>Environment</span>
            <select value={form.environment} onChange={(event) => setForm({ ...form, environment: event.target.value })}>
              <option value="development">Development</option><option value="staging">Staging</option><option value="production">Production</option>
            </select>
          </label>
          <label className="field">
            <span>Risk level</span>
            <select value={form.risk_level} onChange={(event) => setForm({ ...form, risk_level: event.target.value })}>
              <option value="low">Low</option><option value="medium">Medium</option><option value="high">High</option><option value="critical">Critical</option>
            </select>
          </label>
          <label className="field">
            <span>Owner <small>Optional</small></span>
            <input maxLength={150} value={form.owner} onChange={(event) => setForm({ ...form, owner: event.target.value })} placeholder="Team or person" />
          </label>
          <label className="field field-span-two">
            <span>Description <small>Optional</small></span>
            <textarea rows="3" value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="What does this agent do?" />
          </label>
        </div>
        <div className="modal-actions">
          <button type="button" className="button button-quiet" onClick={onClose}>Cancel</button>
          <button className="button button-primary" disabled={busy}>{busy ? "Registering…" : "Register agent"} {!busy && <Icon name="arrow" />}</button>
        </div>
      </form>
    </Modal>
  );
}

function OneTimeKeyModal({ data, onClose }) {
  const [copied, setCopied] = useState(false);
  const [copyError, setCopyError] = useState("");
  async function copyKey() {
    try {
      await navigator.clipboard.writeText(data.apiKey);
      setCopied(true);
      setCopyError("");
    } catch (error) {
      console.error("Could not copy the agent key.", error);
      setCopyError("Copy was blocked by the browser. Select and copy the key above.");
    }
  }

  return (
    <Modal onClose={onClose} labelledBy="one-time-key-title">
      <div className="modal-icon modal-icon-success"><Icon name="check" /></div>
      <span className="eyebrow page-eyebrow">SAVE THIS CREDENTIAL</span>
      <h2 id="one-time-key-title">{data.agentName} is ready</h2>
      <p className="modal-description">{data.message}</p>
      <div className="secret-key-box"><code>{data.apiKey}</code></div>
      {copyError && <div className="form-alert copy-alert" role="alert">{copyError}</div>}
      <div className="modal-actions">
        <button className="button button-quiet" onClick={onClose}>Done</button>
        <button className="button button-primary" onClick={copyKey}><Icon name={copied ? "check" : "copy"} />{copied ? "Copied" : "Copy API key"}</button>
      </div>
    </Modal>
  );
}

function Modal({ children, onClose, labelledBy, wide = false }) {
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className={`modal-card ${wide ? "modal-wide" : ""}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
        <button className="icon-button modal-close" aria-label="Close dialog" onClick={onClose}><Icon name="close" /></button>
        {children}
      </section>
    </div>
  );
}

function LoadingPanel({ label, compact = false }) {
  return (
    <div className={`loading-panel ${compact ? "loading-compact" : ""}`} role="status">
      <span className="spinner" />
      <span>{label}</span>
    </div>
  );
}

function EmptyState({ icon, title, description, action }) {
  return (
    <div className="empty-state">
      <div className="empty-state-icon"><Icon name={icon} /></div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}

function pageTitle(page) {
  return NAV_ITEMS.find((item) => item.id === page)?.label || "Overview";
}

function formatDateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function BrandMark() {
  return (
    <svg viewBox="0 0 32 32" aria-hidden="true">
      <path d="M16 3.5 27 9.8v12.4L16 28.5 5 22.2V9.8L16 3.5Z" />
      <path d="m11 16 3.2 3.2L21.5 12" />
      <circle cx="16" cy="16" r="11.5" />
    </svg>
  );
}

function Icon({ name }) {
  const common = {
    viewBox: "0 0 24 24",
    fill: "none",
    stroke: "currentColor",
    strokeWidth: 1.8,
    strokeLinecap: "round",
    strokeLinejoin: "round",
    "aria-hidden": "true",
  };
  const paths = {
    overview: <><rect x="3.5" y="3.5" width="7" height="7" rx="1.5" /><rect x="13.5" y="3.5" width="7" height="4" rx="1.5" /><rect x="13.5" y="10.5" width="7" height="10" rx="1.5" /><rect x="3.5" y="13.5" width="7" height="7" rx="1.5" /></>,
    agents: <><circle cx="9" cy="8" r="3.5" /><path d="M3 20a6 6 0 0 1 12 0" /><path d="M16 5.2a3.5 3.5 0 0 1 0 6.6M18 14a5.8 5.8 0 0 1 3 5" /></>,
    runs: <><path d="M4 19V5" /><path d="M4 19h17" /><path d="m7 15 4-4 3 2 6-7" /><path d="M16 6h4v4" /></>,
    security: <><path d="M12 3 20 6v5.5c0 4.8-3.1 8-8 9.5-4.9-1.5-8-4.7-8-9.5V6l8-3Z" /><path d="m8.5 12 2.2 2.2 4.8-5" /></>,
    plus: <><path d="M12 5v14M5 12h14" /></>,
    key: <><circle cx="8" cy="15" r="4" /><path d="m11 12 8-8 2 2-2 2 2 2-3 3-2-2-2 2" /></>,
    chevron: <path d="m8 10 4 4 4-4" />,
    breadcrumb: <path d="m9 6 6 6-6 6" />,
    arrow: <><path d="M5 12h14" /><path d="m13 6 6 6-6 6" /></>,
    refresh: <><path d="M20 7v5h-5" /><path d="M4.8 9a7.5 7.5 0 0 1 12.6-2L20 12M4 17v-5h5" /><path d="M19.2 15a7.5 7.5 0 0 1-12.6 2L4 12" /></>,
    lock: <><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 1 1 8 0v3" /><path d="M12 14v3" /></>,
    logout: <><path d="M10 17l5-5-5-5M15 12H3" /><path d="M12 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6" /></>,
    close: <><path d="m18 6-12 12M6 6l12 12" /></>,
    menu: <><path d="M4 7h16M4 12h16M4 17h16" /></>,
    check: <path d="m5 12 4 4L19 6" />,
    pause: <><path d="M8 5v14M16 5v14" /></>,
    ban: <><circle cx="12" cy="12" r="9" /><path d="m5.6 5.6 12.8 12.8" /></>,
    shield: <><path d="M12 3 20 6v5.5c0 4.8-3.1 8-8 9.5-4.9-1.5-8-4.7-8-9.5V6l8-3Z" /><path d="m8.5 12 2.2 2.2 4.8-5" /></>,
    copy: <><rect x="8" y="8" width="12" height="12" rx="2" /><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3" /></>,
  };
  return <svg {...common}>{paths[name] || paths.overview}</svg>;
}

export default App;
