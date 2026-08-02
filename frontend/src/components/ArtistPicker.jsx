import { useState } from 'react'

// The exact 16-artist grid mandated by the handoff (Step 2.3).
const ARTISTS = [
  'Taylor Swift',
  'Billie Eilish',
  'Kendrick Lamar',
  'Daft Punk',
  'Radiohead',
  'Miles Davis',
  'Iron Maiden',
  'Bob Marley',
  'Adele',
  'The Weeknd',
  'Fleet Foxes',
  'Ravi Shankar',
  'Nujabes',
  'Beethoven',
  'Arctic Monkeys',
  'Calvin Harris',
]

const MIN_SELECTION = 3

export default function ArtistPicker({ onGenerate, error }) {
  const [selected, setSelected] = useState([])

  const canContinue = selected.length >= MIN_SELECTION

  function toggle(artist) {
    setSelected((prev) =>
      prev.includes(artist)
        ? prev.filter((a) => a !== artist)
        : [...prev, artist],
    )
  }

  function handleSubmit() {
    if (!canContinue) return
    onGenerate(selected)
  }

  return (
    <main className="picker fade-in">
      <header className="picker-header">
        <h1 className="picker-title">Build your vibe</h1>
        <p className="picker-subtitle">
          Pick at least {MIN_SELECTION} artists you love and we'll spin up a
          playlist tuned to your taste.
        </p>
      </header>

      <div className="picker-grid">
        {ARTISTS.map((artist) => {
          const active = selected.includes(artist)
          return (
            <button
              key={artist}
              className={`chip ${active ? 'chip-active' : ''}`}
              onClick={() => toggle(artist)}
              aria-pressed={active}
            >
              {artist}
            </button>
          )
        })}
      </div>

      {error && <p className="picker-error">{error}</p>}

      <div className="picker-footer">
        <span className="picker-count">
          {selected.length} selected
          {!canContinue && ` · ${MIN_SELECTION - selected.length} more to go`}
        </span>
        <button
          className="btn-cta-compact"
          onClick={handleSubmit}
          disabled={!canContinue}
        >
          Find my vibe
        </button>
      </div>
    </main>
  )
}
