// Styled alert banner for AI degradation warnings.
export default function ErrorAlert({ message }) {
  return (
    <div className="error-alert fade-in" role="status">
      <span className="error-alert-icon" aria-hidden="true">⚠️</span>
      <span className="error-alert-message">{message}</span>
    </div>
  )
}
