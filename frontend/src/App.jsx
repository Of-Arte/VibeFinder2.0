import { useState } from 'react'
import './App.css'
import Splash from './components/Splash'
import NameStep from './components/NameStep'
import ArtistPicker from './components/ArtistPicker'
import Loading from './components/Loading'
import PlaylistResults from './components/PlaylistResults'
import { fetchRecommendations } from './api'

// Screen state machine: 'splash' -> 'name' -> 'picker' -> 'loading' -> 'results'
function App() {
  const [screen, setScreen] = useState('splash')
  const [userName, setUserName] = useState('')
  const [result, setResult] = useState(null)
  const [error, setError] = useState('')

  function handleNameContinue(name) {
    setUserName(name)
    setScreen('picker')
  }

  async function handleGenerate(selectedArtists) {
    setError('')
    setScreen('loading')
    try {
      const data = await fetchRecommendations(userName, selectedArtists)
      setResult(data)
      setScreen('results')
    } catch (err) {
      setError(err.message || 'Something went wrong.')
      setScreen('picker')
    }
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

      {screen === 'results' && result && (
        <PlaylistResults result={result} onRestart={handleRestart} />
      )}
    </div>
  )
}

export default App
