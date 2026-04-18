#!/bin/bash

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Phase 2 Multi-Rack Latency Injector
# ─────────────────────────────────────────────────────────────────────────────
# Logically splits the 4-worker cluster into two racks by injecting a 50ms
# one-way latency on workers 3 and 4 (Rack B - Slow), leaving workers 1
# and 2 (Rack A - Fast) untouched.
#
# How it works:
#   1. Loops over llm-cluster-worker3 and llm-cluster-worker4.
#   2. Installs iproute2 inside each container (kind images are minimal).
#   3. Runs `tc qdisc add dev eth0 root netem delay 50ms`, emulating a
#      cross-zone data-center link.
#
# Invoked automatically by the Makefile's setup-cluster target right after
# the cluster is created, so Phase 2 trials always start with the rack
# split in place.
# ─────────────────────────────────────────────────────────────────────────────

echo "🌐 Splitting cluster into Rack A (Fast) and Rack B (Slow)..."

# Target worker3 and worker4 to represent the slow 'Rack B'
for node in llm-cluster-worker3 llm-cluster-worker4; do
    echo "  -> Injecting 50ms cross-zone latency into $node..."
    docker exec -u root $node apt-get update -y > /dev/null 2>&1
    docker exec -u root $node apt-get install -y iproute2 > /dev/null 2>&1
    # Add a 50ms delay to all outgoing packets on the main ethernet interface
    docker exec -u root $node tc qdisc add dev eth0 root netem delay 50ms > /dev/null 2>&1 || true
done
echo "✅ Rack B is now physically delayed by 50ms!"
