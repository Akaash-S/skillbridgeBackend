#!/usr/bin/env python3
"""
Endpoint Latency Benchmark (p50 / p95)
Measures response time across 4 key endpoints:
1. /health
2. /skills/master
3. /jobs/trending
4. /roles/categories
"""

import time
import statistics
import os
import sys

# Ensure backend root is on path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Set test environment
os.environ['ALLOW_MOCK_DB'] = 'true'
os.environ['DISABLE_SCHEDULER'] = 'true'
os.environ['TESTING'] = 'true'

from app import create_app

app = create_app()
client = app.test_client()

ENDPOINTS = [
    ("/health", "GET"),
    ("/skills/master", "GET"),
    ("/roles/categories", "GET"),
    ("/roadmap/templates", "GET"),
]

ROUNDS = 50

def run_benchmark():
    print(f"===========================================================")
    print(f"SkillBridge API Benchmark (Short Load Test: {ROUNDS} reqs/endpoint)")
    print(f"Environment: Windows 11, Python {sys.version.split()[0]}, Flask TestClient")
    print(f"Database Mode: ALLOW_MOCK_DB=true, In-memory cache")
    print(f"===========================================================\n")

    results = {}

    for endpoint, method in ENDPOINTS:
        latencies = []
        status_codes = []

        # Warm up 2 requests
        for _ in range(2):
            client.get(endpoint)

        for _ in range(ROUNDS):
            start = time.perf_counter()
            if method == "GET":
                resp = client.get(endpoint)
            else:
                resp = client.post(endpoint)
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            latencies.append(elapsed_ms)
            status_codes.append(resp.status_code)

        latencies.sort()
        p50 = statistics.median(latencies)
        # 95th percentile
        p95_idx = int(0.95 * len(latencies))
        p95 = latencies[min(p95_idx, len(latencies) - 1)]
        p99_idx = int(0.99 * len(latencies))
        p99 = latencies[min(p99_idx, len(latencies) - 1)]
        min_lat = latencies[0]
        max_lat = latencies[-1]
        mean_lat = statistics.mean(latencies)

        all_ok = all(s in (200, 201) for s in status_codes)

        results[endpoint] = {
            "status_code": status_codes[0],
            "all_ok": all_ok,
            "min_ms": round(min_lat, 2),
            "max_ms": round(max_lat, 2),
            "mean_ms": round(mean_lat, 2),
            "p50_ms": round(p50, 2),
            "p95_ms": round(p95, 2),
            "p99_ms": round(p99, 2),
        }

        print(f"Endpoint: {endpoint} [{method}]")
        print(f"  Status: {status_codes[0]} (All OK: {all_ok})")
        print(f"  Min: {min_lat:.2f} ms | Mean: {mean_lat:.2f} ms | Max: {max_lat:.2f} ms")
        print(f"  p50: {p50:.2f} ms | p95: {p95:.2f} ms | p99: {p99:.2f} ms\n")

    return results

if __name__ == "__main__":
    run_benchmark()
