# G23_network_monitor.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Live Network Telemetry Daemon
# ─────────────────────────────────────────────────────────────────────────────
# Standalone observability process that periodically pings every worker node
# and logs latency to a timestamped CSV. Used to validate the emulation
# environment (verifying that tc netem and the topology_injector actually
# produced the expected latency bands).
#
# How it works:
#   1. Queries the K8s API for every node's InternalIP on each tick.
#   2. Issues a single ICMP ping per node and parses the 'time=' field.
#   3. Unreachable nodes are marked 'unreachable' with empty latency so
#      downstream plotting can distinguish packet loss from real values.
#   4. Appends rows to results/G23_network_telemetry_<timestamp>.csv with
#      columns: timestamp_iso, elapsed_sec, node, latency_ms, status.
#
# CLI flags: --interval (seconds between samples, default 2.0),
#            --output   (custom CSV path).
# ─────────────────────────────────────────────────────────────────────────────

import argparse
import csv
import datetime as dt
import os
import subprocess
import time
from kubernetes import client, config

def get_node_ips():
    """Fetches the internal IP addresses of all Kubernetes nodes."""
    config.load_kube_config()
    v1 = client.CoreV1Api()
    nodes = v1.list_node().items
    
    node_ips = {}
    for node in nodes:
        node_name = node.metadata.name
        # Find the InternalIP address
        for address in node.status.addresses:
            if address.type == "InternalIP":
                node_ips[node_name] = address.address
    return node_ips

def ping_node(ip_address):
    """Pings an IP address once and returns the latency in milliseconds."""
    try:
        # Removed the strict Mac 1ms timeout so it can capture the 100ms delay
        output = subprocess.check_output(
            ["ping", "-c", "1", ip_address], 
            stderr=subprocess.STDOUT, 
            universal_newlines=True
        )
        # Parse the output to find the 'time=X.XXX ms' string
        for line in output.split('\n'):
            if "time=" in line:
                time_ms = line.split("time=")[1].split(" ")[0]
                return float(time_ms)
        
        return float('inf') # Safety fallback if parsing fails
        
    except subprocess.CalledProcessError:
        return float('inf') # Return infinity if the ping fails/drops
    except Exception as e:
        print(f"Error occurred while pinging {ip_address}: {e}")
        return float('inf')

def generate_network_matrix():
    """Builds and returns the latency dictionary for the scheduler."""
    node_ips = get_node_ips()
    network_matrix = {}
    
    for node_name, ip in node_ips.items():
        latency = ping_node(ip)
        network_matrix[node_name] = latency
        
    return network_matrix


def _default_output_path():
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    return os.path.join("results", f"G23_network_telemetry_{ts}.csv")


def _ensure_parent_dir(path):
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def _append_rows(csv_path, elapsed_sec, matrix):
    file_exists = os.path.exists(csv_path)
    with open(csv_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["timestamp_iso", "elapsed_sec", "node", "latency_ms", "status"])
        timestamp = dt.datetime.now(dt.timezone.utc).isoformat()
        for node, latency in matrix.items():
            if latency == float('inf'):
                writer.writerow([timestamp, f"{elapsed_sec:.2f}", node, "", "unreachable"])
            else:
                writer.writerow([timestamp, f"{elapsed_sec:.2f}", node, f"{latency:.6f}", "ok"])


def parse_args():
    parser = argparse.ArgumentParser(description="Monitor node network latency and write telemetry CSV.")
    parser.add_argument("--interval", type=float, default=2.0, help="Sampling interval in seconds (default: 2.0)")
    parser.add_argument("--output", default=None, help="Output CSV path (default: results/G23_network_telemetry_<timestamp>.csv)")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    output_path = args.output or _default_output_path()
    _ensure_parent_dir(output_path)

    print("🚀 Starting NEMESIS Network Telemetry Module...")
    print(f"📁 Writing telemetry to: {output_path}")
    start_time = time.time()
    try:
        while True:
            matrix = generate_network_matrix()
            elapsed = time.time() - start_time
            _append_rows(output_path, elapsed, matrix)
            print("\n--- Real-Time Network Matrix ---")
            for node, latency in matrix.items():
                # If latency is infinity, it means the node is totally unreachable
                if latency == float('inf'):
                    print(f"{node}: Unreachable (Packet Loss)")
                else:
                    print(f"{node}: {latency:.2f} ms")
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\n🛑 Telemetry stopped.")