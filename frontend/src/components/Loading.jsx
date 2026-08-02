// Loading screen shown while the backend fetches, classifies, scores, and
// writes the DJ intro. Reflects the multi-agent pipeline for a bit of delight.
export default function Loading() {
  return (
    <main className="loading fade-in">
      <div className="loading-spinner" />
      <h2 className="loading-title">Finding your vibe…</h2>
      <p className="loading-subtitle">
        Fetching tracks · classifying moods · scoring your matches · cueing the
        DJ
      </p>
    </main>
  )
}
