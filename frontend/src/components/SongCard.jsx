import { useEffect, useRef, useState } from 'react'

// A single track row: cover · title/artist · genre pill + play + info toggle.
export default function SongCard({ song, rank, isPlaying, onPlayToggle, onEnded }) {
  const audioRef = useRef(null)
  const [showInfo, setShowInfo] = useState(false)

  const hasPreview = Boolean(song.preview_url)

  // Drive the <audio> element from the parent-owned isPlaying flag so only one
  // preview ever plays at a time.
  useEffect(() => {
    const audio = audioRef.current
    if (!audio) return
    if (isPlaying) {
      audio.play().catch(() => onEnded())
    } else {
      audio.pause()
      audio.currentTime = 0
    }
  }, [isPlaying, onEnded])

  const reasons = Array.isArray(song.reasons) ? song.reasons : []

  return (
    <article className={`song-card ${isPlaying ? 'song-card-active' : ''}`}>
      <div className="song-main">
        <span className="song-rank">{rank}</span>

        <div className="song-cover">
          {song.cover_url ? (
            <img src={song.cover_url} alt="" loading="lazy" />
          ) : (
            <span className="song-cover-fallback">♫</span>
          )}
        </div>

        <div className="song-meta">
          <p className="song-title" title={song.title}>
            {song.title}
          </p>
          <p className="song-artist">{song.artist}</p>
        </div>

        <div className="song-actions">
          {song.genre && <span className="song-genre-pill">{song.genre}</span>}

          <button
            className="icon-btn play-btn"
            onClick={onPlayToggle}
            disabled={!hasPreview}
            title={
              hasPreview ? 'Play 30s preview' : 'No preview available'
            }
            aria-label={isPlaying ? 'Pause preview' : 'Play preview'}
          >
            {isPlaying ? '❚❚' : '▶'}
          </button>

          <button
            className={`icon-btn info-btn ${showInfo ? 'info-btn-active' : ''}`}
            onClick={() => setShowInfo((s) => !s)}
            aria-expanded={showInfo}
            aria-label="Why this track"
            title="Why this track?"
          >
            ℹ
          </button>
        </div>
      </div>

      {showInfo && (
        <div className="song-info">
          <div className="song-info-header">
            <span className="song-score">Match score {song.score}</span>
          </div>
          <ul className="song-reasons">
            {reasons.length > 0 ? (
              reasons.map((reason, i) => <li key={i}>{reason}</li>)
            ) : (
              <li>Matches your baseline profile.</li>
            )}
          </ul>
        </div>
      )}

      {hasPreview && (
        <audio
          ref={audioRef}
          src={song.preview_url}
          onEnded={onEnded}
          preload="none"
        />
      )}
    </article>
  )
}
