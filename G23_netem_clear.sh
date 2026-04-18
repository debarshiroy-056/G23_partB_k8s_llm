#!/bin/bash
# G23_netem_clear.sh

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Network Latency Cleanup Helper (Phase 1B)
# ─────────────────────────────────────────────────────────────────────────────
# Removes all tc netem rules from the Phase 1 worker containers, restoring
# default (near-zero) networking. Invoked:
#   1. Before each 0ms baseline sweep step in G23_sweep_run.sh.
#   2. At the end of the entire sweep to leave the cluster in a clean state.
#
# Silently tolerates "no rules to clear" so it is safe to call repeatedly.
# ─────────────────────────────────────────────────────────────────────────────

set -e

INTERFACE="eth0"
WORKERS=("llm-cluster-worker" "llm-cluster-worker2")

echo "══ Clearing tc rules from worker nodes..."

for worker in "${WORKERS[@]}"; do
    echo "── ${worker}"
    docker exec "${worker}" tc qdisc del dev "${INTERFACE}" root 2>/dev/null || echo "   (no rules to clear)"
    echo "   ✓ Cleared"
done

echo "══ Done. Networking restored to normal."
