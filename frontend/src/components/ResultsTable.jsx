export default function ResultsTable({ results }) {
  if (!results.length) {
    return null;
  }

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Results</h2>
      </div>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Account Email</th>
              <th>Viewed Short</th>
              <th>Liked?</th>
              <th>Status</th>
              <th>Error</th>
            </tr>
          </thead>
          <tbody>
            {results.map((row) => (
              <tr key={row.email} className={row.error ? "row-error" : ""}>
                <td>{row.email}</td>
                <td className="video-title-cell">
                  {row.video_url ? (
                    <a href={row.video_url} target="_blank" rel="noreferrer">
                      {row.video_title || row.video_url}
                    </a>
                  ) : (
                    row.video_title || "—"
                  )}
                </td>
                <td>
                  <span className={`liked-pill ${row.liked ? "liked-yes" : "liked-no"}`}>
                    {row.liked ? "Yes" : "No"}
                  </span>
                </td>
                <td>
                  <span className={`status-pill status-${row.status}`}>{row.status}</span>
                </td>
                <td className="error-cell">{row.error || "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
