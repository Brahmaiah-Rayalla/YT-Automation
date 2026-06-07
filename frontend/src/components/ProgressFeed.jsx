const levelColors = {
  info: "#94a3b8",
  success: "#4ade80",
  warning: "#fbbf24",
  error: "#f87171",
};

export default function ProgressFeed({
  events,
  isRunning,
  onRunWorkflow,
  canRunWorkflow,
  selectedShort,
}) {
  return (
    <section className="panel progress-panel">
      <div className="panel-header progress-header">
        <div className="progress-header-text">
          <h2>Live Progress</h2>
          {selectedShort && (
            <p className="muted progress-target">
              Target: {selectedShort.title} ({selectedShort.video_id})
            </p>
          )}
        </div>
        {isRunning && <span className="badge running">Running</span>}
      </div>

      <div className="feed">
        {events.length === 0 ? (
          <p className="muted">
            Progress updates will appear here when the workflow runs.
          </p>
        ) : (
          events.map((event, index) => (
            <div key={`${event.timestamp}-${index}`} className="feed-item">
              <span className="feed-time">
                {new Date(event.timestamp).toLocaleTimeString()}
              </span>
              <span style={{ color: levelColors[event.level] || levelColors.info }}>
                {event.message}
              </span>
            </div>
          ))
        )}
      </div>

      <div className="progress-actions">
        <button
          type="button"
          className="primary-button run-workflow-button"
          onClick={onRunWorkflow}
          disabled={!canRunWorkflow || isRunning}
        >
          {isRunning ? "Workflow Running..." : "Run Workflow"}
        </button>
      </div>
    </section>
  );
}
