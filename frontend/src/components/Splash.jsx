// Splash screen: logo + tagline + green pill CTA.
export default function Splash({ onStart }) {
  return (
    <main className="splash">
      <div className="splash-logo fade-in" style={{ animationDelay: '100ms' }}>
        <span className="splash-logo-mark">♫</span>
      </div>
      <h1 className="splash-title fade-in" style={{ animationDelay: '200ms' }}>
        VibeFinder
      </h1>
      <p className="splash-tagline fade-in" style={{ animationDelay: '300ms' }}>
        Let's find your vibe.
      </p>
      <button
        className="btn-primary splash-cta fade-in"
        style={{ animationDelay: '450ms' }}
        onClick={onStart}
      >
        Get Started
      </button>
    </main>
  )
}
