import { useState } from 'react'

// Step 1 of the flow: capture the user's name before artist selection.
export default function NameStep({ onContinue }) {
  const [name, setName] = useState('')

  function handleSubmit(e) {
    e.preventDefault()
    onContinue(name.trim())
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
          onChange={(e) => setName(e.target.value)}
          maxLength={40}
          autoFocus
        />
        <button type="submit" className="btn-primary name-step-cta">
          Continue
        </button>
      </form>
    </main>
  )
}
