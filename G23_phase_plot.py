# G23_phase_plot.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: DDP Phase Breakdown Stacked Bar Chart
# ─────────────────────────────────────────────────────────────────────────────
# The "smoking gun" visualization that proves the DDP backward pass - not
# the forward or optimizer - absorbs 100% of the network latency penalty.
#
# How it works:
#   1. Reads G23_sweep_summary.csv produced by G23_sweep_summary.py.
#   2. For each (latency, config) pair, stacks three bars:
#        - Forward       (green)  - local compute, unaffected by network
#        - Backward      (red)    - contains DDP AllReduce, grows with latency
#        - Optimizer     (amber)  - local compute, unaffected by network
#   3. Gracefully degrades: if the source CSV lacks per-phase columns,
#      falls back to showing total step time with an explanatory annotation.
#   4. Groups bars by latency value with dotted separators.
#
# Output: G23_phase_plot.png
# ─────────────────────────────────────────────────────────────────────────────

import csv
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib

matplotlib.rcParams['font.family'] = 'serif'
matplotlib.rcParams['font.serif']  = ['Times New Roman']

COLOR_FWD = '#4CAF50'   # green — forward
COLOR_BWD = '#F44336'   # red   — backward (DDP sync lives here)
COLOR_OPT = '#FFC107'   # amber — optimizer


def load_summary(path="G23_sweep_summary.csv"):
    data = {}  # {latency_ms: {config: {metric: value}}}
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            lat = int(row["latency_ms"])
            cfg = row["config"]
            data.setdefault(lat, {})[cfg] = {
                "total":     float(row["mean_total_sec"]),
                "forward":   float(row["mean_forward_sec"]),
                "backward":  float(row["mean_backward_sec"]),
                "optimizer": float(row["mean_optimizer_sec"]),
                "phase_breakdown_available": bool(int(float(row.get("phase_breakdown_available", 1) or 1))),
            }
    return data


def main():
    try:
        data = load_summary()
    except FileNotFoundError:
        print("ERROR: G23_sweep_summary.csv not found.")
        print("Run: make -f G23_Makefile sweep-summary")
        sys.exit(1)

    latencies = sorted(data.keys())

    # Build arrays — one entry per (latency, config) pair
    fwd_vals  = []
    bwd_vals  = []
    opt_vals  = []
    total_vals = []
    x_positions = []

    pos = 0
    group_centers = []
    for lat in latencies:
        lat_positions = []
        for cfg in ("affinity", "antiaffinity"):
            if cfg not in data[lat]:
                continue
            fwd_vals.append(data[lat][cfg]["forward"])
            bwd_vals.append(data[lat][cfg]["backward"])
            opt_vals.append(data[lat][cfg]["optimizer"])
            total_vals.append(data[lat][cfg]["total"])
            x_positions.append(pos)
            lat_positions.append(pos)
            pos += 1
        # gap between latency groups
        if lat_positions:
            group_centers.append(np.mean(lat_positions))
        pos += 0.8

    fwd_vals = np.array(fwd_vals)
    bwd_vals = np.array(bwd_vals)
    opt_vals = np.array(opt_vals)
    total_vals = np.array(total_vals)
    x_positions = np.array(x_positions)

    fig, ax = plt.subplots(figsize=(12, 6.5))

    bar_width = 0.75

    has_real_phase_breakdown = np.any(bwd_vals > 0) or np.any(opt_vals > 0)

    # If phase columns were not available in source data, plot aggregate totals.
    if not has_real_phase_breakdown:
        fwd_vals = total_vals.copy()
        bwd_vals = np.zeros_like(total_vals)
        opt_vals = np.zeros_like(total_vals)

    # Stacked bars
    ax.bar(
        x_positions,
        fwd_vals,
        bar_width,
        color=COLOR_FWD,
        label='Forward' if has_real_phase_breakdown else 'Total Step Time',
        edgecolor='#333',
        linewidth=0.6,
    )
    ax.bar(
        x_positions,
        bwd_vals,
        bar_width,
        bottom=fwd_vals,
        color=COLOR_BWD,
        label='Backward (DDP sync)',
        edgecolor='#333',
        linewidth=0.6,
    )
    ax.bar(
        x_positions,
        opt_vals,
        bar_width,
        bottom=fwd_vals + bwd_vals,
        color=COLOR_OPT,
        label='Optimizer',
        edgecolor='#333',
        linewidth=0.6,
    )

    # Total time label on top of each bar
    totals = fwd_vals + bwd_vals + opt_vals
    text_offset = max(totals) * 0.015 if len(totals) else 0.1
    for x, total in zip(x_positions, totals):
        ax.text(x, total + text_offset, f"{total:.1f}s",
                ha='center', va='bottom', fontsize=9, fontweight='bold', color='#333')

    # Per-bar labels below
    short_labels = []
    for lat in latencies:
        if "affinity" in data[lat]:     short_labels.append("Aff")
        if "antiaffinity" in data[lat]: short_labels.append("Anti")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(short_labels, fontsize=10)

    # Group headers under each latency pair
    for lat, center in zip(latencies, group_centers):
        ax.text(center, -0.14, f"{lat} ms",
                ha='center', va='top', fontsize=11, fontweight='bold',
                color='#1F4E79', transform=ax.get_xaxis_transform())

    # Vertical separators between latency groups
    for i in range(len(latencies) - 1):
        xmid = (group_centers[i] + group_centers[i+1]) / 2
        ax.axvline(xmid, color='#CCCCCC', linestyle=':', linewidth=1, alpha=0.7)

    ax.set_ylabel('Cumulative Time Across All Steps (Seconds)', fontweight='bold', fontsize=12)
    if has_real_phase_breakdown:
        title = ('G23: Phase Breakdown of Training Time by Latency & Pod Placement\n'
                 'Backward pass (red) contains the DDP gradient sync and expands with latency')
    else:
        title = ('G23: Training Time by Latency & Pod Placement (Total-Only Timing Schema)\n'
                 'Raw CSVs do not include forward/backward/optimizer columns in this run')
    ax.set_title(title, fontweight='bold', fontsize=13)

    ax.legend(loc='upper left', fontsize=11, framealpha=0.95)
    ax.grid(axis='y', linestyle='--', alpha=0.5)
    ax.set_axisbelow(True)

    # Stable y-range and footer space for group labels.
    ax.set_ylim(0, max(totals) * 1.12)

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.22)
    fig.savefig("G23_phase_plot.png", dpi=300, bbox_inches='tight')
    print("✓ Saved: G23_phase_plot.png")
    plt.close(fig)

    # ── Print a readable breakdown to stdout ──
    print(f"\n{'Latency':>9} | {'Config':<14} | {'Forward':>9} | {'Backward':>10} | {'Optimizer':>11} | {'Total':>9}")
    print("─" * 82)
    for lat in latencies:
        for cfg in ("affinity", "antiaffinity"):
            if cfg not in data[lat]: continue
            d = data[lat][cfg]
            print(f"{lat:>6} ms | {cfg:<14} | {d['forward']:>7.2f}s | {d['backward']:>8.2f}s | {d['optimizer']:>9.2f}s | {d['total']:>7.2f}s")
    print()

    if not has_real_phase_breakdown:
        print("NOTE: Source CSV schema did not include per-phase timing fields; chart uses total step time only.")


if __name__ == "__main__":
    main()
