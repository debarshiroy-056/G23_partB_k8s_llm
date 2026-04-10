#!/bin/bash
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
