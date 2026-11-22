import { useEffect, useState } from "react";
import {
  getModelUsage,
  getObservabilityOverview,
  getToolUsage,
} from "../services/observability";
import MetricsCards from "../../components/observability/MetricsCards";

function Observability({ apiKey, selectedAgent, onConnect }) {
  const [overview, setOverview] = useState(null);
  const [models, setModels] = useState([]);
  const [tools, setTools] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!apiKey) {
      setOverview(null);
      setModels([]);
      setTools([]);
      setLoading(false);
      return undefined;
    }

    const controller = new AbortController();
    setLoading(true);
    setError("");

    Promise.all([
      getObservabilityOverview(apiKey, controller.signal),
      getModelUsage(apiKey, controller.signal),
      getToolUsage(apiKey, controller.signal),
    ])
      .then(([overviewData, modelsData, toolsData]) => {
        setOverview(overviewData);
        setModels(modelsData.models || []);
        setTools(toolsData.tools || []);
      })
      .catch((requestError) => {
        if (requestError.name !== "AbortError") setError(requestError.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, [apiKey]);

  if (loading) {
    return (
      <div className="loading-panel dashboard-loading" role="status">
        <span className="spinner" />
        <span>Loading {selectedAgent} metrics…</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error" role="alert">
        <div className="dashboard-error-icon">!</div>
        <div>
          <strong>Couldn’t load agent metrics</strong>
          <span>{error}. Check that this agent’s API key is current.</span>
        </div>
        <button className="button button-quiet" onClick={onConnect}>Update key</button>
      </div>
    );
  }

  if (!overview) return null;

  const performance = overview.performance || {};
  const usage = overview.usage || {};
  const cost = overview.cost || {};
  const reliability = overview.reliability || {};

  return (
    <div className="observability-page">
      <MetricsCards data={overview} />

      <div className="dashboard-grid">
        <section className="surface-card performance-card">
          <div className="section-heading">
            <div>
              <span className="section-kicker">LATENCY</span>
              <h2>Performance</h2>
            </div>
            <span className="chart-caption">Response time</span>
          </div>
          <div className="latency-bars" aria-label="Latency percentiles">
            {[
              ["P50", performance.p50_latency_ms ?? 0],
              ["P95", performance.p95_latency_ms ?? 0],
              ["P99", performance.p99_latency_ms ?? 0],
            ].map(([label, value]) => {
              const max = Math.max(performance.p99_latency_ms || 0, 1);
              return (
                <div className="latency-row" key={label}>
                  <span>{label}</span>
                  <div className="latency-track"><span style={{ width: `${Math.min((value / max) * 100, 100)}%` }} /></div>
                  <strong>{value} ms</strong>
                </div>
              );
            })}
          </div>
          <div className="chart-footnote">Latency percentiles from completed runs</div>
        </section>

        <section className="surface-card reliability-card">
          <div className="section-heading">
            <div>
              <span className="section-kicker">RELIABILITY</span>
              <h2>Run health</h2>
            </div>
            <span className="health-mark"><span className="workspace-status-mark" /> Current metrics</span>
          </div>
          <div className="health-score">
            <div className="health-ring" style={{ "--score": `${overview.execution?.success_rate || 0}%` }}>
              <div><strong>{overview.execution?.success_rate || 0}<small>%</small></strong><span>success rate</span></div>
            </div>
            <div className="health-legend">
              <div><span className="legend-dot legend-success" /><span>Successful</span><strong>{overview.execution?.successful_runs || 0}</strong></div>
              <div><span className="legend-dot legend-error" /><span>Failed</span><strong>{overview.execution?.failed_runs || 0}</strong></div>
              <div><span className="legend-dot legend-active" /><span>Active</span><strong>{overview.execution?.active_runs || 0}</strong></div>
            </div>
          </div>
          <div className="reliability-footer">
            <span>Tool success rate</span><strong>{reliability.tool_success_rate ?? 0}%</strong>
          </div>
        </section>
      </div>

      <div className="section-heading usage-section-heading">
        <div>
          <span className="section-kicker">RESOURCE CONSUMPTION</span>
          <h2>Usage breakdown</h2>
        </div>
      </div>
      <div className="usage-grid">
        <section className="surface-card usage-card">
          <div className="usage-card-heading"><div className="usage-card-icon usage-purple">✳</div><div><h3>Model usage</h3><span>{models.length} {models.length === 1 ? "model" : "models"} detected</span></div></div>
          {models.length === 0 ? <p className="compact-empty">No model calls recorded yet.</p> : (
            <div className="usage-list">
              {models.slice(0, 4).map((model) => (
                <div className="usage-list-row" key={`${model.provider}-${model.model}`}>
                  <div><strong>{model.model || "Unknown model"}</strong><span>{model.provider || "Provider"} · {Number(model.calls || 0).toLocaleString()} calls</span></div>
                  <strong>${Number(model.cost || 0).toFixed(4)}</strong>
                </div>
              ))}
            </div>
          )}
          <div className="usage-card-footer"><span>Total tokens</span><strong>{Number(usage.total_tokens || 0).toLocaleString()}</strong></div>
        </section>

        <section className="surface-card usage-card">
          <div className="usage-card-heading"><div className="usage-card-icon usage-green">⌘</div><div><h3>Tool activity</h3><span>{tools.length} {tools.length === 1 ? "tool" : "tools"} detected</span></div></div>
          {tools.length === 0 ? <p className="compact-empty">No tool calls recorded yet.</p> : (
            <div className="usage-list">
              {tools.slice(0, 4).map((tool) => (
                <div className="usage-list-row" key={tool.tool_name || "unnamed"}>
                  <div><strong>{tool.tool_name || "Unnamed tool"}</strong><span>{Number(tool.calls || 0).toLocaleString()} calls · {tool.average_latency_ms || 0} ms avg</span></div>
                  <span className="tool-success">{tool.success_rate ?? 0}% success</span>
                </div>
              ))}
            </div>
          )}
          <div className="usage-card-footer"><span>LLM calls</span><strong>{Number(usage.llm_calls || 0).toLocaleString()}</strong></div>
        </section>
      </div>
      <div className="overview-footnote">Estimated spend <strong>${Number(cost.total_estimated_cost || 0).toFixed(4)}</strong> across {Number(usage.trace_count || 0).toLocaleString()} traces.</div>
    </div>
  );
}

export default Observability;
