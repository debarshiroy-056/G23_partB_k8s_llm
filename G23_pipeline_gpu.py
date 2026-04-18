# G23_pipeline_gpu.py

# ─────────────────────────────────────────────────────────────────────────────
# OVERVIEW: Phase 3 GPU Results Aggregator and Plot Generator
# ─────────────────────────────────────────────────────────────────────────────
# GPU counterpart to G23_pipeline.py. Aggregates bare-metal trial CSVs and
# renders the Phase 3 headline plots comparing Clean GPU, Noisy GPU, and the
# NEMESIS auto-routed outcome.
#
# How it works:
#   1. Globs results/G23_results_gpu_<config>_run*.csv for each of three
#      configs: clean, noisy, nemesis.
#   2. Aggregates total runtime (mean ± std) and per-step latency arrays.
#   3. Produces:
#        - G23_plot_bar_gpu.png     (overall runtime bar chart)
#        - G23_plot_perstep_gpu.png (per-step latency line plot)
#
# Invoked via `make -f G23_Makefile_gpu plot`.
# ─────────────────────────────────────────────────────────────────────────────

import os
import csv
import glob
import numpy as np
import matplotlib.pyplot as plt

RESULTS_DIR = "results"
NUM_STEPS = 50

def get_totals(config):
    pattern = os.path.join(RESULTS_DIR, f"G23_results_gpu_{config}_run*.csv")
    files = glob.glob(pattern)
    totals = []
    for f in files:
        with open(f, 'r') as csvfile:
            reader = list(csv.DictReader(csvfile))
            if reader:
                totals.append(float(reader[-1]['cumulative_sec']))
    return totals

def get_step_stats(config):
    pattern = os.path.join(RESULTS_DIR, f"G23_results_gpu_{config}_run*.csv")
    files = sorted(glob.glob(pattern))
    runs = []
    for file_path in files:
        with open(file_path, "r") as csvfile:
            reader = list(csv.DictReader(csvfile))
            if reader:
                step_times = [float(row["step_time_sec"]) for row in reader if "step_time_sec" in row]
                if len(step_times) >= NUM_STEPS:
                    runs.append(step_times[:NUM_STEPS])
    if not runs:
        return np.zeros(NUM_STEPS), np.zeros(NUM_STEPS), 0
    arr = np.array(runs, dtype=float)
    return arr.mean(axis=0), arr.std(axis=0), arr.shape[0]

# Structure the data
configs = [
    ("clean", "Baseline\n(Clean GPU 0)", "#4C72B0"),
    ("noisy", "Baseline\n(Noisy GPU 1)", "#DD8452"),
    ("nemesis", "NEMESIS\n(Auto-Routed)", "#55A868")
]

means, stds, labels, colors = [], [], [], []
for conf, label, color in configs:
    totals = get_totals(conf)
    means.append(np.mean(totals) if totals else 0)
    stds.append(np.std(totals) if totals else 0)
    labels.append(label)
    colors.append(color)

# --- 1. Generate Bar Plot ---
plt.figure(figsize=(10, 6))
bars = plt.bar(labels, means, yerr=stds, capsize=8, color=colors, edgecolor='black')
plt.ylabel('Execution Time (seconds)', fontsize=12, fontweight='bold')
plt.title('NEMESIS GPU Scheduler Performance (n=5)', fontsize=14, fontweight='bold')

for bar, mean, std in zip(bars, means, stds):
    plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + std + 0.05, 
             f'{mean:.2f}s ± {std:.2f}s', ha='center', va='bottom', fontweight='bold')

plt.tight_layout()
plt.savefig('G23_plot_bar_gpu.png', dpi=300)

# --- 2. Generate Per-Step Plot ---
plt.figure(figsize=(12, 6))
steps = np.arange(NUM_STEPS)
for conf, label, color in configs:
    mean_vals, std_vals, n = get_step_stats(conf)
    if n > 0:
        plt.plot(steps, mean_vals, label=f"{label.replace(chr(10), ' ')} (n={n})", color=color, linewidth=2)
        plt.fill_between(steps, mean_vals - std_vals, mean_vals + std_vals, color=color, alpha=0.15)

plt.grid(True, linestyle="--", alpha=0.7)
plt.xlabel("Training Step", fontweight="bold")
plt.ylabel("Step Latency (seconds)", fontweight="bold")
plt.title("G23: GPU Per-Step Latency Comparison (mean ± 1σ)", fontsize=14, fontweight="bold")
plt.xlim(-1, NUM_STEPS)
plt.legend(fontsize=10, loc="upper right", framealpha=1.0, edgecolor="darkgray")

plt.tight_layout()
plt.savefig('G23_plot_perstep_gpu.png', dpi=300)

print("✅ GPU Pipeline complete! G23_plot_bar_gpu.png and G23_plot_perstep_gpu.png generated.")
