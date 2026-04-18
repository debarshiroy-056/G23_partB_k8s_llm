#!/bin/bash
# G23_netem_apply.sh

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Network Latency Injection Helper (Phase 1B)
# ─────────────────────────────────────────────────────────────────────────────
# Uses Linux Traffic Control (tc netem) to add a precise, deterministic
# packet delay to both Phase 1 worker containers. Runs inside each Kind
# node's container via `docker exec`.
#
# Usage:   ./G23_netem_apply.sh <delay_ms>
# Example: ./G23_netem_apply.sh 10           # adds 10ms delay
#
# For every worker it:
#   1. Deletes any existing root qdisc to prevent rule stacking.
#   2. Adds a fresh `netem delay <X>ms` rule on eth0.
#
# Used in a loop by G23_sweep_run.sh to step through 0/1/5/10/25ms delays.
# ─────────────────────────────────────────────────────────────────────────────

set -e

DELAY_MS=${1:-10}
INTERFACE="eth0"
WORKERS=("llm-cluster-worker" "llm-cluster-worker2")

echo "══ Applying ${DELAY_MS}ms latency to worker nodes on ${INTERFACE}..."

for worker in "${WORKERS[@]}"; do
    echo "── ${worker}"

    # Remove any existing qdisc first (ignore errors if none exists)
    docker exec "${worker}" tc qdisc del dev "${INTERFACE}" root 2>/dev/null || true

    # Apply new netem rule with specified delay
    docker exec "${worker}" tc qdisc add dev "${INTERFACE}" root netem delay "${DELAY_MS}ms"

    echo "   ✓ Applied ${DELAY_MS}ms delay"
done

echo "══ Done. Verify with: ./G23_netem_status.sh"
