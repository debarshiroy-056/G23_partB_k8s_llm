#!/bin/bash
# G23_netem_status.sh

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Network Latency Inspection Helper
# ─────────────────────────────────────────────────────────────────────────────
# Diagnostic utility that prints the current tc qdisc configuration on
# every Phase 1 worker container so you can verify netem rules were applied
# and/or cleared correctly. Does not modify any state.
#
# Usage: ./G23_netem_status.sh
# ─────────────────────────────────────────────────────────────────────────────

INTERFACE="eth0"
WORKERS=("llm-cluster-worker" "llm-cluster-worker2")

echo "══ Current tc rules on worker nodes:"

for worker in "${WORKERS[@]}"; do
    echo ""
    echo "── ${worker}"
    docker exec "${worker}" tc qdisc show dev "${INTERFACE}"
done
