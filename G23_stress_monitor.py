# G23_stress_monitor.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Live CPU Stress Telemetry Daemon
# ─────────────────────────────────────────────────────────────────────────────
# Companion daemon to G23_network_monitor.py that tracks CPU contention on
# every node by polling the Kubernetes metrics-server. Used to visually
# confirm that the noisy-neighbor chaos pod is actually starving its target.
#
# How it works:
#   1. On each tick, calls the metrics.k8s.io/v1beta1/nodes custom object API.
#   2. Converts CPU usage from nanocores (K8s default) to millicores by
#      stripping the trailing 'n' and dividing by 1,000,000 (1m = 1/1000 core).
#   3. Prints a high-stress warning if any node exceeds 1000 millicores
#      (equivalent to 1 full CPU core saturated).
#   4. Appends rows to results/G23_stress_telemetry_<timestamp>.csv with
#      columns: timestamp_iso, elapsed_sec, node, cpu_millicores.
#
# CLI flags: --interval (seconds, default 5.0), --output (CSV path).
# Requires metrics-server to be installed on the cluster.
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import csv
import datetime as dt
import os
import time
from kubernetes import client, config

def get_node_stress():
    """Fetches real-time CPU usage (in millicores) from the K8s Metrics API."""
    config.load_kube_config()
    api = client.CustomObjectsApi()
    
    try:
        # Query the metrics-server for node statistics
        metrics = api.list_cluster_custom_object("metrics.k8s.io", "v1beta1", "nodes")
        node_metrics = {}
        
        for node in metrics.get('items', []):
            name = node['metadata']['name']
            cpu_nano = node['usage']['cpu']
            
            # K8s returns CPU in 'nanocores' (e.g., "150000000n"). 
            # We strip the 'n' and convert to 'millicores' (1m = 1/1000th of a CPU core)
            cpu_millicores = int(cpu_nano.replace('n', '')) // 1_000_000
            node_metrics[name] = cpu_millicores
            
        return node_metrics
    except Exception as e:
        print(f"Waiting for Metrics Server to initialize... ({e})")
        return None


def _default_output_path():
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("results", f"G23_stress_telemetry_{ts}.csv")


def _ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _append_rows(csv_path, elapsed_sec, stress_data):
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp_iso", "elapsed_sec", "node", "cpu_millicores"])
        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        for node, cpu in stress_data.items():
            writer.writerow([timestamp, f"{elapsed_sec:.2f}", node, int(cpu)])


def parse_args():
    parser = argparse.ArgumentParser(description="Monitor node CPU usage and write telemetry CSV.")
    parser.add_argument("--interval", type=float, default=5.0, help="Sampling interval in seconds (default: 5.0)")
    parser.add_argument("--output", default=None, help="Output CSV path (default: results/G23_stress_telemetry_<timestamp>.csv)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    output_path = args.output or _default_output_path()
    _ensure_parent_dir(output_path)

    print("🚀 Starting NEMESIS CPU Interference Telemetry...")
    print("Note: Metrics Server takes about 60 seconds to gather its first data points.\n")
    print(f"📁 Writing telemetry to: {output_path}")
    start_time = time.time()
    
    try:
        while True:
            stress_data = get_node_stress()
            if stress_data:
                elapsed = time.time() - start_time
                _append_rows(output_path, elapsed, stress_data)
                print("--- Real-Time Node CPU Usage (Millicores) ---")
                for node, cpu in stress_data.items():
                    # Visual warning if CPU is heavily spiked (e.g., over 1000 millicores / 1 full core)
                    warning = " ⚠️ (HIGH STRESS)" if cpu > 1000 else ""
                    print(f"{node}: {cpu}m{warning}")
                print("-" * 45)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n🛑 Stress Telemetry stopped.")
