// API integration for VibeFinder 2.0.
//
// All third-party access (Deezer track retrieval, Gemini agents) happens
// server-side in the FastAPI backend — no API keys are ever exposed to the
// browser. The frontend only talks to our own /api endpoint, proxied to
// http://localhost:8000 by Vite in development (see vite.config.js).

/**
 * Request a personalized playlist.
 * @param {string} userName
 * @param {string[]} selectedArtists
 * @returns {Promise<object>} the RecommendResponse payload
 */
export async function fetchRecommendations(userName, selectedArtists) {
  let response
  try {
    response = await fetch('/api/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_name: userName,
        selected_artists: selectedArtists,
      }),
    })
  } catch {
    // Network / connection refused (backend not running, etc.)
    throw new Error(
      'Could not reach the VibeFinder server. Is the backend running on port 8000?',
    )
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    try {
      const body = await response.json()
      if (body?.detail) detail = body.detail
    } catch {
      /* non-JSON error body — keep the generic message */
    }
    const err = new Error(detail)
    err.status = response.status
    throw err
  }

  return response.json()
}
