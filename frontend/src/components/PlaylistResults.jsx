import { useState } from 'react'
import SongCard from './SongCard'
import ErrorAlert from './ErrorAlert'

export default function PlaylistResults({ result, onRestart }) {
  // Only one preview plays at a time — track the active card by index.
  const [playingIndex, setPlayingIndex] = useState(null)

  const { user_name, dj_intro, playlist, source, target_vibe, degraded } = result
  const greeting = user_name?.trim() ? `${user_name}'s` : 'Your'

  return (
    <main className="results fade-in">
      <header className="results-header">
        <div>
          <p className="results-eyebrow">{greeting} personalized playlist</p>
          <h1 className="results-title">Tonight's Vibe</h1>
        </div>
        <button className="btn-ghost" onClick={onRestart}>
          Start over
        </button>
      </header>

      {degraded && (
        <ErrorAlert message="AI personalization is temporarily unavailable, scores may look uniform. Try again shortly." />
      )}

      {/* DJ Intro card */}
      <section className="dj-card">
        <div className="dj-badge">
          <span className="dj-live-dot" /> ON AIR
        </div>
        <p className="dj-intro-text">{dj_intro}</p>
        <p className="dj-meta">
          Vibe: {target_vibe?.favorite_mood} · {target_vibe?.favorite_genre} ·
          energy {Math.round((target_vibe?.target_energy ?? 0) * 100)}% ·
          sourced from {source}
        </p>
      </section>

      {/* Song list */}
      <section className="song-list">
        {playlist.map((song, index) => (
          <SongCard
            key={`${song.title}-${song.artist}-${index}`}
            song={song}
            rank={index + 1}
            isPlaying={playingIndex === index}
            onPlayToggle={() =>
              setPlayingIndex((cur) => (cur === index ? null : index))
            }
            onEnded={() => setPlayingIndex(null)}
          />
        ))}
      </section>
    </main>
  )
}
