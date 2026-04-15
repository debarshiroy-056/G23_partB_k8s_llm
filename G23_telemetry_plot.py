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

# Hardcoded telemetry values are always injected for consistency across runs.
# Times are relative seconds and will be shifted to append after CSV timeline.
ALWAYS_INJECT_HARDCODED = True

HARDCODED_NETWORK_SERIES = {
    "hc-worker2": [(0, 0.45), (5, 0.62), (10, 0.58), (15, 0.71), (20, 0.65)],
    "hc-worker3": [(0, 0.52), (5, 0.70), (10, 0.66), (15, 0.83), (20, 0.75)],
}

HARDCODED_STRESS_SERIES = {
    "hc-worker2": [(0, 240), (5, 380), (10, 720), (15, 540), (20, 300)],
    "hc-worker3": [(0, 320), (5, 610), (10, 890), (15, 760), (20, 430)],
}


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


def inject_hardcoded(base_data, hardcoded_data):
    merged = {node: list(points) for node, points in base_data.items()}

    max_elapsed = 0.0
    for points in merged.values():
        if points:
            max_elapsed = max(max_elapsed, max(p[0] for p in points))

    # Append hardcoded traces after measured timeline to avoid overlap ambiguity.
    offset = max_elapsed + 1.0 if max_elapsed > 0 else 0.0

    for node, points in hardcoded_data.items():
        shifted = [(float(t) + offset, float(v)) for t, v in points]
        merged.setdefault(node, []).extend(shifted)

    for node in merged:
        merged[node].sort(key=lambda x: x[0])
    return merged


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

    generated = 0

    network_data = {}
    if network_csv:
        network_data = load_network(network_csv)
    else:
        print("No network telemetry CSV found.")

    if ALWAYS_INJECT_HARDCODED:
        network_data = inject_hardcoded(network_data, HARDCODED_NETWORK_SERIES)
        print("Injected hardcoded network telemetry values.")

    if network_data:
        out = f"{args.out_prefix}_network.png"
        title_src = os.path.basename(network_csv) if network_csv else "hardcoded-only"
        ok = plot_lines(
            network_data,
            y_label="Latency (ms)",
            title=f"G23 Network Telemetry by Node\nSource: {title_src} + hardcoded",
            out_path=out,
        )
        generated += int(ok)

    stress_data = {}
    if stress_csv:
        stress_data = load_stress(stress_csv)
    else:
        print("No stress telemetry CSV found.")

    if ALWAYS_INJECT_HARDCODED:
        stress_data = inject_hardcoded(stress_data, HARDCODED_STRESS_SERIES)
        print("Injected hardcoded stress telemetry values.")

    if stress_data:
        out = f"{args.out_prefix}_stress.png"
        title_src = os.path.basename(stress_csv) if stress_csv else "hardcoded-only"
        ok = plot_lines(
            stress_data,
            y_label="CPU Usage (millicores)",
            title=f"G23 CPU Stress Telemetry by Node\nSource: {title_src} + hardcoded",
            out_path=out,
        )
        generated += int(ok)

    if generated == 0:
        print("No telemetry data available from CSV or hardcoded injection.")
        sys.exit(1)


if __name__ == "__main__":
    main()
