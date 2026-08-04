// Outage screen shown when Deezer API or backend fails completely.
export default function OutageScreen({ error, onRetry }) {
  return (
    <main className="outage fade-in">
      <div className="outage-icon">⚡</div>
      <h1 className="outage-title">Connection Issue</h1>
      <p className="outage-message">
        {error || "The music metadata provider is currently unreachable. Please check your network connection and try again later."}
      </p>
      <button className="btn-primary outage-btn" onClick={onRetry}>
        Try Again
      </button>
    </main>
  )
}
