import { useState } from 'react'

// Standard, reasonable constraints for a display name. The name is only ever
// used as UI display text (it is never sent to the LLM), so this is about
// keeping it tidy and sensible rather than security-critical sanitization.
const MAX_NAME_LENGTH = 20
// Letters (incl. accents), spaces, hyphens and apostrophes — no digits/symbols.
const NAME_PATTERN = /^[\p{L}][\p{L} '-]*$/u

// Step 1 of the flow: capture the user's name before artist selection.
export default function NameStep({ onContinue }) {
  const [name, setName] = useState('')

  const trimmed = name.trim()
  const isValid = trimmed.length >= 2 && NAME_PATTERN.test(trimmed)

  function handleChange(e) {
    // Enforce max length and strip disallowed characters as the user types.
    const cleaned = e.target.value
      .replace(/[^\p{L} '-]/gu, '')
      .slice(0, MAX_NAME_LENGTH)
    setName(cleaned)
  }

  function handleSubmit(e) {
    e.preventDefault()
    if (!isValid) return
    onContinue(trimmed)
  }

  return (
    <main className="name-step fade-in">
      <form className="name-step-form" onSubmit={handleSubmit}>
        <h1 className="name-step-title">What should we call you?</h1>
        <p className="name-step-subtitle">
          We'll use this to personalize your playlist.
        </p>
        <input
          className="picker-name-input name-step-input"
          type="text"
          placeholder="Your name"
          value={name}
          onChange={handleChange}
          maxLength={MAX_NAME_LENGTH}
          minLength={2}
          autoComplete="given-name"
          aria-label="Your name"
          autoFocus
        />
        <button
          type="submit"
          className="btn-primary name-step-cta"
          disabled={!isValid}
        >
          Continue
        </button>
      </form>
    </main>
  )
}
