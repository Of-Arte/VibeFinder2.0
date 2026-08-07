# Changelog
All notable changes to the **VibeFinder** project will be documented in this file.

---

## [Unreleased]

### Planned
- LocalStorage / SQLite session history tracking for past playlists and DJ intros.
- OAuth integration for exporting generated playlists to Spotify and Apple Music.
- Track-level user feedback (thumbs up / thumbs down) for dynamic playlist re-ranking.

---

## [2.1.0] - Keyless Deezer API, Agent Evals & Weighted Scoring (2026-08-06)

### Added
- **Weighted Scoring Engine (`src/recommender.py` & `backend/agent.py`)**:
  - Multi-attribute weighted genre & mood vector scoring to eliminate single-genre dominance bias.
  - Scaled proximity calculation allowing subtle secondary preferences to influence song rankings.
- **Deezer API Metadata Integration (`backend/deezer_client.py`)**:
  - Live keyless audio track pool fetching, replacing local CSV candidate selection.
- **Evaluation Harness (`evaluate.py`)**:
  - Automated system quality benchmark suite evaluating recommendation precision, vibe alignment, and latency across test scenarios.
- **Resilience & Fallback Mechanisms**:
  - Track-level Gemini classification chunking and fallback heuristics with user-facing `degraded` flag.
  - Sliding-window rate limiting middleware (`backend/ratelimit.py`) preventing external API quota exhaustion.
- **DevOps & CI/CD**:
  - Multi-stage Docker containerization (`docker-compose.yml` and `backend/Dockerfile`).
  - GitHub Actions automated testing workflow (`.github/workflows/tests.yml`).

### Changed
- Refactored scoring from discrete step functions into smooth, weighted continuous-proximity distance curves.
- Refined DJ Intro prompt template to enforce strict injection safety.

---

## [2.0.0] - Web & Agent Initialization (2026-08-06)

### Added
- **React + Vite Web Application (`frontend/`)**:
  - Artist selection onboarding grid (16 curated artist cards).
  - Modern dark mode playlist UI with track cover art, badges, scoring explanations, and audio preview controls.
- **FastAPI Backend Server (`backend/server.py`)**:
  - Initial `POST /api/recommend` orchestration endpoint.
  - Initial `GET /api/health` probe.
- **Agentic Pipeline Scaffold (`backend/agent.py`)**:
  - Multi-agent workflow scaffolding (Classifier, Vibe Translator, DJ Intro Synthesizer).

---

## [1.0.0] - Legacy Baseline: Static CLI Recommender (2026-07-15)

> **Iteration Summary**: Initial CLI release scoring static CSV track datasets using basic mathematical attribute proximity.

### Added
- Static dataset parsing (`music_dataset.csv`).
- Deterministic attribute proximity scoring for energy, valence, tempo, and acousticness.
- Terminal CLI output displaying top ranked recommendations.
