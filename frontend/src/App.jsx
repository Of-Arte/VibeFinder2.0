import { useState } from 'react'
import './App.css'
import Splash from './components/Splash'
import NameStep from './components/NameStep'
import ArtistPicker from './components/ArtistPicker'
import Loading from './components/Loading'
import PlaylistResults from './components/PlaylistResults'
import OutageScreen from './components/OutageScreen'
import { fetchRecommendations } from './api'

// Screen state machine: 'splash' -> 'name' -> 'picker' -> 'loading' -> 'results'
function App() {
  const [screen, setScreen] = useState('splash')
  const [userName, setUserName] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')
  const [selectedArtists, setSelectedArtists] = useState([])

  function handleNameContinue(name) {
    setUserName(name)
    setScreen('picker')
  }

  async function handleGenerate(artistsList) {
    setSelectedArtists(artistsList)
    setError('')
    setScreen('loading')
    try {
      const data = await fetchRecommendations(userName, artistsList)
      setResult(data)
      setScreen('results')
    } catch (err) {
      setError(err.message || 'Something went wrong.')
      if (err.status === 502 || err.status === 503) {
        setScreen('outage')
      } else {
        setScreen('picker')
      }
    }
  }

  async function handleRetry() {
    await handleGenerate(selectedArtists)
  }

  function handleRestart() {
    setResult(null)
    setError('')
    setScreen('picker')
  }

  return (
    <div className="app-shell">
      {screen === 'splash' && <Splash onStart={() => setScreen('name')} />}

      {screen === 'name' && <NameStep onContinue={handleNameContinue} />}

      {screen === 'picker' && (
        <ArtistPicker onGenerate={handleGenerate} error={error} />
      )}

      {screen === 'loading' && <Loading />}

      {screen === 'outage' && (
        <OutageScreen error={error} onRetry={handleRetry} />
      )}

      {screen === 'results' && result && (
        <PlaylistResults result={result} onRestart={handleRestart} />
      )}
    </div>
  )
}

export default App
