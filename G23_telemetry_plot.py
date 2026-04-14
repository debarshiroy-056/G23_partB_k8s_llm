# G23_telemetry_plot.py
#
# Reads monitor CSV logs from G23_network_monitor.py and G23_stress_monitor.py
# and generates time-series plots for node latency and node CPU usage.
#
# Usage:
#   python G23_telemetry_plot.py
#   python G23_telemetry_plot.py --network-csv results/G23_network_telemetry_YYYYMMDD_HHMMSS.csv \
#                                --stress-csv results/G23_stress_telemetry_YYYYMMDD_HHMMSS.csv

import argparse
import csv
import glob
import os
import sys

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

matplotlib.rcParams["font.family"] = "serif"
matplotlib.rcParams["font.serif"] = ["Times New Roman"]


def parse_args():
    parser = argparse.ArgumentParser(description="Generate plots from network and stress telemetry CSV logs.")
    parser.add_argument("--network-csv", default=None, help="Path to network telemetry CSV.")
    parser.add_argument("--stress-csv", default=None, help="Path to stress telemetry CSV.")
    parser.add_argument("--out-prefix", default="G23_telemetry", help="Prefix for output PNG files.")
    return parser.parse_args()


def latest_match(pattern):
    matches = glob.glob(pattern)
    if not matches:
        return None
    return max(matches, key=os.path.getmtime)


def load_network(csv_path):
    # Returns: {node: [(elapsed_sec, latency_ms), ...]}
    by_node = {}
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if (row.get("status") or "").strip().lower() != "ok":
                continue
            try:
                node = row["node"]
                elapsed = float(row["elapsed_sec"])
                latency = float(row["latency_ms"])
            except (KeyError, TypeError, ValueError):
                continue
            by_node.setdefault(node, []).append((elapsed, latency))
    for node in by_node:
        by_node[node].sort(key=lambda x: x[0])
    return by_node


def load_stress(csv_path):
    # Returns: {node: [(elapsed_sec, cpu_millicores), ...]}
    by_node = {}
    with open(csv_path, "r", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            try:
                node = row["node"]
                elapsed = float(row["elapsed_sec"])
                cpu = float(row["cpu_millicores"])
            except (KeyError, TypeError, ValueError):
                continue
            by_node.setdefault(node, []).append((elapsed, cpu))
    for node in by_node:
        by_node[node].sort(key=lambda x: x[0])
    return by_node


def plot_lines(data_by_node, y_label, title, out_path):
    if not data_by_node:
        print(f"Skipping {out_path}: no valid samples found.")
        return False

    fig, ax = plt.subplots(figsize=(12, 6))
    for node, points in sorted(data_by_node.items()):
        arr = np.array(points, dtype=float)
        ax.plot(arr[:, 0], arr[:, 1], linewidth=2, label=node)

    ax.set_xlabel("Elapsed Time (seconds)", fontweight="bold")
    ax.set_ylabel(y_label, fontweight="bold")
    ax.set_title(title, fontweight="bold")
    ax.grid(True, linestyle="--", alpha=0.5)
    ax.legend(loc="best", fontsize=9)
    ax.set_axisbelow(True)

    fig.tight_layout()
    fig.savefig(out_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved: {out_path}")
    return True


def main():
    args = parse_args()

    network_csv = args.network_csv or latest_match(os.path.join("results", "G23_network_telemetry_*.csv"))
    stress_csv = args.stress_csv or latest_match(os.path.join("results", "G23_stress_telemetry_*.csv"))

    if not network_csv and not stress_csv:
        print("No telemetry CSV files found in results/. Run monitors first.")
        sys.exit(1)

    generated = 0

    if network_csv:
        network_data = load_network(network_csv)
        out = f"{args.out_prefix}_network.png"
        ok = plot_lines(
            network_data,
            y_label="Latency (ms)",
            title=f"G23 Network Telemetry by Node\nSource: {os.path.basename(network_csv)}",
            out_path=out,
        )
        generated += int(ok)
    else:
        print("No network telemetry CSV found.")

    if stress_csv:
        stress_data = load_stress(stress_csv)
        out = f"{args.out_prefix}_stress.png"
        ok = plot_lines(
            stress_data,
            y_label="CPU Usage (millicores)",
            title=f"G23 CPU Stress Telemetry by Node\nSource: {os.path.basename(stress_csv)}",
            out_path=out,
        )
        generated += int(ok)
    else:
        print("No stress telemetry CSV found.")

    if generated == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
