const levelColors = {
  info: "#94a3b8",
  success: "#4ade80",
  warning: "#fbbf24",
  error: "#f87171",
};

export default function ProgressFeed({ events, isRunning }) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Live Progress</h2>
        {isRunning && <span className="badge running">Running</span>}
      </div>
      <div className="feed">
        {events.length === 0 ? (
          <p className="muted">Progress updates will appear here when the workflow runs.</p>
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
    </section>
  );
}
