const MetricsCards = ({ data }) => {
  if (!data) return null;

  const cards = [
    {
      label: "Total Runs",
      value: data.execution.total_runs,
      detail: `${data.execution.active_runs} currently active`,
      icon: "↗",
    },
    {
      label: "Success Rate",
      value: `${data.execution.success_rate}%`,
      detail: `${data.execution.successful_runs} successful runs`,
      icon: "✓",
    },
    {
      label: "Average latency",
      value: `${data.performance.average_latency_ms} ms`,
      detail: `P95 ${data.performance.p95_latency_ms} ms`,
      icon: "◷",
    },
    {
      label: "Estimated Cost",
      value: `$${Number(data.cost.total_estimated_cost).toFixed(4)}`,
      detail: `${Number(data.usage.total_tokens).toLocaleString()} tokens used`,
      icon: "$",
    },
  ];

  return (
    <div className="metrics-grid overview-metrics">
      {cards.map((card, index) => (
        <div className="metric-card" key={card.label} style={{ "--card-index": index }}>
          <div className="metric-card-top">
            <span className={`metric-icon metric-icon-${index}`}>{card.icon}</span>
            <span className="metric-period">All time</span>
          </div>
          <p className="metric-label">{card.label}</p>
          <h2>{card.value}</h2>
          <span className="metric-detail">{card.detail}</span>
        </div>
      ))}
    </div>
  );
};

export default MetricsCards;