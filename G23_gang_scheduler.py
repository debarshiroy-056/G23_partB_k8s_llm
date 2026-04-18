# G23_gang_scheduler.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Topology-Aware Gang Scheduler
# ─────────────────────────────────────────────────────────────────────────────
# A specialized scheduler that protects the DDP All-Reduce ring by ensuring
# ALL N workers of a distributed job land on the same low-latency rack ("gang"
# scheduling), preventing cross-zone bottlenecks.
#
# How it works:
#   1. Watches the cluster for pods tagged `schedulerName: gang-scheduler`.
#   2. Accumulates all 4 pending workers before making any placement decision
#      (the "gang" property -> schedule all together or none at all).
#   3. Maps the network: pings every worker node to build a latency map.
#   4. Sorts nodes by latency and picks the 2 fastest as the "Fast Rack".
#   5. Bin-packs the 4 pods onto these 2 fast nodes (2 pods per node) via
#      V1Binding, trading CPU contention for network locality.
#
# Note: This exposes the Phase 2 trade-off documented in our report -
# aggressive bin-packing avoids the 50ms cross-zone penalty but can cause
# severe CPU fighting when heavy ML workers are double-stacked.
# ─────────────────────────────────────────────────────────────────────────────

import time
import subprocess
from kubernetes import client, config, watch

def ping_node(ip):
    try:
        out = subprocess.check_output(["ping", "-c", "1", ip], stderr=subprocess.STDOUT, universal_newlines=True)
        for line in out.split('\n'):
            if "time=" in line:
                return float(line.split("time=")[1].split(" ")[0])
        return 100.0
    except:
        return 100.0

def run_gang_scheduler():
    config.load_kube_config()
    v1 = client.CoreV1Api()
    
    print("🧠 Gang Scheduler running: Waiting for 4 PyTorch pods...")
    pending_pods = []
    
    w = watch.Watch()
    for event in w.stream(v1.list_pod_for_all_namespaces):
        pod = event['object']
        
        # Intercept pods asking for gang scheduling
        if pod.status.phase == "Pending" and pod.spec.scheduler_name == "gang-scheduler" and not pod.spec.node_name:
            if pod.metadata.name not in [p.metadata.name for p in pending_pods]:
                pending_pods.append(pod)
                print(f"🔔 Captured Pod: {pod.metadata.name} ({len(pending_pods)}/4)")
                
            # Once we have the full "Gang" of 4 pods, execute topology mapping
            if len(pending_pods) == 4:
                print("\n🗺️ Mapping Cluster Network Topology...")
                nodes = [n for n in v1.list_node().items if "worker" in n.metadata.name]
                node_latencies = {}
                
                for n in nodes:
                    ip = next(addr.address for addr in n.status.addresses if addr.type == "InternalIP")
                    node_latencies[n.metadata.name] = ping_node(ip)
                    print(f"  -> {n.metadata.name}: {node_latencies[n.metadata.name]:.2f}ms")
                
                # Sort nodes by latency and grab the two fastest (Rack A)
                fast_rack = sorted(node_latencies.items(), key=lambda x: x[1])[:2]
                fast_nodes = [n[0] for n in fast_rack]
                
                print(f"🏆 Selected Fast Rack: {fast_nodes}")
                print("📦 Bin-packing the 4 pods onto the fast rack...")
                
                # Pack 2 pods per fast node
                for i, p in enumerate(pending_pods):
                    target = fast_nodes[i % 2]
                    ref = client.V1ObjectReference(kind="Node", api_version="v1", name=target)
                    meta = client.V1ObjectMeta(name=p.metadata.name)
                    binding = client.V1Binding(target=ref, metadata=meta)
                    v1.create_namespaced_binding(namespace=p.metadata.namespace, body=binding, _preload_content=False)
                    print(f"✅ Bound {p.metadata.name} -> {target}")
                
                # Clear the queue for the next trial
                pending_pods = [] 

if __name__ == "__main__":
    run_gang_scheduler()
