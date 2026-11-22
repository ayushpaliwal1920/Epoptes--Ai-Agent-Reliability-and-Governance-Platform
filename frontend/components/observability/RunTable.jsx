const RunTable = ({ runs = [] }) => {
  return (
    <div className="run-table-container">
      <div className="section-heading">
        <div>
          <h2>Recent runs</h2>
          <p>The latest activity from your connected agent.</p>
        </div>
      </div>
      <div className="table-scroll">
        <table className="run-table">
          <thead>
            <tr>
              <th>Run</th>
              <th>Status</th>
              <th>Started</th>
              <th>Latency</th>
              <th>Tokens</th>
              <th>Cost</th>
            </tr>
          </thead>
          <tbody>
            {runs.map((run) => (
              <tr key={run.id}>
                <td>
                  <strong>{run.name || run.external_run_id || `Run #${run.id}`}</strong>
                  <span className="table-subtext">{run.external_run_id}</span>
                </td>
                <td>
                  <span className={`status-badge status-${run.status}`}>
                    <span className="status-dot" />
                    {run.status}
                  </span>
                </td>
                <td>{formatDate(run.started_at)}</td>
                <td>{run.latency_ms == null ? "—" : `${run.latency_ms} ms`}</td>
                <td>{Number(run.total_tokens || 0).toLocaleString()}</td>
                <td>${Number(run.estimated_cost || 0).toFixed(4)}</td>
              </tr>
            ))}
            {runs.length === 0 && (
              <tr>
                <td colSpan="6" className="empty-table">
                  No runs recorded yet. Start an agent run to see activity here.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

function formatDate(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(new Date(value));
}

export default RunTable;