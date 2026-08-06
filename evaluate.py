"""
VibeFinder 2.0 - Standalone System Evaluation Harness

Runs the full recommendation pipeline across a standardized benchmark suite
of user artist profiles. Computes latency breakdown, recommendation vibe alignment,
pool diversity, degradation rate, and overall system health score.

Usage:
  python evaluate.py --mock                 # Run offline benchmark with mock data
  python evaluate.py --live                 # Run live benchmark against real APIs
  python evaluate.py --mock --save eval.json# Run benchmark and save JSON report artifact
"""

import argparse
import json
import math
import sys
import time
from typing import Dict, List, Any

# Predefined Evaluation Benchmark Suite
BENCHMARK_SCENARIOS = [
    {
        "id": "pop_mainstream",
        "name": "Pop & Mainstream",
        "user_name": "TaylorFan",
        "selected_artists": ["Taylor Swift", "Dua Lipa", "Billie Eilish"],
    },
    {
        "id": "electronic_dance",
        "name": "Electronic & Dance",
        "user_name": "ElectroHead",
        "selected_artists": ["Daft Punk", "Justice", "Calvin Harris"],
    },
    {
        "id": "rock_metal",
        "name": "Rock & Metal",
        "user_name": "MetalHead",
        "selected_artists": ["Iron Maiden", "Radiohead", "Arctic Monkeys"],
    },
    {
        "id": "jazz_lofi",
        "name": "Jazz & Lofi",
        "user_name": "ChillLofi",
        "selected_artists": ["Miles Davis", "Nujabes"],
    },
    {
        "id": "cross_genre",
        "name": "Cross-Genre Blend",
        "user_name": "EclecticListener",
        "selected_artists": ["Daft Punk", "Miles Davis", "Taylor Swift"],
    },
    {
        "id": "single_artist",
        "name": "Single Artist Focus",
        "user_name": "SoloFan",
        "selected_artists": ["The Weeknd"],
    },
    {
        "id": "edge_case_empty",
        "name": "Edge Case - Empty Input",
        "user_name": "Anonymous",
        "selected_artists": [],
    },
]

# Mock track pool for offline --mock mode
MOCK_EVAL_POOL = [
    {"title": "Blinding Lights", "artist": "The Weeknd", "genre": "pop", "deezer_bpm": 171.0, "deezer_rank": 950000},
    {"title": "Levitating", "artist": "Dua Lipa", "genre": "pop", "deezer_bpm": 103.0, "deezer_rank": 920000},
    {"title": "Cruel Summer", "artist": "Taylor Swift", "genre": "pop", "deezer_bpm": 170.0, "deezer_rank": 960000},
    {"title": "One More Time", "artist": "Daft Punk", "genre": "edm", "deezer_bpm": 123.0, "deezer_rank": 890000},
    {"title": "D.A.N.C.E.", "artist": "Justice", "genre": "edm", "deezer_bpm": 115.0, "deezer_rank": 820000},
    {"title": "Feel So Close", "artist": "Calvin Harris", "genre": "edm", "deezer_bpm": 128.0, "deezer_rank": 870000},
    {"title": "The Trooper", "artist": "Iron Maiden", "genre": "metal", "deezer_bpm": 160.0, "deezer_rank": 780000},
    {"title": "Karma Police", "artist": "Radiohead", "genre": "rock", "deezer_bpm": 75.0, "deezer_rank": 840000},
    {"title": "Do I Wanna Know?", "artist": "Arctic Monkeys", "genre": "rock", "deezer_bpm": 85.0, "deezer_rank": 910000},
    {"title": "So What", "artist": "Miles Davis", "genre": "jazz", "deezer_bpm": 136.0, "deezer_rank": 760000},
    {"title": "Feather", "artist": "Nujabes", "genre": "lofi", "deezer_bpm": 92.0, "deezer_rank": 800000},
    {"title": "Bad Guy", "artist": "Billie Eilish", "genre": "pop", "deezer_bpm": 135.0, "deezer_rank": 930000},
]


def calculate_vibe_alignment(target_vibe: Dict[str, Any], playlist: List[Dict[str, Any]]) -> float:
    """
    Compute similarity score (0.0 to 1.0) between target vibe and playlist tracks.
    Compares normalized continuous features: energy, valence, danceability, acousticness.
    """
    if not playlist:
        return 0.0

    target_e = float(target_vibe.get("target_energy", 0.5))
    target_v = float(target_vibe.get("target_valence", 0.5))
    target_d = float(target_vibe.get("target_danceability", 0.5))
    target_a = float(target_vibe.get("target_acousticness", 0.5))

    distances = []
    for track in playlist:
        e = float(track.get("energy", 0.5))
        v = float(track.get("valence", 0.5))
        d = float(track.get("danceability", 0.5))
        a = float(track.get("acousticness", 0.5))

        # Euclidean distance in 4D feature space (max distance = 2.0)
        dist = math.sqrt((e - target_e) ** 2 + (v - target_v) ** 2 + (d - target_d) ** 2 + (a - target_a) ** 2)
        distances.append(dist)

    avg_dist = sum(distances) / len(distances)
    # Convert distance to alignment score between 0.0 and 1.0
    alignment = max(0.0, 1.0 - (avg_dist / 2.0))
    return round(alignment, 4)


def calculate_playlist_diversity(playlist: List[Dict[str, Any]]) -> float:
    """
    Compute playlist feature variance (spread across energy & valence).
    Prevents recommendations from being monotonous.
    """
    if len(playlist) < 2:
        return 0.0

    energies = [float(t.get("energy", 0.5)) for t in playlist]
    mean_e = sum(energies) / len(energies)
    var_e = sum((x - mean_e) ** 2 for x in energies) / len(energies)

    valences = [float(t.get("valence", 0.5)) for t in playlist]
    mean_v = sum(valences) / len(valences)
    var_v = sum((x - mean_v) ** 2 for x in valences) / len(valences)

    diversity = math.sqrt((var_e + var_v) / 2.0)
    return round(diversity, 4)


def run_eval_scenario(scenario: Dict[str, Any], mock: bool = True) -> Dict[str, Any]:
    """Execute full recommendation pipeline for one scenario and capture evaluation metrics."""
    from backend import agent, deezer_client, server
    from src.recommender import score_song

    artists = scenario["selected_artists"]

    t0 = time.perf_counter()

    # Step 1: Fetch
    t_f0 = time.perf_counter()
    if mock:
        pool = list(MOCK_EVAL_POOL)
        source = "deezer_mock"
    else:
        pool, source = server._fetch_pool(artists)
    t_fetch = time.perf_counter() - t_f0

    agent.reset_degraded()

    # Step 2: Classify
    t_c0 = time.perf_counter()
    pool = server._classify_pool(pool)
    t_classify = time.perf_counter() - t_c0

    # Step 3: Vibe Translation
    t_v0 = time.perf_counter()
    target_vibe = agent.translate_artists_to_prefs(artists, pool)
    t_vibe = time.perf_counter() - t_v0

    # Step 4: Scoring
    t_s0 = time.perf_counter()
    playlist = server._score_pool(pool, target_vibe, k=5)
    t_score = time.perf_counter() - t_s0

    # Step 5: DJ Intro
    t_d0 = time.perf_counter()
    dj_intro = agent.generate_dj_intro(artists, playlist)
    t_dj = time.perf_counter() - t_d0

    t_total = time.perf_counter() - t0

    is_degraded = agent.is_degraded()
    vibe_alignment = calculate_vibe_alignment(target_vibe, playlist)
    diversity = calculate_playlist_diversity(playlist)

    return {
        "scenario_id": scenario["id"],
        "scenario_name": scenario["name"],
        "artists": artists,
        "source": source,
        "pool_size": len(pool),
        "playlist_size": len(playlist),
        "target_vibe": target_vibe,
        "dj_intro": dj_intro,
        "degraded": is_degraded,
        "vibe_alignment": vibe_alignment,
        "diversity": diversity,
        "latency_ms": {
            "fetch": round(t_fetch * 1000, 2),
            "classify": round(t_classify * 1000, 2),
            "vibe_translation": round(t_vibe * 1000, 2),
            "scoring": round(t_score * 1000, 2),
            "dj_intro": round(t_dj * 1000, 2),
            "total": round(t_total * 1000, 2),
        },
    }


def main():
    parser = argparse.ArgumentParser(description="VibeFinder 2.0 System Evaluation Harness")
    parser.add_argument("--mock", action="store_true", default=True, help="Run evaluation in mock/offline mode")
    parser.add_argument("--live", action="store_true", help="Run evaluation against live Deezer and Gemini APIs")
    parser.add_argument("--save", type=str, help="Save evaluation report output as JSON file")
    args = parser.parse_args()

    use_mock = not args.live

    mode_str = "LIVE APIs" if args.live else "OFFLINE MOCK"
    print("=" * 80)
    print(f"  VIBEFINDER 2.0 - SYSTEM EVALUATION HARNESS  [{mode_str}]")
    print("=" * 80)
    print(f"Running {len(BENCHMARK_SCENARIOS)} benchmark scenarios...\n")

    results = []
    total_alignment = 0.0
    total_latency = 0.0
    total_diversity = 0.0
    degraded_count = 0

    for sc in BENCHMARK_SCENARIOS:
        try:
            res = run_eval_scenario(sc, mock=use_mock)
            results.append(res)

            total_alignment += res["vibe_alignment"]
            total_latency += res["latency_ms"]["total"]
            total_diversity += res["diversity"]
            if res["degraded"]:
                degraded_count += 1

            status_str = "DEGRADED" if res["degraded"] else "OK"
            print(
                f"  [{res['scenario_name']:<22}] "
                f"Total: {res['latency_ms']['total']:>6.1f} ms | "
                f"Vibe Align: {res['vibe_alignment']:>5.2f} | "
                f"Diversity: {res['diversity']:>5.3f} | "
                f"Status: {status_str}"
            )

            from backend import config
            if config.has_gemini() and sc != BENCHMARK_SCENARIOS[-1]:
                print("  Sleeping 10s to respect Gemini rate limits...")
                time.sleep(10.0)
        except Exception as e:
            print(f"  [{sc['name']:<22}] FAILED with error: {str(e)}")

    n = len(results)
    if n == 0:
        print("No scenario succeeded.")
        sys.exit(1)

    avg_alignment = total_alignment / n
    avg_latency = total_latency / n
    avg_diversity = total_diversity / n
    degradation_rate = (degraded_count / n) * 100.0

    # Composite health score (0-100): 50% vibe alignment, 30% latency (<2000ms), 20% resilience
    lat_score = max(0.0, 1.0 - (avg_latency / 2000.0))
    resilience_score = max(0.0, 1.0 - (degradation_rate / 100.0))
    health_score = round((avg_alignment * 50) + (lat_score * 30) + (resilience_score * 20), 1)

    print("\n" + "=" * 80)
    print("  EVALUATION SUMMARY & SYSTEM HEALTH METRICS")
    print("=" * 80)
    print(f"  Total Scenarios Evaluated : {n}")
    print(f"  Mean Total Latency        : {avg_latency:.2f} ms")
    print(f"  Mean Vibe Alignment Score : {avg_alignment:.4f} (Target: >0.80)")
    print(f"  Mean Feature Diversity    : {avg_diversity:.4f}")
    print(f"  Degraded Execution Rate   : {degradation_rate:.1f}%")
    print(f"  System Health Score       : {health_score}/100")
    print("=" * 80)

    summary_data = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": "live" if args.live else "mock",
        "scenarios_evaluated": n,
        "metrics": {
            "mean_total_latency_ms": round(avg_latency, 2),
            "mean_vibe_alignment": round(avg_alignment, 4),
            "mean_feature_diversity": round(avg_diversity, 4),
            "degradation_rate_percent": round(degradation_rate, 1),
            "system_health_score": health_score,
        },
        "details": results,
    }

    if args.save:
        save_path = args.save
        with open(save_path, "w", encoding="utf-8") as f:
            json.dump(summary_data, f, indent=2)
        print(f"\n[Artifact Saved] Detailed evaluation report written to {save_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
