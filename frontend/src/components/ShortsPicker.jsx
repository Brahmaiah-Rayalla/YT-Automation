export default function ShortsPicker({
  shorts,
  selectedShortUrl,
  onSelect,
  isLoading,
  handle,
}) {
  if (isLoading) {
    return (
      <section className="panel">
        <div className="panel-header">
          <h2>Recent Shorts</h2>
        </div>
        <p className="hint">Loading recent Shorts for {handle}...</p>
      </section>
    );
  }

  if (!shorts.length) {
    return null;
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Recent Shorts</h2>
        <span className="muted">{shorts.length} available</span>
      </div>
      <p className="hint">Select the Short you want each account to view and like.</p>
      <div className="shorts-grid">
        {shorts.map((short) => {
          const isSelected = selectedShortUrl === short.url;
          return (
            <button
              key={short.video_id}
              type="button"
              className={`short-card ${isSelected ? "selected" : ""}`}
              onClick={() => onSelect(short)}
            >
              <div className="short-thumb-wrap">
                {short.thumbnail_url ? (
                  <img src={short.thumbnail_url} alt={short.title} className="short-thumb" />
                ) : (
                  <div className="short-thumb placeholder">Short</div>
                )}
                {isSelected && <span className="short-selected-badge">Selected</span>}
              </div>
              <div className="short-meta">
                <p className="short-title">{short.title}</p>
                <p className="short-id">{short.video_id}</p>
              </div>
            </button>
          );
        })}
      </div>
    </section>
  );
}
